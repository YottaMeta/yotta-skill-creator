#!/usr/bin/env python3
"""yotta-skill-creator 测试：脚手架生成 / 命名校验 / 自用模式 / 结构自检。"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLI = HERE / "yotta_skill_creator.py"
sys.path.insert(0, str(HERE))
import yotta_skill_creator as mod  # noqa: E402


def run_cli(*argv):
    r = subprocess.run([sys.executable, str(CLI)] + list(argv),
                       capture_output=True)
    return r.returncode, r.stdout.decode("utf-8", errors="replace"), \
        r.stderr.decode("utf-8", errors="replace")


class TestBasics(unittest.TestCase):
    def test_version(self):
        code, out, _ = run_cli("--version")
        self.assertEqual(code, 0)
        self.assertIn("yotta-skill-creator", out)

    def test_help(self):
        code, out, _ = run_cli("--help")
        self.assertEqual(code, 0)
        self.assertIn("create", out)

    def test_no_command_fails(self):
        code, _, _ = run_cli()
        self.assertNotEqual(code, 0)


class TestNaming(unittest.TestCase):
    def test_non_yotta_prefix(self):
        with tempfile.TemporaryDirectory() as td:
            code, _, err = run_cli("create", "my-tool", "--zh", "元测",
                                   "--desc", "d", "--out", td)
            self.assertEqual(code, 2)
            self.assertIn("yotta-", err)

    def test_uppercase_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            code, _, err = run_cli("create", "yotta-Bad", "--zh", "元测",
                                   "--desc", "d", "--out", td)
            self.assertEqual(code, 2)

    def test_empty_zh_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            code, _, _ = run_cli("create", "yotta-x", "--zh", "",
                                 "--desc", "d", "--out", td)
            self.assertEqual(code, 2)

    def test_non_yuan_zh_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            code, _, err = run_cli("create", "yotta-x", "--zh", "工具",
                                   "--desc", "d", "--out", td)
            self.assertEqual(code, 2)
            self.assertIn("元", err)


class TestCreate(unittest.TestCase):
    def _create(self, *extra):
        td = tempfile.mkdtemp(prefix="ysc-test-")
        self.addCleanup(shutil.rmtree, td, ignore_errors=True)
        code, out, err = run_cli(
            "create", "yotta-test-a", "--zh", "元测甲",
            "--desc", "测试技能：做什么。触发：用户说 元测甲。边界：不做什么。",
            "--summary", "测试一句话", "--out", td, *extra)
        self.assertEqual(code, 0, err)
        return Path(td) / "yotta-test-a", out

    def test_full_scaffold_files(self):
        d, _ = self._create()
        for rel in ("SKILL.md", "LICENSE", "NOTICE", "README.md",
                    "README.zh-CN.md", "CHANGELOG.md", "package.json",
                    ".gitignore", ".npmignore", "install.sh",
                    "bin/install.js", "references/README.md",
                    "assets/README.md", ".github/workflows/publish.yml"):
            self.assertTrue((d / rel).is_file(), "缺少 " + rel)

    def test_render_maps_skill_template_to_skill_md(self):
        td = tempfile.mkdtemp(prefix="ysc-render-")
        self.addCleanup(shutil.rmtree, td, ignore_errors=True)
        template = Path(td) / "template"
        template.mkdir()
        (template / "SKILL.md.tmpl").write_text(
            "---\nname: {{skill_name}}\n---\n", encoding="utf-8")
        out = Path(td) / "out"

        mod.render(template, out, {"skill_name": "yotta-render-test"},
                   skip_installer=False, with_cli=False, no_banner=False)

        self.assertTrue((out / "SKILL.md").is_file())
        self.assertFalse((out / "SKILL.md.tmpl").exists())

    def test_render_maps_pack_safe_ignore_templates(self):
        td = tempfile.mkdtemp(prefix="ysc-render-")
        self.addCleanup(shutil.rmtree, td, ignore_errors=True)
        template = Path(td) / "template"
        template.mkdir()
        (template / ".gitignore.tmpl").write_text(
            "__pycache__/\n", encoding="utf-8")
        (template / ".npmignore.tmpl").write_text(
            ".npmignore\n", encoding="utf-8")
        out = Path(td) / "out"

        mod.render(template, out, {}, skip_installer=False,
                   with_cli=False, no_banner=False)

        self.assertTrue((out / ".gitignore").is_file())
        self.assertTrue((out / ".npmignore").is_file())
        self.assertFalse((out / ".gitignore.tmpl").exists())
        self.assertFalse((out / ".npmignore.tmpl").exists())

    def test_template_directory_has_no_host_scannable_skill_md(self):
        self.assertFalse((mod.TEMPLATE_DIR / "SKILL.md").exists(),
                         "模板目录不得包含会被宿主递归扫描的 SKILL.md")
        self.assertTrue((mod.TEMPLATE_DIR / "SKILL.md.tmpl").is_file(),
                        "技能模板应以 SKILL.md.tmpl 保存")

    def test_template_ignore_files_use_pack_safe_names(self):
        self.assertTrue((mod.TEMPLATE_DIR / ".gitignore.tmpl").is_file())
        self.assertTrue((mod.TEMPLATE_DIR / ".npmignore.tmpl").is_file())
        self.assertFalse((mod.TEMPLATE_DIR / ".gitignore").exists())
        self.assertFalse((mod.TEMPLATE_DIR / ".npmignore").exists())

    def test_official_installer_preserves_nested_template_payload(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node 不可用")
        td = tempfile.mkdtemp(prefix="ysc-install-")
        self.addCleanup(shutil.rmtree, td, ignore_errors=True)
        installer = HERE.parent / "bin" / "install.js"
        r = subprocess.run([node, str(installer), "--dir", td],
                           capture_output=True)
        self.assertEqual(r.returncode, 0,
                         r.stderr.decode("utf-8", errors="replace"))
        installed = Path(td) / "yotta-skill-creator"
        for rel in ("template/package.json", "template/bin/install.js",
                    "template/SKILL.md.tmpl", "template/.gitignore.tmpl",
                    "template/.npmignore.tmpl"):
            self.assertTrue((installed / rel).is_file(), "缺少安装载荷: " + rel)
        self.assertFalse((installed / "package.json").exists())
        self.assertFalse((installed / "bin").exists())

    def test_template_installer_preserves_nested_payload(self):
        """v0.1.4 回归：模板内的 bin/install.js 与自身安装器同口径（仅顶层跳过）。"""
        node = shutil.which("node")
        if not node:
            self.skipTest("node 不可用")
        td = tempfile.mkdtemp(prefix="ysc-tpl-install-")
        self.addCleanup(shutil.rmtree, td, ignore_errors=True)
        pkg = Path(td) / "pkg"
        rendered = (mod.TEMPLATE_DIR / "bin" / "install.js").read_text(encoding="utf-8")
        rendered = rendered.replace("{{skill_name}}", "yotta-template-probe")
        (pkg / "bin").mkdir(parents=True)
        (pkg / "bin" / "install.js").write_text(rendered, encoding="utf-8")
        (pkg / "SKILL.md").write_text(
            "---\nname: yotta-template-probe\n---\n", encoding="utf-8")
        (pkg / "package.json").write_text(
            '{"name":"@yottameta/yotta-template-probe"}', encoding="utf-8")
        (pkg / "template" / "bin").mkdir(parents=True)
        (pkg / "template" / "package.json").write_text(
            '{"name":"{{skill_name}}"}', encoding="utf-8")
        (pkg / "template" / "bin" / "install.js").write_text(
            "// nested payload", encoding="utf-8")
        out = Path(td) / "out"
        out.mkdir()
        r = subprocess.run([node, str(pkg / "bin" / "install.js"), "--dir", str(out)],
                           capture_output=True)
        self.assertEqual(r.returncode, 0,
                         r.stderr.decode("utf-8", errors="replace"))
        installed = out / "yotta-template-probe"
        self.assertTrue((installed / "SKILL.md").is_file())
        self.assertFalse((installed / "package.json").exists(),
                         "顶层 package.json 应跳过")
        self.assertTrue((installed / "template" / "package.json").is_file(),
                        "嵌套 template/package.json 必须保留")
        self.assertTrue((installed / "template" / "bin" / "install.js").is_file(),
                        "嵌套 template/bin/install.js 必须保留")

    def test_no_leftover_placeholders(self):
        d, _ = self._create()
        for f in d.rglob("*"):
            if f.is_file() and f.suffix in (".md", ".json", ".sh", ".yml", ".yaml", ".js"):
                self.assertNotIn("{{", f.read_text(encoding="utf-8"),
                                 "残留占位符: %s" % f)

    def test_frontmatter_and_package(self):
        d, _ = self._create()
        fm = mod.parse_frontmatter((d / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(fm["name"], "yotta-test-a")
        self.assertEqual(fm["version"], "0.1.0")
        self.assertEqual(fm["license"], "MIT")
        pkg = json.loads((d / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg["name"], "@yottameta/yotta-test-a")
        self.assertEqual(pkg["version"], "0.1.0")

    def test_version_alignment(self):
        d, _ = self._create()
        chg = re.search(r"^##\s*v?([0-9.]+)",
                        (d / "CHANGELOG.md").read_text(encoding="utf-8"), re.M)
        self.assertEqual(chg.group(1), "0.1.0")

    def test_readme_four_ways(self):
        d, _ = self._create()
        for name in ("README.md", "README.zh-CN.md"):
            t = (d / name).read_text(encoding="utf-8")
            for pat in mod.FOUR_WAYS.values():
                self.assertRegex(t, pat, "%s 缺四方式之一" % name)

    def test_with_cli_generates_runnable(self):
        d, _ = self._create("--with-cli")
        cli = d / "scripts" / "yotta_test_a.py"
        self.assertTrue(cli.is_file())
        r = subprocess.run([sys.executable, str(cli), "--version"],
                           capture_output=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("yotta-test-a", r.stdout.decode("utf-8", "replace"))

    def test_skip_installer(self):
        d, _ = self._create("--skip-installer")
        self.assertFalse((d / "install.sh").exists())
        self.assertFalse((d / "bin").exists())
        pkg = json.loads((d / "package.json").read_text(encoding="utf-8"))
        self.assertNotIn("bin", pkg)
        self.assertNotIn("install.sh", pkg["files"])

    def test_no_banner(self):
        d, _ = self._create("--no-banner")
        self.assertFalse((d / "assets").exists())
        pkg = json.loads((d / "package.json").read_text(encoding="utf-8"))
        self.assertNotIn("assets", pkg["files"])

    def test_existing_target_blocked(self):
        d, _ = self._create()
        code, _, err = run_cli("create", "yotta-test-a", "--zh", "元测甲",
                               "--desc", "d", "--out", str(d.parent))
        self.assertEqual(code, 2)
        self.assertIn("已存在", err)


class TestMetaInjectionGuard(unittest.TestCase):
    """v0.1.3：外部元数据不得注入 frontmatter / 生成文件（T09 修复回归）。"""

    def _run(self, desc, summary="一句话", slug="yotta-test-meta"):
        td = tempfile.mkdtemp(prefix="ysc-meta-")
        self.addCleanup(shutil.rmtree, td, ignore_errors=True)
        self._last_td = Path(td)
        return run_cli("create", slug, "--zh", "元测乙",
                       "--desc", desc, "--summary", summary, "--out", td)

    def test_newline_in_desc_rejected(self):
        code, out, err = self._run("第一行\nname: 注入名")
        self.assertEqual(code, 2, out + err)
        self.assertIn("控制字符", err)

    def test_frontmatter_separator_rejected(self):
        code, _out, err = self._run("正常描述 --- 注入")
        self.assertEqual(code, 2)
        self.assertIn("---", err)

    def test_quote_and_backslash_rejected(self):
        for bad in ('描述带引号 "x"', "反斜杠 \\ 注入", "反引号 `注入`"):
            code, _out, err = self._run(bad)
            self.assertEqual(code, 2, bad)
            self.assertIn("保留字符", err)

    def test_valid_desc_roundtrip(self):
        desc = "测试技能：做什么。触发：用户说 元测乙。边界：不做什么。"
        code, _out, err = self._run(desc)
        self.assertEqual(code, 0, err)
        td = self._last_td
        skill = td / "yotta-test-meta" / "SKILL.md"
        fm = mod.parse_frontmatter(skill.read_text(encoding="utf-8"))
        self.assertEqual(fm.get("name"), "yotta-test-meta")
        self.assertEqual(fm.get("description"), desc)
        self.assertEqual(fm.get("version"), "0.1.0")

    def test_readback_detects_extra_key(self):
        td = Path(tempfile.mkdtemp(prefix="ysc-readback-"))
        self.addCleanup(shutil.rmtree, str(td), ignore_errors=True)
        d = td / "yotta-test-meta"
        d.mkdir()
        (d / "SKILL.md").write_text(
            "---\nname: yotta-test-meta\ndescription: \"ok\"\n"
            "version: 0.1.0\nlicense: MIT\ninjected: yes\n---\n",
            encoding="utf-8")
        with self.assertRaises(ValueError):
            mod.verify_generated_frontmatter(d, "yotta-test-meta", "ok")


class TestSelfUse(unittest.TestCase):
    def test_self_use_minimal(self):
        td = tempfile.mkdtemp(prefix="ysc-self-")
        self.addCleanup(shutil.rmtree, td, ignore_errors=True)
        code, out, err = run_cli(
            "create", "yotta-private", "--zh", "元私",
            "--desc", "自用技能。触发：私用。边界：不发布。",
            "--out", td, "--self-use", "--with-cli")
        self.assertEqual(code, 0, err)
        d = Path(td) / "yotta-private"
        for rel in ("SKILL.md", "references/README.md",
                    "scripts/yotta_private.py"):
            self.assertTrue((d / rel).is_file(), "缺少 " + rel)
        for rel in ("README.md", "README.zh-CN.md", "package.json",
                    "CHANGELOG.md", "LICENSE", "NOTICE", "install.sh",
                    "bin", "assets", ".npmignore", ".github"):
            self.assertFalse((d / rel).exists(), "自用模式不应生成 " + rel)
        self.assertIn("自用模式", out)

    def test_self_use_no_placeholder(self):
        td = tempfile.mkdtemp(prefix="ysc-self-")
        self.addCleanup(shutil.rmtree, td, ignore_errors=True)
        code, _, _ = run_cli(
            "create", "yotta-private", "--zh", "元私",
            "--desc", "自用技能。触发：私用。边界：不发布。",
            "--out", td, "--self-use")
        self.assertEqual(code, 0)
        d = Path(td) / "yotta-private"
        for f in d.rglob("*"):
            if f.is_file() and f.suffix == ".md":
                self.assertNotIn("{{", f.read_text(encoding="utf-8"))


class TestSelfCheck(unittest.TestCase):
    def test_self_check_direct(self):
        td = tempfile.mkdtemp(prefix="ysc-check-")
        self.addCleanup(shutil.rmtree, td, ignore_errors=True)
        code = mod.main(["create", "yotta-ok", "--zh", "元可",
                         "--desc", "校验技能。触发：校验。边界：无。",
                         "--out", td])
        self.assertEqual(code, 0)
        d = Path(td) / "yotta-ok"
        errors, warns = mod.self_check(d, "yotta-ok",
                                       skip_installer=False,
                                       with_cli=False, no_banner=False)
        self.assertEqual(errors, [])

    def test_self_check_detects_placeholder(self):
        td = tempfile.mkdtemp(prefix="ysc-check-")
        self.addCleanup(shutil.rmtree, td, ignore_errors=True)
        d = Path(td) / "yotta-ok"
        d.mkdir()
        (d / "SKILL.md").write_text(
            "---\nname: yotta-ok\ndescription: d\nversion: 0.1.0\n"
            "license: MIT\n---\n# x\n{{skill_name}}\n", encoding="utf-8")
        errors, _ = mod.self_check(d, "yotta-ok",
                                   skip_installer=False,
                                   with_cli=False, no_banner=False,
                                   self_use=True)
        self.assertTrue(any("占位符" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
