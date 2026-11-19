#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_skill — BUILD skill 版本单源 + 结构合规校验（panda-builder 工具）。

用法：
    python3 skills/panda-builder/scripts/validate_skill.py <skill目录> [--ref HEAD]

--ref 给定时从 git blob 读取（发布工作区按 HEAD 校验）；否则读工作树。
退出码：0 通过；1 有 fail 项；2 用法错误。
校验项：
  1. 八件套 + agents/ 三适配器齐全
  2. skill.json name == 目录名 == SKILL.md frontmatter name
  3. 版本单源：skill.json == CHANGELOG 首个条目 == agents/openai.yaml
     （SKILL.md 若声明 version 也一并比对）
  4. license：LICENSE 为 GPLv3 全文；skill.json license=GPL-3.0-only
  5. README.md 含「## ⚠️ 免责声明」；README.en.md 含 Disclaimer 标题
纯标准库；可被 panda-upload-task / CI / panda-publisher 阶段二共用。
"""

import argparse
import json
import os
import re
import subprocess
import sys

ROOT_FILES = ["SKILL.md", "README.md", "README.en.md", "LICENSE", "INSTALL.md",
              "requirements.txt", "skill.json", "CHANGELOG.md"]
AGENT_FILES = ["agents/cursor-rule.mdc", "agents/portable-loader.md", "agents/openai.yaml"]


def make_reader(path, ref=None):
    if ref:
        def read(rel):
            p = subprocess.run(["git", "-C", path, "show", f"{ref}:{rel}"],
                               capture_output=True, text=True)
            return p.stdout if p.returncode == 0 else None
        return read
    def read(rel):
        fp = os.path.join(path, rel)
        try:
            with open(fp, encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None
    return read


def semver(v):
    return tuple(int(p) if p.isdigit() else 0 for p in (v or "").split("."))


def check_skill(path, ref=None):
    """返回 (fails, version)。fails 为人类可读问题列表。"""
    read = make_reader(path, ref)
    slug = os.path.basename(os.path.normpath(path))
    fails = []

    for rel in ROOT_FILES + AGENT_FILES:
        if read(rel) is None:
            fails.append(f"缺文件: {rel}")

    sj_raw = read("skill.json")
    version = None
    if sj_raw:
        try:
            sj = json.loads(sj_raw)
        except ValueError:
            sj = {}
            fails.append("skill.json 不是合法 JSON")
        version = sj.get("version")
        if sj.get("name") != slug:
            fails.append(f"skill.json name={sj.get('name')!r} 与目录名 {slug} 不一致")
        if sj.get("license") != "GPL-3.0-only":
            fails.append(f"skill.json license={sj.get('license')!r} 必须 GPL-3.0-only")

    sk = read("SKILL.md") or ""
    m = re.search(r"^name:\s*(\S+)", sk, re.M)
    if m and m.group(1) != slug:
        fails.append(f"SKILL.md frontmatter name={m.group(1)} 与目录名不一致")
    mv = re.search(r"^version:\s*([0-9.]+)", sk, re.M)
    if mv and version and mv.group(1) != version:
        fails.append(f"SKILL.md version={mv.group(1)} vs skill.json {version} 漂移")

    chlog = read("CHANGELOG.md") or ""
    mc = re.search(r"^## \[(\d+\.\d+\.\d+)\]", chlog, re.M)
    if mc and version and mc.group(1) != version:
        fails.append(f"CHANGELOG 当前条目={mc.group(1)} vs skill.json {version} 漂移")

    oy = read("agents/openai.yaml") or ""
    my = re.search(r"^\s*version:\s*[\"']?(\d+\.\d+\.\d+)", oy, re.M)
    if my and version and my.group(1) != version:
        fails.append(f"openai.yaml version={my.group(1)} vs skill.json {version} 漂移")

    lic_raw = read("LICENSE") or ""
    lic = lic_raw.lstrip()
    if lic_raw and not lic.startswith("GNU GENERAL PUBLIC LICENSE"):
        fails.append(f"LICENSE 首个非空行不是「GNU GENERAL PUBLIC LICENSE」（实际: {lic.splitlines()[0][:40] if lic else ''}）")

    rm = read("README.md") or ""
    if rm and "## ⚠️ 免责声明" not in rm:
        fails.append("README.md 缺「## ⚠️ 免责声明」")
    ren = read("README.en.md") or ""
    if ren and not re.search(r"^#+ .*(Disclaimer|免责声明)", ren, re.M | re.I):
        fails.append("README.en.md 缺英文免责声明")

    for d in ("开发产物", "生产产物"):
        if read(f"{d}/SKILL.md") is not None or os.path.isdir(os.path.join(path, d)):
            fails.append(f"存在禁用交付目录 {d}/（panda-builder §10）")

    return fails, version


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--ref", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.path):
        print(f"目录不存在: {args.path}", file=sys.stderr)
        return 2
    fails, version = check_skill(args.path, args.ref)
    if args.json:
        print(json.dumps({"path": args.path, "ref": args.ref, "version": version,
                          "fails": fails}, ensure_ascii=False, indent=1))
    else:
        if fails:
            for f in fails:
                print("FAIL:", f)
        else:
            print(f"PASS {os.path.basename(args.path)} v{version}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
