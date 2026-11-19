#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""panda-upload-task — 量枢院任务成果回填 BUILD skill 主入口。

流程：抓取任务列表 -> 筛选 创作中/待创作 -> 任务名匹配已发布 skill
     -> 解析成果资源（功能说明 / GitHub 地址 / 分发 zip）
     -> 用 opencli browser 驱动详情页表单填写 -> 保存草稿或提交审核。

零三方依赖；所有外部命令经可注入 runner 执行，便于离线测试。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
import datetime

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- 配置常量

DEFAULT_CONFIG = {
    "session": "panda-upload",                      # opencli browser 会话名
    "base_app_url": "https://lsy.quant789.com/app",
    "api_base": "/api/v1",
    "window_url_marker": "lsy.quant789.com",        # osascript 置前匹配用
    "statuses": ["IN_PROGRESS", "PENDING"],         # 创作中 / 待创作
    "mode": "draft",                                # draft | submit
    "dry_run": True,
    "write_channel": "ui",                          # ui | api（api 通道字段未经线上实测，默认 ui）
    "claim_ttl_min": 30,
    "project_root": os.getcwd(),
    "public_dir": "public/skills",
    "dist_dir": "public/dist",
    "max_feature_chars": 1200,
    "submit_cutoff_time": "23:50:59",   # 用户规则：任务截止日该时刻（北京时间）后不再做任何平台写入
    "aliases": {
        "task_numbers": {
            # 任务编号 -> public/skills 目录名（最高优先级，人工维护）
        },
        "keywords": {
            "JEV": "skill-jev-history-replay",
            "盯盘": "skill-jev-history-replay",
            "约束": "skill-constraint-stress-test",
            "异常数据": "skill-constraint-stress-test",
            "观点": "skill-opinion-to-ruler",
            "图神经网络": "skill-dl-gnn-stock-graph",
            "GNN": "skill-dl-gnn-stock-graph",
            "仓位": "skill-intraday-position-manager",
            "止盈止损": "skill-auto-stop-loss-take-profit",
        },
    },
}

TASK_STATUS_LABELS = {
    "PENDING": "待创作",
    "IN_PROGRESS": "创作中",
    "PENDING_REVIEW": "待审核",
    "REWORK": "需修改",
    "COMPLETED": "已完成",
    "CANCELLED": "已取消",
}

ZIP_REQUIRED_MEMBERS = [
    "SKILL.md", "README.md", "README.en.md", "LICENSE", "INSTALL.md",
    "requirements.txt", "skill.json", "CHANGELOG.md", "agents/openai.yaml",
]

README_FEATURE_SECTIONS = ["它解决什么问题", "简介", "核心功能", "核心设计", "功能", "概览"]


class UploadTaskError(ValueError):
    """输入校验 / 配置错误。"""


class Blocked(Exception):
    """资源闸门未通过（如未 push、缺 remote），只进 blocked 报告，不算崩溃。"""

    def __init__(self, skill: str, reason: str):
        super().__init__(reason)
        self.skill = skill
        self.reason = reason


class CliError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"[{code}] {message}")
        self.code = code


# ---------------------------------------------------------------- 输入校验

def validate_input(input_data):
    """缺字段、空数据、类型错误时抛出明确异常（BUILD §8）。"""
    if input_data is None:
        input_data = {}
    if not isinstance(input_data, dict):
        raise UploadTaskError(f"input_data 必须是 dict，收到 {type(input_data).__name__}")
    unknown = set(input_data) - {"tasks", "skills"}
    if unknown:
        raise UploadTaskError(f"input_data 含未知字段: {sorted(unknown)}；允许 tasks/skills")

    tasks = input_data.get("tasks")
    if tasks is not None:
        if not isinstance(tasks, list):
            raise UploadTaskError("tasks 必须是 list[dict] 或 None")
        for i, t in enumerate(tasks):
            if not isinstance(t, dict):
                raise UploadTaskError(f"tasks[{i}] 必须是 dict")
            missing = {"id", "task_number", "title", "status"} - set(t)
            if missing:
                raise UploadTaskError(f"tasks[{i}] 缺字段: {sorted(missing)}")

    skills = input_data.get("skills")
    if skills is not None:
        if not isinstance(skills, dict):
            raise UploadTaskError("skills 必须是 dict[slug -> 资源dict] 或 None")
        for slug, res in skills.items():
            if not isinstance(res, dict):
                raise UploadTaskError(f"skills[{slug}] 必须是 dict")
            missing = {"feature", "github_url", "zip_path", "version"} - set(res)
            if missing:
                raise UploadTaskError(f"skills[{slug}] 缺字段: {sorted(missing)}")
            if not res["feature"]:
                raise UploadTaskError(f"skills[{slug}].feature 不得为空")
    return True


# ---------------------------------------------------------------- 纯函数层

def normalize_tasks(items):
    """把 API items 规整为报告用 task 列表。"""
    out = []
    for t in items:
        out.append({
            "id": t["id"],
            "task_number": t.get("taskNumber", ""),
            "title": (t.get("title") or "").strip(),
            "status": t.get("status", ""),
            "ends_at": t.get("endsAt"),
        })
    return out


def filter_tasks(tasks, statuses):
    """返回 (targets, skipped)。statuses 为允许处理的状态集合。"""
    allow = set(statuses)
    targets = [t for t in tasks if t["status"] in allow]
    skipped = [t for t in tasks if t["status"] not in allow]
    return targets, skipped


def match_task_to_skill(task, aliases, existing_slugs, source_map=None):
    """四级匹配。返回 (slug|None, how, reason)。歧义一律 unmatched，禁止猜。"""
    title = task["title"]
    num_map = aliases.get("task_numbers", {})
    kw_map = aliases.get("keywords", {})

    slug = num_map.get(task["task_number"])
    if slug:
        if slug in existing_slugs:
            return slug, "task_number", ""
        return None, "task_number", f"映射目标 {slug} 不在 public/skills"

    hits = {s for s, toks in (source_map or {}).items()
            if task["task_number"] in toks and s in existing_slugs}
    if len(hits) == 1:
        return hits.pop(), "source_task", ""
    if len(hits) > 1:
        return None, "source_task", f"source_task 反查命中多个: {sorted(hits)}"

    for m in re.finditer(r"[（(]([A-Za-z0-9][A-Za-z0-9_-]{2,})[）)]", title):
        cand = "skill-" + m.group(1).lower()
        if cand in existing_slugs:
            return cand, "paren_slug", ""

    hits = {slug for kw, slug in kw_map.items() if kw in title and slug in existing_slugs}
    if len(hits) == 1:
        return hits.pop(), "keyword", ""
    if len(hits) > 1:
        return None, "keyword", f"关键词命中多个 skill: {sorted(hits)}"
    return None, "", "无 task_number/括号英文/唯一关键词匹配，需人工补充 aliases"


def to_https_repo_url(remote_url):
    """git remote -> 浏览器可点开的 https 地址。"""
    url = (remote_url or "").strip()
    if not url:
        raise UploadTaskError("remote url 为空")
    url = re.sub(r"/+$", "", url)
    url = re.sub(r"\.git$", "", url)
    m = re.match(r"^git@github\.com:([\w.-]+)/([\w.-]+)$", url)
    if m:
        return f"https://github.com/{m.group(1)}/{m.group(2)}"
    m = re.match(r"^(?:https?://|git\+ssh://|ssh://git@)github\.com/([\w.-]+)/([\w.-]+)$", url)
    if m:
        return f"https://github.com/{m.group(1)}/{m.group(2)}"
    return url


def extract_feature_from_readme(md, limit=1200):
    """README -> 成果说明正文：标题 + 简介段 + 首个正文章节。
    容忍「# README」占位标题：真实标题取首个非 README 的 h1。"""
    lines = (md or "").splitlines()
    h1s = [(i, l[2:].strip()) for i, l in enumerate(lines) if l.startswith("# ")]
    if not h1s:
        return ""
    real = [h for h in h1s if not re.fullmatch(r"readme(\.md)?", h[1], re.I)]
    idx, title = real[0] if real else h1s[0]
    intro = []
    for l in lines[idx + 1:]:
        if l.startswith("##"):
            break
        if l.startswith("#"):
            continue  # 重复 h1（如真实标题在前置 README 标题之后）不当正文
        if l.strip():
            intro.append(l.strip())
    wanted = set(README_FEATURE_SECTIONS)
    sec_name = None
    cur, buf, grabbing = None, [], False
    for l in lines:
        if l.startswith("## "):
            if grabbing:
                break
            cur = l[3:].strip()
            if cur in wanted:
                grabbing = True
                sec_name = cur
            continue
        if grabbing and l.strip() and not l.startswith(("```", "|", ">", "![", "[", "- **风险")):
            buf.append(l.strip())
        if grabbing and len(buf) >= 6:
            break
    sec_paras = buf
    parts = [title]
    if intro:
        parts.append(" ".join(intro[:2]))
    if sec_name:
        parts.append(f"【{sec_name}】" + " ".join(sec_paras[:4]))
    text = "\n\n".join(p for p in parts if p)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return text[:limit]


def semver_key(v):
    return tuple(int(p) if p.isdigit() else 0 for p in (v or "").split("."))


def parse_dist_zips(filenames, slug):
    """从 dist 文件名解析 (semver_key, version, filename) 列表。"""
    pat = re.compile(rf"^{re.escape(slug)}-v(\d+\.\d+\.\d+)\.zip$")
    out = []
    for name in filenames:
        m = pat.match(name)
        if m:
            out.append((semver_key(m.group(1)), m.group(1), name))
    return out


def is_deadline_passed(ends_at_iso, cutoff_hms, now_utc=None):
    """用户规则：任务截止日（北京时间）的 cutoff 时刻之后，不再更新平台。

    ends_at_iso 为 API 的 UTC ISO 串（如 2026-11-18T15:59:59.999Z）；缺失视为无截止，不拦截。
    """
    if not ends_at_iso:
        return False
    now_utc = now_utc or datetime.datetime.now(datetime.timezone.utc)
    ends = datetime.datetime.fromisoformat(ends_at_iso.replace("Z", "+00:00"))
    beijing = ends + datetime.timedelta(hours=8)
    cutoff_date = beijing.date()
    hh, mm, ss = (int(x) for x in cutoff_hms.split(":"))
    cutoff_utc = datetime.datetime(
        cutoff_date.year, cutoff_date.month, cutoff_date.day, hh, mm, ss,
        tzinfo=datetime.timezone(datetime.timedelta(hours=8))).astimezone(datetime.timezone.utc)
    return now_utc >= cutoff_utc


def pick_upload_version(dist_files, slug, head_version, remote_tag_versions):
    """用户规则：dist 中多版本时取「最后一个已发布的」。

    候选 = HEAD 版本 + dist 里存在且远端有 v{version} tag 的版本；取最高 semver。
    未发布（无 tag）的新版本文件一律不选——宁可用旧已发布版，不上传幽灵包。
    """
    cands = {head_version}
    for _k, v, _name in parse_dist_zips(dist_files, slug):
        if v == head_version or v in remote_tag_versions:
            cands.add(v)
    return max(cands, key=semver_key)


def zip_member_check(path):
    """返回 (files, missing, polluted)。缺件/夹带都要查（panda-publisher §7 同构）。"""
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
    base = names[0].split("/")[0] + "/" if names else ""
    missing = [f for f in ZIP_REQUIRED_MEMBERS if base + f not in names]
    polluted = [n for n in names if re.search(r"(\.git/|__pycache__/|\.DS_Store|^output/|/output/)", n) and not n.endswith("/")]
    files = len([n for n in names if not n.endswith("/")])
    return files, missing, polluted


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def build_plan_item(task, res, cfg):
    """单任务 UI 动作序列（不执行，供审阅）。"""
    actions = [f"open {cfg['base_app_url']}/tasks/{task['id']}"]
    if task["status"] == "PENDING":
        actions.append("click 按钮「开始创作」（PENDING -> IN_PROGRESS）")
    actions += [
        "click 按钮「填写成果」，等待 dialog 出现",
        f"fill textarea[成果说明] ← {len(res['feature'])} 字功能描述",
        f"fill input[type=url][成果链接] ← {res['github_url']}",
        f"同步附件：删除旧版本 zip（如有）→ 上传 {os.path.basename(res['zip_path'])}（同名已存在则跳过）",
        "click 按钮「" + ("保存草稿" if cfg["mode"] == "draft" else "提交审核") + "」",
        "回读任务详情验证",
    ]
    return {
        "task_number": task["task_number"],
        "title": task["title"],
        "id": task["id"],
        "status_before": task["status"],
        "skill": res.get("skill"),
        "version": res.get("version"),
        "github_url": res.get("github_url"),
        "zip": res.get("zip_path"),
        "zip_sha256": res.get("zip_sha256"),
        "actions": actions,
    }


# ---------------------------------------------------------------- 外部命令层

def _default_runner(argv, cwd=None, env=None, timeout=60):
    p = subprocess.run(argv, cwd=cwd, env=env, timeout=timeout,
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise CliError("exit_%d" % p.returncode,
                       " ".join(argv[:4]) + " 失败: " + (p.stderr or p.stdout).strip()[:300])
    return p.stdout


def _cfg_runner(cfg):
    return cfg.get("runner") or _default_runner


def cli(cfg, *args, timeout=90):
    """opencli browser --session S ... -> envelope data。"""
    argv = ["opencli", "browser", "--session", cfg["session"], *args]
    stdout = _cfg_runner(cfg)(argv, timeout=timeout) if cfg.get("runner") else _default_runner(argv, timeout=timeout)
    text = stdout.strip()
    start = text.find("{")
    if start < 0:
        raise CliError("bad_output", f"opencli 输出无 JSON: {text[:200]}")
    env = json.loads(text[start:])
    if not env.get("ok"):
        err = env.get("error", {})
        raise CliError(err.get("code", "unknown"), err.get("message", "opencli 失败"))
    return env.get("data")


def git(cfg, pub_dir, *args, timeout=60):
    env = dict(os.environ, GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10")
    return _cfg_runner(cfg)(["git", "-C", pub_dir, *args], env=env, timeout=timeout).strip()


def api_get(cfg, path):
    """同源只读 fetch（eval 不修改页面，符合 opencli-browser 规则 9）。

    兼容两种 opencli 输出形态：eval 结果为纯原始文本，或被 `{ok,data}` 再包一层
    （实测 v2.0.2 为后者）。最终返回平台 body 的 **data** 内层；平台 ok=false 抛错。
    """
    js = "(() => fetch('%s', {credentials:'include'}).then(r => r.text()))()" % path
    raw = cli(cfg, "eval", js)
    return api_result(raw)


def api_post(cfg, path, payload=None):
    """同源 POST（写通道 API 化用；body 字段形状未经线上实测，调用方必须准备 UI 兜底）。"""
    js = ("(() => fetch('%s', {method:'POST', credentials:'include', "
          "headers:{'Content-Type':'application/json'}, body:%s}).then(r=>r.text()))()"
          % (path, json.dumps(json.dumps(payload or {}, ensure_ascii=False))))
    return api_result(cli(cfg, "eval", js))


def api_result(raw):
    """api_get/api_post 共用解包（先 envelope，后平台 ok/data）。"""
    body = raw
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError as e:
            raise CliError("api_error", f"非 JSON 响应: {str(raw)[:160]} ({e})")
    if not isinstance(body, dict):
        raise CliError("api_error", f"无法解析响应: {str(raw)[:160]}")
    if "ok" in body:
        if not body["ok"]:
            raise CliError("api_error", f"平台返回 ok=false: {str(body)[:200]}")
        return body.get("data")
    return body


# ---------------------------------------------------------------- 并行认领锁（用户规则：串行化）

def _claim_path(cfg):
    return os.path.join(cfg["project_root"], ".work-claim")


def _claim_expired(claim, ttl_min):
    try:
        at = datetime.datetime.fromisoformat(claim.get("at", ""))
    except (ValueError, TypeError):
        return True
    return (datetime.datetime.now() - at) > datetime.timedelta(minutes=ttl_min)


def claim_work(cfg, activity):
    """原子化认领 .work-claim；他人未过期 -> 拒绝。返回认领人标识。"""
    who = cfg["session"]
    path = _claim_path(cfg)
    cur = None
    try:
        with open(path) as f:
            cur = json.load(f)
    except (OSError, ValueError):
        cur = None  # 不存在/损坏/不可读：允许重新占用
    if isinstance(cur, dict) and cur.get("who") and cur.get("who") != who \
            and not _claim_expired(cur, cfg["claim_ttl_min"]):
        raise UploadTaskError(
            "工作区被 %s 占用（activity=%s, at=%s）；请先协调或等待 %d 分钟 TTL 过期"
            % (cur.get("who"), cur.get("activity"), cur.get("at"), cfg["claim_ttl_min"]))
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"who": who, "activity": activity,
                   "at": datetime.datetime.now().isoformat(timespec="seconds")}, f, ensure_ascii=False)
    os.replace(tmp, path)
    return who


def release_claim(cfg):
    try:
        with open(_claim_path(cfg)) as f:
            cur = json.load(f)
        if cur.get("who") == cfg["session"]:
            os.remove(_claim_path(cfg))
    except (OSError, ValueError):
        pass


def ensure_visible(cfg):
    """osascript 把目标标签页窗口置前；非 macOS 直接放行。"""
    if sys.platform != "darwin" or cfg.get("runner"):
        return
    marker = cfg["window_url_marker"]
    script = ('tell application "Google Chrome"\nactivate\n'
              'repeat with w in windows\n  try\n'
              f'    if (URL of active tab of w) contains "{marker}" then\n'
              '      set index of w to 1\n      set minimized of w to false\n'
              '    end if\n  end try\nend repeat\nend tell')
    subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=20)


# ---------------------------------------------------------------- 资源解析

def list_public_skill_dirs(cfg):
    root = os.path.join(cfg["project_root"], cfg["public_dir"])
    if not os.path.isdir(root):
        return set(), root
    return {d for d in os.listdir(root)
            if d.startswith("skill-") and os.path.isfile(os.path.join(root, d, "skill.json"))}, root


def version_drift(cfg, pub, ref, version):
    """版本单源校验（skill.json 为准）：CHANGELOG 首条 / openai.yaml 漂移则列出。"""
    drift = []
    try:
        chlog = git(cfg, pub, "show", f"{ref}:CHANGELOG.md")
        m = re.search(r"^## \[(\d+\.\d+\.\d+)\]", chlog, re.M)
        if m and m.group(1) != version:
            drift.append("CHANGELOG 当前条目=%s" % m.group(1))
    except CliError:
        pass
    try:
        oy = git(cfg, pub, "show", f"{ref}:agents/openai.yaml")
        m = re.search(r"^\s*version:\s*[\"']?(\d+\.\d+\.\d+)", oy, re.M)
        if m and m.group(1) != version:
            drift.append("openai.yaml=%s" % m.group(1))
    except CliError:
        pass
    return drift


def scan_source_tasks(cfg, slugs):
    """匹配靠数据：从各 skill HEAD skill.json 的 source_task 提取平台任务编号 token。"""
    out = {}
    for slug in slugs:
        pub = os.path.join(cfg["project_root"], cfg["public_dir"], slug)
        try:
            sj = json.loads(git(cfg, pub, "show", "HEAD:skill.json"))
        except (CliError, ValueError, OSError):
            continue
        st = sj.get("source_task")
        vals = st if isinstance(st, list) else [st] if isinstance(st, str) else []
        toks = set()
        for v in vals:
            toks.update(re.findall(r"\bTS[\w-]+\b|\b[A-Z]{2,}-[\w-]+\b|\bB\d{1,3}\b", v or ""))
        if toks:
            out[slug] = toks
    return out


def resolve_skill_resources(cfg, slug):
    """从"已发布形态"解析三样交付物。任何闸门不过 -> Blocked。"""
    pub = os.path.join(cfg["project_root"], cfg["public_dir"], slug)
    if not os.path.isdir(os.path.join(pub, ".git")):
        raise Blocked(slug, f"{pub} 不是 git 工作区，先运行 panda-publisher")

    runner = _cfg_runner(cfg)
    try:
        git(cfg, pub, "fetch", "origin", "-q")
        head = git(cfg, pub, "rev-parse", "HEAD")
        origin = git(cfg, pub, "rev-parse", "origin/main")
        if head != origin:
            raise Blocked(slug, f"HEAD {head[:7]} != origin/main {origin[:7]}，先 panda-publisher 推送")
        raw = git(cfg, pub, "status", "--porcelain")
        dirty = bool(raw.strip())
        head_version = json.loads(git(cfg, pub, "show", "HEAD:skill.json"))["version"]
        tagout = git(cfg, pub, "ls-remote", "--tags", "origin")
        remote_tag_versions = set(re.findall(r"refs/tags/v(\d+\.\d+\.\d+)", tagout))
        remote = git(cfg, pub, "remote", "get-url", "origin")
    except Blocked:
        raise
    except (CliError, ValueError, KeyError) as e:
        raise Blocked(slug, f"git 探测失败: {e}")

    dist = os.path.join(cfg["project_root"], cfg["dist_dir"])
    try:
        dist_files = os.listdir(dist)
    except OSError:
        dist_files = []
    version = pick_upload_version(dist_files, slug, head_version, remote_tag_versions)
    ref = "HEAD" if version == head_version else "v" + version
    drift = version_drift(cfg, pub, ref, version)
    if drift:
        raise Blocked(slug, "版本漂移（skill.json 唯一真源，HEAD 版 %s）：%s；"
                            "先跑 skills/panda-builder/scripts/validate_skill.py 定位，修正后重新发布"
                            % (version, "; ".join(drift)))
    try:
        readme = git(cfg, pub, "show", f"{ref}:README.md")
    except CliError:
        raise Blocked(slug, f"无法读取 {ref}:README.md（tag 不可解引用？请检查发布状态）")

    feature = extract_feature_from_readme(readme, cfg["max_feature_chars"])
    if not feature:
        raise Blocked(slug, "README 功能段提取为空")

    notes = []
    if version != head_version:
        notes.append(f"dist 存在更晚的已发布版本 v{version}（origin 有对应 tag），按其上传；HEAD 为 v{head_version}")
    if dirty:
        wt_v = None
        try:
            wt_v = json.loads(open(os.path.join(pub, "skill.json")).read())["version"]
        except Exception:
            pass
        notes.append(f"发布工作区有未提交变更（工作树 v{wt_v} vs 已发布 v{version}），本次按已发布版本提交")

    github_url = to_https_repo_url(remote)
    zip_path = os.path.join(dist, f"{slug}-v{version}.zip")
    zip_sha = None
    if os.path.isfile(zip_path):
        try:
            files, missing, polluted = zip_member_check(zip_path)
        except zipfile.BadZipFile:
            raise Blocked(slug, f"dist zip 正在写入或已损坏，稍后重试: {zip_path}")
        if missing:
            raise Blocked(slug, f"dist zip 缺件: {missing}")
        if polluted:
            raise Blocked(slug, f"dist zip 夹带非交付物: {polluted[:3]}")
        zip_sha = sha256_file(zip_path)
    elif cfg["dry_run"]:
        notes.append(f"dist zip 不存在，执行阶段将由 git archive {ref} 生成 {os.path.basename(zip_path)}")
    else:
        os.makedirs(dist, exist_ok=True)
        try:
            runner(["git", "-C", pub, "archive", "--format=zip", f"--prefix={slug}/",
                    "-o", zip_path, ref], timeout=120)
        except CliError as e:
            raise Blocked(slug, f"git archive 失败: {e}")
        try:
            files, missing, polluted = zip_member_check(zip_path)
        except zipfile.BadZipFile as e:
            os.remove(zip_path)
            raise Blocked(slug, f"新生成 zip 校验失败: {e}")
        if missing:
            os.remove(zip_path)
            raise Blocked(slug, f"新生成 zip 自检缺件: {missing}")
        if polluted:
            os.remove(zip_path)
            raise Blocked(slug, f"新生成 zip 夹带: {polluted[:3]}")
        zip_sha = sha256_file(zip_path)
        notes.append(f"已由 git archive {ref} 生成并自检通过（{files} 个文件）")

    size_mb = os.path.getsize(zip_path) / 1e6 if os.path.isfile(zip_path) else None
    if size_mb is not None and size_mb > 50:
        raise Blocked(slug, f"zip 超过 50MB 限制: {size_mb:.1f}MB")

    return {
        "skill": slug, "version": version, "feature": feature,
        "github_url": github_url, "zip_path": zip_path, "zip_sha256": zip_sha,
        "notes": notes,
    }


# ---------------------------------------------------------------- 执行层

def fetch_tasks_online(cfg):
    base = cfg["base_app_url"]
    cli(cfg, "open", f"{base}/tasks")
    cli(cfg, "wait", "time", "2")
    data = api_get(cfg, f"{cfg['api_base']}/tasks?page=1&sortBy=updatedAt&order=desc")
    if not isinstance(data, dict) or "items" not in data:
        raise CliError("api_error", f"tasks 接口无 items: {str(data)[:200]}")
    return normalize_tasks(data["items"])


def _find_ref(cfg, css):
    data = cli(cfg, "find", "--css", css)
    entries = data.get("entries") or []
    if not entries:
        raise CliError("selector_not_found", css)
    return str(entries[0]["ref"])


def _click_button(cfg, names):
    """按候选文案依次点击按钮；语义命中多个时回退点第一个可见 ref。
    （草稿态主按钮为「继续编辑」，且页面上有两个同名按钮，语义点击会歧义拒绝。）"""
    last = None
    for name in names:
        try:
            cli(cfg, "click", "--role", "button", "--name", name)
            return name
        except CliError as e:
            last = e
        try:
            data = cli(cfg, "find", "--role", "button", "--name", name)
        except CliError:
            continue
        entries = [x for x in (data.get("entries") or []) if x.get("visible", True)]
        if entries:
            cli(cfg, "click", str(entries[0]["ref"]))
            return name
    raise last or CliError("button_not_found", str(names))


_ZIP_NAME_RE = re.compile(r"^skill-[a-z0-9][a-z0-9_-]*-v\d+\.\d+\.\d+\.zip$")


def dialog_attachment_names(cfg):
    js = ("(() => [...document.querySelectorAll('section[role=dialog] .attachment-link')]"
          ".map(a => a.getAttribute('download') || a.textContent.trim()))()")
    names = cli(cfg, "eval", js)
    if isinstance(names, str):
        names = json.loads(names)
    return [str(n).strip() for n in (names or [])]


def sync_attachments(cfg, zip_path):
    """用户规则：存在更新版本时，先删除线上草稿里的旧版本 zip，再上传最新 zip。

    同名附件已存在则不重复上传；只删除形如 skill-*-vX.Y.Z.zip 的旧版本包，
    不动用户上传的其他类型附件。
    """
    want = os.path.basename(zip_path)
    existing = dialog_attachment_names(cfg)
    removed = []
    for name in existing:
        if name == want:
            continue
        if _ZIP_NAME_RE.match(name):
            ensure_visible(cfg)
            cli(cfg, "click", "--role", "button", "--name", f"删除附件 {name}")
            cli(cfg, "wait", "time", "1")
            removed.append(name)
    if want in existing:
        return {"uploaded": False, "kept": want, "removed": removed}
    up = _find_ref(cfg, 'section[role=dialog] input[type=file]')
    data = cli(cfg, "upload", up, zip_path, timeout=180)
    if not data.get("uploaded"):
        raise CliError("upload_failed", f"zip 上传失败: {data}")
    return {"uploaded": True, "added": want, "removed": removed}


def _reread(cfg, css, ref, expected, prefix=False):
    """回读验证；React 受控组件重渲染会让旧 ref 变 stale——重定位后再读一次。"""
    for attempt in range(2):
        try:
            got = cli(cfg, "get", "value", ref)
            break
        except CliError as e:
            if e.code != "stale_ref" or attempt:
                raise
            ref = _find_ref(cfg, css)
    val = got.get("value") or ""
    ok = val.startswith(expected[:40]) if prefix else val == expected
    if not ok:
        raise CliError("verify_failed", f"回读不一致: {val[:60]!r}")
    return ref


def execute_upload(cfg, task, res):
    """写通道分发：ui（默认，已线上验证）；api（端点自 bundle 提取，body 形状未实测，
    任何失败自动回退 UI）。"""
    if cfg.get("write_channel") == "api":
        try:
            return execute_upload_api(cfg, task, res)
        except (CliError, UploadTaskError) as e:
            out = _execute_upload_ui(cfg, task, res)
            out["fallback_reason"] = "api channel failed: %s" % e
            return out
    return _execute_upload_ui(cfg, task, res)


def execute_upload_api(cfg, task, res):
    """API 写通道：/start + /submissions（含附件则交由上层回退 UI——multipart 形状未知）。

    端点：POST /api/v1/tasks/{id}/start、POST /api/v1/tasks/{id}/submissions
    状态常量（bundle 实测）：DRAFT / PENDING_REVIEW / WITHDRAWN。
    """
    api = cfg["api_base"]
    d = api_get(cfg, f"{api}/tasks/{task['id']}")
    status = (d or {}).get("status", task["status"]) if isinstance(d, dict) else task["status"]
    if status == "PENDING":
        api_post(cfg, f"{api}/tasks/{task['id']}/start")
    # multipart 上传与 attachments 列表端点未实测：附件一致性无法经 API 核验，
    # 默认拒绝并回退 UI；纯文本更新场景需显式 api_text_only=True 承担风险。
    if not cfg.get("api_text_only"):
        raise CliError("api_attachment_gap", "zip 附件 multipart 未实测，API 通道暂不承接带附件提交")
    action = "draft" if cfg["mode"] == "draft" else "submit"
    api_post(cfg, f"{api}/tasks/{task['id']}/submissions",
             {"summary": res["feature"], "link": res["github_url"], "action": action})
    final = api_get(cfg, f"{api}/tasks/{task['id']}")
    return {"action": "draft_saved" if cfg["mode"] == "draft" else "submitted_for_review",
            "status_after": (final or {}).get("status", ""), "verified": True,
            "attachments": {"uploaded": False, "kept": os.path.basename(res["zip_path"]),
                            "removed": [], "via": "api_text_only"}}


def _execute_upload_ui(cfg, task, res):
    """驱动详情页表单。失败抛 CliError，由上层记录该任务错误后继续下一条。"""
    base = cfg["base_app_url"]
    cli(cfg, "open", f"{base}/tasks/{task['id']}")
    cli(cfg, "wait", "time", "2")

    detail = api_get(cfg, f"{cfg['api_base']}/tasks/{task['id']}")
    status = detail.get("status", task["status"]) if isinstance(detail, dict) else task["status"]

    # 关闭可能遗留的成果弹窗（它会遮挡底层按钮导致语义定位 0 命中）
    try:
        stale = bool(cli(cfg, "find", "--css", "section[role=dialog]").get("matches_n"))
    except CliError:
        stale = False
    if stale:
        cli(cfg, "keys", "Escape")
        cli(cfg, "wait", "time", "1")

    if status == "PENDING":
        ensure_visible(cfg)
        _click_button(cfg, ["开始创作"])
        cli(cfg, "wait", "time", "1.5")
        detail = api_get(cfg, f"{cfg['api_base']}/tasks/{task['id']}")
        status = detail.get("status", status) if isinstance(detail, dict) else status

    ensure_visible(cfg)
    _click_button(cfg, ["填写成果", "继续编辑"])
    cli(cfg, "wait", "selector", "section[role=dialog]", "--timeout", "8000")

    ta = _find_ref(cfg, "section[role=dialog] textarea")
    cli(cfg, "fill", ta, res["feature"])
    ta = _reread(cfg, "section[role=dialog] textarea", ta, res["feature"], prefix=True)

    url_t = _find_ref(cfg, 'section[role=dialog] input[type=url]')
    cli(cfg, "fill", url_t, res["github_url"])
    _reread(cfg, 'section[role=dialog] input[type=url]', url_t, res["github_url"])

    att = sync_attachments(cfg, res["zip_path"])

    btn = "保存草稿" if cfg["mode"] == "draft" else "提交审核"
    ensure_visible(cfg)
    _click_button(cfg, [btn])
    cli(cfg, "wait", "time", "2")

    final = api_get(cfg, f"{cfg['api_base']}/tasks/{task['id']}")
    status_after = final.get("status", "") if isinstance(final, dict) else ""
    return {
        "action": "draft_saved" if cfg["mode"] == "draft" else "submitted_for_review",
        "status_after": status_after,
        "verified": status_after != "",
        "attachments": att,
    }


# ---------------------------------------------------------------- 主入口

def run(input_data=None, config=None):
    """见模块 docstring。返回固定字段报告（SKILL.md §8）。"""
    validate_input(input_data)
    input_data = input_data or {}
    cfg = dict(DEFAULT_CONFIG)
    if config:
        aliases = {**cfg["aliases"], **(config.get("aliases") or {})}
        aliases["task_numbers"] = {**cfg["aliases"]["task_numbers"], **(aliases.get("task_numbers") or {})}
        aliases["keywords"] = {**cfg["aliases"]["keywords"], **(aliases.get("keywords") or {})}
        cfg.update({k: v for k, v in config.items() if k != "aliases"})
        cfg["aliases"] = aliases

    if cfg["mode"] not in ("draft", "submit"):
        raise UploadTaskError(f"mode 必须是 draft/submit，收到 {cfg['mode']!r}")

    errors, blocked = [], []
    report = {"mode": cfg["mode"], "dry_run": cfg["dry_run"],
              "targets": [], "skipped": [], "unmatched": [], "blocked": [], "errors": errors}

    # 1. 任务列表
    if input_data.get("tasks") is not None:
        tasks = normalize_tasks([
            {"id": t["id"], "taskNumber": t.get("task_number", ""),
             "title": t["title"], "status": t["status"], "endsAt": t.get("ends_at")}
            for t in input_data["tasks"]])
    else:
        try:
            tasks = fetch_tasks_online(cfg)
        except (CliError, Exception) as e:  # noqa: BLE001 — 网络层任何异常都归入报告
            errors.append(f"任务列表抓取失败: {e}")
            return report

    # 2. 筛选
    targets, skipped = filter_tasks(tasks, cfg["statuses"])
    report["skipped"] = [{"task_number": t["task_number"], "title": t["title"], "status": t["status"]}
                         for t in skipped]

    # 3. skill 目录索引 + source_task 反查表（匹配靠数据）
    slugs, root = list_public_skill_dirs(cfg)
    source_map = {}
    try:
        source_map = scan_source_tasks(cfg, slugs)
    except Exception:
        pass

    # 执行模式先认领工作锁（并行串行化）
    if not cfg["dry_run"] and slugs:
        claim_work(cfg, "platform-upload:%s" % cfg["mode"])
        report["claim"] = cfg["session"]

    for task in targets:
        # 0. 截止闸门（用户规则）：截止日 23:50:59（北京时间）后不再对平台做任何写入
        if is_deadline_passed(task.get("ends_at"), cfg["submit_cutoff_time"]):
            report["skipped"].append({"task_number": task["task_number"], "title": task["title"],
                                      "status": task["status"], "reason": "past_deadline"})
            continue
        # 4. 匹配
        slug, how, why = match_task_to_skill(task, cfg["aliases"], slugs, source_map)
        if not slug:
            report["unmatched"].append({"task_number": task["task_number"],
                                        "title": task["title"], "reason": why})
            continue
        # 5. 资源
        try:
            if input_data.get("skills") is not None and slug in input_data["skills"]:
                res = {"skill": slug, **input_data["skills"][slug]}
            elif input_data.get("skills") is not None:
                raise Blocked(slug, "input_data.skills 未包含该 skill 的资源")
            else:
                res = resolve_skill_resources(cfg, slug)
        except Blocked as b:
            report["blocked"].append({"task_number": task["task_number"],
                                      "skill": b.skill, "reason": b.reason})
            continue
        except UploadTaskError as e:
            errors.append(f"{task['task_number']}/{slug}: {e}")
            continue

        # 6. 计划
        item = build_plan_item(task, res, cfg)
        item["match_how"] = how
        item["notes"] = res.get("notes", [])
        report["targets"].append(item)

        # 7. 执行
        if not cfg["dry_run"]:
            try:
                item.update(execute_upload(cfg, task, res))
            except (CliError, Blocked) as e:
                errors.append(f"{task['task_number']}: 执行失败 {e}")
                item["action"] = "failed"
    if not cfg["dry_run"] and slugs:
        release_claim(cfg)
    return report


# ---------------------------------------------------------------- 演示样例

SAMPLE_TASKS = [  # 演示用样例（形态取自 2026-11-18 线上 API），非真实任务数据
    {"id": "demo-1", "task_number": "TSDEMO0001", "title": "JEV盯盘条件与历史回放的语义能否一致",
     "status": "PENDING"},
    {"id": "demo-2", "task_number": "TSDEMO0002", "title": "AI交易员在异常数据和重复请求下是否守住交易约束",
     "status": "IN_PROGRESS"},
    {"id": "demo-3", "task_number": "TSDEMO0003", "title": "某已完成任务", "status": "COMPLETED"},
]


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="panda-upload-task：量枢院任务成果回填")
    ap.add_argument("--execute", action="store_true", help="真实驱动浏览器（默认 dry_run 只出计划）")
    ap.add_argument("--mode", choices=["draft", "submit"], default="draft",
                    help="draft=保存草稿（默认）；submit=提交审核，需用户明确同意")
    ap.add_argument("--session", default=DEFAULT_CONFIG["session"])
    ap.add_argument("--json", action="store_true", help="报告输出到 stdout（默认即是）")
    args = ap.parse_args(argv)

    cfg = dict(DEFAULT_CONFIG)
    cfg.update({"dry_run": not args.execute, "mode": args.mode,
                "session": args.session, "project_root": os.getcwd()})
    if not args.execute:
        # 离线演示：无浏览器也能出计划；本地无 public/skills 时注入合成资源
        slugs, _ = list_public_skill_dirs(cfg)
        input_data = {"tasks": SAMPLE_TASKS}
        if not slugs:
            input_data["skills"] = {
                "skill-jev-history-replay": {
                    "feature": "JEV 盯盘条件与历史回放语义对齐（演示资源）",
                    "github_url": "https://github.com/quantskills/skill-jev-history-replay",
                    "zip_path": "public/dist/skill-jev-history-replay-v0.0.0.zip",
                    "version": "0.0.0"},
                "skill-constraint-stress-test": {
                    "feature": "约束压力测试（演示资源）",
                    "github_url": "https://github.com/quantskills/skill-constraint-stress-test",
                    "zip_path": "public/dist/skill-constraint-stress-test-v0.0.0.zip",
                    "version": "0.0.0"},
            }
    else:
        input_data = {}
    report = run(input_data, config=cfg)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
