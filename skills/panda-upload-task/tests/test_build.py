# -*- coding: utf-8 -*-
"""panda-upload-task tests — 纯函数 + validate + 离线 run + fake-runner 执行链路。"""

import json
import os
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build  # noqa: E402

REAL_README = """# JEV 盯盘条件与历史回放语义对齐

核对 JEV 记录的盯盘判断与一个可复现的历史回放器是否语义一致，并把差异逐项归因。

## ⚠️ 免责声明

- **仅供研究与教育用途**：不构成投资建议。

## 它解决什么问题

同一条盯盘规则、同一份 K 线，JEV 侧记录和自己写的回放器经常对不上。

## 目录结构

```
SKILL.md
```
"""


# ---------------------------------------------------------------- validate_input

def test_validate_input_rejects_bad_shapes():
    with pytest.raises(build.UploadTaskError, match="dict"):
        build.validate_input(["not", "a", "dict"])
    with pytest.raises(build.UploadTaskError, match="未知字段"):
        build.validate_input({"bogus": 1})
    with pytest.raises(build.UploadTaskError, match="缺字段"):
        build.validate_input({"tasks": [{"id": "1"}]})
    with pytest.raises(build.UploadTaskError, match="feature 不得为空"):
        build.validate_input({"skills": {"skill-x": {
            "feature": "", "github_url": "u", "zip_path": "z", "version": "1"}}})
    assert build.validate_input(None) is True
    assert build.validate_input({"tasks": []}) is True


# ---------------------------------------------------------------- 纯函数

def test_filter_tasks():
    tasks = build.normalize_tasks([
        {"id": "a", "taskNumber": "T1", "title": "甲", "status": "PENDING"},
        {"id": "b", "taskNumber": "T2", "title": "乙", "status": "IN_PROGRESS"},
        {"id": "c", "taskNumber": "T3", "title": "丙", "status": "PENDING_REVIEW"},
        {"id": "d", "taskNumber": "T4", "title": "丁", "status": "COMPLETED"},
    ])
    targets, skipped = build.filter_tasks(tasks, ["IN_PROGRESS", "PENDING"])
    assert {t["task_number"] for t in targets} == {"T1", "T2"}
    assert {t["task_number"] for t in skipped} == {"T3", "T4"}


def test_match_task_to_skill_three_levels():
    slugs = {"skill-jev-history-replay", "skill-video-to-text",
             "skill-constraint-stress-test", "skill-intraday-position-manager"}
    aliases = {"task_numbers": {"TS001": "skill-video-to-text"},
               "keywords": build.DEFAULT_CONFIG["aliases"]["keywords"]}

    t = {"id": "x", "task_number": "TS001", "title": "任意标题 JEV"}
    slug, how, _ = build.match_task_to_skill(t, aliases, slugs)
    assert (slug, how) == ("skill-video-to-text", "task_number")  # 编号优先于关键词

    t = {"id": "x", "task_number": "TS999", "title": "JEV盯盘条件与历史回放的语义能否一致"}
    slug, how, _ = build.match_task_to_skill(t, aliases, slugs)
    assert (slug, how) == ("skill-jev-history-replay", "keyword")

    t = {"id": "x", "task_number": "TS999", "title": "视频转文字Skill（video-to-text）"}
    slug, how, _ = build.match_task_to_skill(t, aliases, slugs)
    assert (slug, how) == ("skill-video-to-text", "paren_slug")

    # 边界：标题同时命中两个不同关键词 -> 歧义，必须 unmatched，不得取第一个
    t = {"id": "x", "task_number": "TS999", "title": "带约束的仓位管理是否守住交易约束与JEV"}
    slug, how, why = build.match_task_to_skill(t, aliases, slugs)
    assert slug is None and len(why) > 0

    # 异常输入：完全匹配不上
    t = {"id": "x", "task_number": "TS999", "title": "一个与任何别名无关的新课题"}
    slug, how, why = build.match_task_to_skill(t, aliases, slugs)
    assert slug is None and "aliases" in why


def test_to_https_repo_url():
    assert build.to_https_repo_url("git@github.com:quantskills/skill-jev.git") == \
        "https://github.com/quantskills/skill-jev"
    assert build.to_https_repo_url("https://github.com/quantskills/skill-jev.git") == \
        "https://github.com/quantskills/skill-jev"
    assert build.to_https_repo_url("git@github.com:quantskills/skill-jev") == \
        "https://github.com/quantskills/skill-jev"
    with pytest.raises(build.UploadTaskError):
        build.to_https_repo_url("")


def test_extract_feature_from_readme():
    text = build.extract_feature_from_readme(REAL_README, limit=1200)
    assert text.startswith("JEV 盯盘条件与历史回放语义对齐")
    assert "历史回放器是否语义一致" in text
    assert "它解决什么问题" in text
    assert "免责声明" not in text          # 声明段必须被跳过
    assert "```" not in text
    # 边界：截断
    assert len(build.extract_feature_from_readme(REAL_README, limit=20)) <= 20
    # 异常：空输入
    assert build.extract_feature_from_readme("", 100) == ""


def test_extract_feature_skips_readme_pseudo_h1():
    # 真实事故回归：constraint README 首行是 "# README"，真标题在第二个 h1
    md = ("# README\n\n# AI 交易员约束压力测试与故障注入回放\n\n"
          "当需要评测时，使用此 skill。\n\n## ⚠️ 免责声明\n\n- 略\n\n"
          "## 它解决什么问题\n\n正文一。\n")
    text = build.extract_feature_from_readme(md, 1200)
    assert text.startswith("AI 交易员约束压力测试")
    assert "README" not in text.split("\n\n")[0]
    assert "# " not in text
    # 无任何非 README h1 时回退首个 h1
    only = "# README\n\n简介文本。\n"
    assert build.extract_feature_from_readme(only, 100) == "README\n\n简介文本。"


def test_zip_member_check(tmp_path):
    p = tmp_path / "skill-x-v1.zip"
    with zipfile.ZipFile(p, "w") as zf:
        for f in build.ZIP_REQUIRED_MEMBERS:
            zf.writestr(f"skill-x/{f}", "x")
        zf.writestr("skill-x/output/report.json", "x")  # 夹带
    files, missing, polluted = build.zip_member_check(str(p))
    assert missing == []
    assert "skill-x/output/report.json" in polluted
    assert files == len(build.ZIP_REQUIRED_MEMBERS) + 1


# ---------------------------------------------------------------- run（离线计划）

def _cfg(tmp_path, **over):
    cfg = {"project_root": str(tmp_path), "dry_run": True, "mode": "draft",
           "runner": None}
    cfg.update(over)
    return cfg


def _skills_fixture():
    return {
        "skill-jev-history-replay": {
            "feature": "JEV 对齐工具功能说明", "github_url": "https://github.com/quantskills/skill-jev-history-replay",
            "zip_path": "public/dist/skill-jev-history-replay-v0.16.3.zip", "version": "0.16.3"},
        "skill-constraint-stress-test": {
            "feature": "约束压测功能说明", "github_url": "https://github.com/quantskills/skill-constraint-stress-test",
            "zip_path": "public/dist/skill-constraint-stress-test-v0.1.0.zip", "version": "0.1.0"},
    }


def test_run_dry_run_offline_plan(tmp_path):
    (tmp_path / "public" / "skills" / "skill-jev-history-replay").mkdir(parents=True)
    (tmp_path / "public" / "skills" / "skill-jev-history-replay" / "skill.json").write_text("{}")
    (tmp_path / "public" / "skills" / "skill-constraint-stress-test").mkdir(parents=True)
    (tmp_path / "public" / "skills" / "skill-constraint-stress-test" / "skill.json").write_text("{}")

    tasks = [
        {"id": "1", "task_number": "TS01", "title": "JEV盯盘条件与历史回放的语义能否一致", "status": "PENDING"},
        {"id": "2", "task_number": "TS02", "title": "AI交易员在异常数据和重复请求下是否守住交易约束", "status": "IN_PROGRESS"},
        {"id": "3", "task_number": "TS03", "title": "某已完成任务", "status": "COMPLETED"},
    ]
    rep = build.run({"tasks": tasks, "skills": _skills_fixture()}, config=_cfg(tmp_path))
    assert len(rep["targets"]) == 2 and len(rep["skipped"]) == 1
    jev = next(t for t in rep["targets"] if t["task_number"] == "TS01")
    cst = next(t for t in rep["targets"] if t["task_number"] == "TS02")
    assert any("开始创作" in a for a in jev["actions"])       # PENDING 需先开始创作
    assert not any("开始创作" in a for a in cst["actions"])   # IN_PROGRESS 跳过
    assert any("保存草稿" in a for a in jev["actions"])
    assert jev["match_how"] == "keyword"
    assert rep["blocked"] == [] and rep["unmatched"] == [] and rep["errors"] == []


def _make_skill_dirs(tmp_path):
    for slug in ("skill-jev-history-replay", "skill-constraint-stress-test"):
        d = tmp_path / "public" / "skills" / slug
        d.mkdir(parents=True)
        (d / "skill.json").write_text("{}")


def test_run_mode_submit_and_invalid(tmp_path):
    _make_skill_dirs(tmp_path)
    rep = build.run(
        {"tasks": [{"id": "1", "task_number": "TS01", "title": "JEV盯盘", "status": "IN_PROGRESS"}],
         "skills": _skills_fixture()},
        config=_cfg(tmp_path, mode="submit"))
    assert any("提交审核" in a for a in rep["targets"][0]["actions"])
    with pytest.raises(build.UploadTaskError, match="mode"):
        build.run({"tasks": []}, config=_cfg(tmp_path, mode="yolo"))


def test_run_blocked_and_unmatched(tmp_path):
    # tmp_path 下没有 skill 目录 -> 一切关键词匹配目标都不存在 -> unmatched
    rep = build.run(
        {"tasks": [{"id": "1", "task_number": "TS01", "title": "JEV盯盘语义能否一致", "status": "PENDING"}]},
        config=_cfg(tmp_path))
    assert rep["unmatched"] and rep["targets"] == []

    # 目录存在但 input_data.skills 未包含该 slug -> blocked（不触发 git 探测）
    _make_skill_dirs(tmp_path)
    rep = build.run(
        {"tasks": [{"id": "1", "task_number": "TS01", "title": "JEV盯盘", "status": "PENDING"}],
         "skills": {"skill-zzz-unrelated": {
             "feature": "无关", "github_url": "https://github.com/quantskills/skill-zzz-unrelated",
             "zip_path": "z.zip", "version": "0.0.0"}}},
        config=_cfg(tmp_path))
    assert rep["blocked"] and rep["blocked"][0]["skill"] == "skill-jev-history-replay"


# ---------------------------------------------------------------- dist 版本选择

def test_pick_upload_version_last_published():
    files = ["skill-x-v0.1.0.zip", "skill-x-v0.2.0.zip", "skill-x-v0.3.0.zip",
             "skill-other-v9.9.9.zip", "skill-x-v0.4.0.zip.tmp"]
    # 0.3.0 有 tag -> 最后已发布版本，即使 HEAD=0.2.0
    assert build.pick_upload_version(files, "skill-x", "0.2.0", {"0.3.0"}) == "0.3.0"
    # 无 tag 的 0.3.0 不算已发布 -> 仍取 HEAD 0.2.0
    assert build.pick_upload_version(files, "skill-x", "0.2.0", set()) == "0.2.0"
    # 边界：semver 比较必须按数值（0.17.0 > 0.2.0），不能按字符串
    assert build.pick_upload_version(["skill-x-v0.17.0.zip", "skill-x-v0.2.0.zip"],
                                     "skill-x", "0.1.0", {"0.17.0", "0.2.0"}) == "0.17.0"
    # HEAD 高于 dist 中任何 zip -> 取 HEAD，执行时 archive
    assert build.pick_upload_version(files, "skill-x", "0.5.0", {"0.3.0"}) == "0.5.0"
    assert build.parse_dist_zips(files, "skill-x")[0][1] == "0.1.0"
    assert build.semver_key("0.10.1") > build.semver_key("0.9.9")


# ---------------------------------------------------------------- 截止闸门（用户规则）

def test_is_deadline_passed():
    utc = __import__("datetime").timezone.utc
    DT = __import__("datetime").datetime
    f = build.is_deadline_passed
    ends = "2026-11-18T15:59:59.999Z"        # 北京时间 11-18 23:59:59
    assert f(ends, "23:50:59", DT(2026, 11, 18, 15, 50, 58, tzinfo=utc)) is False   # 北京 23:50:58
    assert f(ends, "23:50:59", DT(2026, 11, 18, 15, 50, 59, tzinfo=utc)) is True    # 北京 23:50:59 即算过
    assert f(ends, "23:50:59", DT(2026, 11, 18, 16, 30, 0, tzinfo=utc)) is True     # 北京次日 00:30
    assert f(None, "23:50:59", DT(2027, 1, 1, tzinfo=utc)) is False                 # 无截止时间不拦截


def test_run_past_deadline_skips_without_any_io(tmp_path):
    calls = []
    def boom_runner(argv, cwd=None, env=None, timeout=60):
        calls.append(argv)
        raise AssertionError("不应触碰外部命令")
    tasks = [{"id": "1", "task_number": "TS01", "title": "JEV盯盘", "status": "PENDING",
              "ends_at": "2026-11-17T15:59:59.999Z"}]   # 已过期
    rep = build.run({"tasks": tasks},
                    config=_cfg(tmp_path, dry_run=False, runner=boom_runner))
    assert rep["targets"] == []
    assert rep["skipped"] and rep["skipped"][0]["reason"] == "past_deadline"
    assert calls == []                                   # 未动 git / 未动浏览器
    assert rep["errors"] == []


# ---------------------------------------------------------------- fake runner 执行链路

JEV_GITHUB = "https://github.com/quantskills/skill-jev-history-replay"


def make_live_runner(state):
    """模拟 opencli browser 子命令。argv[4:] 起是 browser 子命令参数。
    eval 分支返回“原始 JSON 文本”（opencli 对字符串结果不加 envelope）。"""
    def ok(data):
        return json.dumps({"ok": True, "data": data}, ensure_ascii=False)

    def runner(argv, cwd=None, env=None, timeout=60):
        args = argv[4:]
        head = args[0] if args else ""
        if head == "eval":
            js = args[1]
            if "attachment-link" in js:
                return json.dumps({"ok": True, "data": json.dumps(state.get("attachments", []))}, ensure_ascii=False)
            if "tasks?page" in js:
                platform = {"ok": True, "data": {"items": state["items"]}}
            else:
                platform = {"ok": True, "data": {"status": state["detail_status"]}}
            # 线上 opencli 2.0.2：字符串结果仍被 {ok,data} envelope 包裹一层
            return json.dumps({"ok": True, "data": json.dumps(platform, ensure_ascii=False)}, ensure_ascii=False)
        if head == "find":
            css = args[2]
            kind = "textarea" if "textarea" in css else ("file" if "file" in css else "url")
            return ok({"matches_n": 1, "entries": [{"ref": state["refs"][kind], "tag": kind}]})
        if head == "fill":
            state.setdefault("filled", {})[args[1]] = args[2]
            return ok({"filled": True, "verified": True, "actual": args[2]})
        if head == "get":
            ref = args[2]
            vals = {state["refs"]["textarea"]: state["feature_text"],
                    state["refs"]["url"]: state.get("url_value", JEV_GITHUB),
                    state["refs"]["file"]: ""}
            return ok({"value": vals.get(ref, ""), "matches_n": 1, "match_level": "exact"})
        if head == "upload":
            state["uploaded"] = args[2]
            return ok({"uploaded": True, "files": 1, "file_names": [args[2].split("/")[-1]]})
        if head == "click":
            state["clicks"].append(args[-1])
            return ok({"clicked": True, "matches_n": 1, "match_level": "exact"})
        return ok("waited")
    return runner


def _live_cfg(state, mode="draft"):
    return {"session": "t", "base_app_url": "http://x/app", "api_base": "/api/v1",
            "window_url_marker": "x", "mode": mode, "runner": make_live_runner(state)}


def test_execute_upload_with_fake_runner():
    res = _skills_fixture()["skill-jev-history-replay"]
    state = {
        "items": [], "detail_status": "IN_PROGRESS",
        "refs": {"textarea": "9", "url": "10", "file": "11"},
        "clicks": [], "uploaded": None, "filled": {},
        "feature_text": res["feature"],
    }
    task = {"id": "1", "task_number": "TS01", "title": "JEV盯盘语义", "status": "IN_PROGRESS"}
    out = build.execute_upload(_live_cfg(state), task, res)
    assert out["action"] == "draft_saved" and out["verified"]
    assert state["uploaded"] == res["zip_path"]
    assert state["clicks"] == ["填写成果", "保存草稿"]      # IN_PROGRESS 不应点开始创作
    assert state["filled"]["10"] == JEV_GITHUB


def test_attachment_replace_rule_removes_old_zip_uploads_new():
    # 用户规则：线上挂的 zip 是旧版本时，先删旧 zip 再传最新；非 zip 附件不动
    res = _skills_fixture()["skill-jev-history-replay"]
    state = {"items": [], "detail_status": "IN_PROGRESS",
             "refs": {"textarea": "9", "url": "10", "file": "11"},
             "clicks": [], "uploaded": None, "feature_text": res["feature"],
             "attachments": ["skill-jev-history-replay-v0.9.9.zip", "补充说明.md"]}
    out = build.execute_upload(_live_cfg(state),
                               {"id": "1", "task_number": "T", "title": "x", "status": "IN_PROGRESS"}, res)
    assert out["attachments"]["removed"] == ["skill-jev-history-replay-v0.9.9.zip"]
    assert "删除附件 skill-jev-history-replay-v0.9.9.zip" in state["clicks"]
    assert "删除附件 补充说明.md" not in state["clicks"]
    assert state["uploaded"] == res["zip_path"]


def test_attachment_same_name_kept_no_reupload():
    res = _skills_fixture()["skill-jev-history-replay"]
    want = res["zip_path"].split("/")[-1]
    state = {"items": [], "detail_status": "IN_PROGRESS",
             "refs": {"textarea": "9", "url": "10", "file": "11"},
             "clicks": [], "uploaded": None, "feature_text": res["feature"],
             "attachments": [want]}
    out = build.execute_upload(_live_cfg(state),
                               {"id": "1", "task_number": "T", "title": "x", "status": "IN_PROGRESS"}, res)
    assert out["attachments"] == {"uploaded": False, "kept": want, "removed": []}
    assert state["uploaded"] is None


def test_execute_submit_mode_clicks_review():
    res = _skills_fixture()["skill-jev-history-replay"]
    state = {"items": [], "detail_status": "IN_PROGRESS",
             "refs": {"textarea": "9", "url": "10", "file": "11"},
             "clicks": [], "uploaded": None, "feature_text": res["feature"]}
    out = build.execute_upload(_live_cfg(state, mode="submit"),
                               {"id": "1", "task_number": "TS01", "title": "x", "status": "IN_PROGRESS"}, res)
    assert out["action"] == "submitted_for_review"
    assert state["clicks"][-1] == "提交审核"


def test_execute_pending_clicks_start_first():
    res = _skills_fixture()["skill-jev-history-replay"]
    state = {"items": [], "detail_status": "PENDING",
             "refs": {"textarea": "9", "url": "10", "file": "11"},
             "clicks": [], "uploaded": None, "feature_text": res["feature"]}
    runner = make_live_runner(state)
    orig = state  # 点击开始创作后由页面把状态推进：包装 runner 在第二次详情读取时改状态

    calls = {"n": 0}

    def runner2(argv, cwd=None, env=None, timeout=60):
        if argv[4:5] == ["eval"] and "/tasks/1" in argv[5]:
            calls["n"] += 1
            if calls["n"] >= 2:
                state["detail_status"] = "IN_PROGRESS"
        return runner(argv, cwd=cwd, env=env, timeout=timeout)

    cfg = _live_cfg(state)
    cfg["runner"] = runner2
    build.execute_upload(cfg, {"id": "1", "task_number": "TS01", "title": "x", "status": "PENDING"}, res)
    assert state["clicks"][0] == "开始创作"
    assert "填写成果" in state["clicks"] and "保存草稿" in state["clicks"]


def test_url_verify_mismatch_raises():
    res = _skills_fixture()["skill-jev-history-replay"]
    state = {"items": [], "detail_status": "IN_PROGRESS",
             "refs": {"textarea": "9", "url": "10", "file": "11"},
             "clicks": [], "uploaded": None, "feature_text": res["feature"],
             "url_value": "https://wrong.example/x"}
    with pytest.raises(build.CliError, match="回读不一致"):
        build.execute_upload(_live_cfg(state), {"id": "1", "task_number": "T", "title": "x", "status": "IN_PROGRESS"}, res)


def test_cli_error_envelope_raises():
    def runner(argv, cwd=None, env=None, timeout=60):
        return json.dumps({"ok": False, "error": {"code": "not_found", "message": "gone"}})
    with pytest.raises(build.CliError, match="not_found"):
        build.cli({"session": "s", "runner": runner}, "state")
