# Repository instructions

This repository contains reusable Agent Skills, not a target application's generated documentation.

- Keep each `skills/<name>/SKILL.md` concise, with `name` and `description` frontmatter. Put detailed procedures in references and reusable output templates in assets.
- Use Chinese for user-facing guidance and preserve code symbols and CLI names. Keep triggers understandable in both Chinese and English.
- Maintain one shared contract: `docs-map.json` module glossary references use `modules[].terms`; `glossary.json` has top-level `terms` objects.
- Keep scripts standard-library-only unless a concrete requirement justifies another dependency. Do not silently download or install tools.
- Distinguish code reading, actual test execution, runtime observation and business confirmation. Label synthetic examples and pending evidence.
- Preserve a complete static explanation when adding interactions. Never claim browser or Mermaid verification without running it.
- Add tests for concrete failure modes in reusable scripts. Run `python3 scripts/check_skills.py` and `python3 -m unittest discover -s tests -v` before committing changes.
- Keep test outputs and caches out of version control. Modify only requested content, preserve existing history, and never force-push to resolve a remote mismatch.
