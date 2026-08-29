# 更新日志

## v0.1.0 (2026-08-29)

初始发布：

- 定位：元造 —— 端到端造技能脚手架（0 元免费开源，工坊 / 质量与工程线）。输入 `yotta-<名称>` +
  中文名 + 描述，一键生成符合元阁发布规范的技能目录并做结构自检，通过才输出「脚手架合格」。
- CLI：零依赖（Python 3.8+ 标准库）yotta_skill_creator.py —— `create` 子命令：命名校验
  （yotta- 前缀 / 小写连字符 / 元X 规范 / 目标不重复）→ 内嵌模板（SKILL.md / README 中英四方式 /
  package.json / CHANGELOG / LICENSE / NOTICE / install.sh + bin/install.js / .gitignore /
  .npmignore / publish.yml / references / assets）→ 占位符替换 → 结构自检（frontmatter /
  版本四件 / README 四方式 / 无残留占位符 / 围栏配对）；退出码 0 / 2 / 4 / 130。
- 自用模式 --self-use：只生成技能本体（SKILL.md / references / 可选 CLI），不生成任何发布件；
  自检只查技能本体完整性。
- references：cli-reference.md（完整参数 / 命名规则 / 退出码 / 自用模式差异）+
  scaffold-structure.md（生成目录结构与文件用途）+ tutorial.md（中文教程）。
- 测试：20 用例（命名矩阵 / 自检项 / 自用模式 / 占位符替换 / 围栏）Python 3.8 + 3.13 双版本全绿。
- 文档：SKILL.md + README 中英双版 + 四方式安装（发布规范 §3.3.1）。
