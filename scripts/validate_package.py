#!/usr/bin/env python3
"""Validate the English package, local links, identity, and optional frozen baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".txt"}


def package_files(root):
    return sorted(p for p in root.rglob("*") if p.is_file()
                  and not {".git", "__pycache__", ".venv", "node_modules"}.intersection(p.relative_to(root).parts)
                  and p.suffix != ".pyc")


def language_metrics(root):
    found = {}
    for path in package_files(root):
        if path.suffix in TEXT_SUFFIXES or path.name == "LICENSE":
            count = len(re.findall(r"[\u3400-\u9fff]", path.read_text(encoding="utf-8")))
            if count:
                found[str(path.relative_to(root))] = count
    return {"cjk_files": len(found), "cjk_characters": sum(found.values()), "files": found}


def trigger_smoke(root):
    cases = json.loads((root/"evals/trigger_cases.json").read_text())
    results = []
    for family, expected in (("should_trigger", True), ("should_not_trigger", False), ("near_neighbor", False)):
        for case in cases[family]:
            text = case["text"].lower()
            matched = [concept for concept, words in cases["positive_concepts"].items()
                       if any(word.lower() in text for word in words)]
            score = len(matched)/len(cases["positive_concepts"])
            excluded = any(pattern.lower() in text for pattern in cases["negative_patterns"])
            predicted = score >= cases["recommended_threshold"] and not excluded
            results.append({"family": case["family"], "passed": predicted == expected})
    return {"ok": all(item["passed"] for item in results), "total": len(results),
            "passed": sum(item["passed"] for item in results), "cases": results,
            "scope": "Lexical configuration smoke test, not measured model-routing accuracy"}


def validate(root, baseline=None):
    failures = []
    required = ["SKILL.md", "README.md", "LICENSE", "manifest.json", "agents/openai.yaml",
                "agents/interface.yaml", "references/svg-contract.md", "evals/trigger_cases.json"]
    for name in required:
        if not (root/name).is_file():
            failures.append("Missing file: " + name)
    if failures:
        return {"ok": False, "failures": failures}
    manifest = json.loads((root/"manifest.json").read_text())
    skill = (root/"SKILL.md").read_text()
    name = re.search(r"(?m)^name: (.+)$", skill)
    version = re.search(r'(?m)^  version: "([^"]+)"$', skill)
    if not name or name[1] != manifest["name"] or root.name != manifest["name"]:
        failures.append("Entrypoint, directory, and manifest names must match")
    if not version or version[1] != manifest["version"]:
        failures.append("Skill and manifest versions must match")
    for target in ("SKILL.md", "README.md", "agents/openai.yaml", "agents/interface.yaml"):
        if manifest["display_name"] not in (root/target).read_text():
            failures.append("Display name missing from " + target)
    files = package_files(root)
    single_entrypoint = [str(p.relative_to(root)) for p in files if p.name == "SKILL.md"] == ["SKILL.md"]
    if not single_entrypoint:
        failures.append("Exactly one root SKILL.md is required")
    language = language_metrics(root)
    if language["cjk_files"]:
        failures.append("Non-English CJK text remains in package files")
    triggers = trigger_smoke(root)
    if not triggers["ok"]:
        failures.append("Trigger smoke cases failed")
    private = re.compile(r"/(?:Users|home)/[^/\s]+/")
    for path in files:
        if path.suffix in TEXT_SUFFIXES:
            content = path.read_text(encoding="utf-8")
            if private.search(content):
                failures.append("Private absolute path in " + str(path.relative_to(root)))
            if path.suffix == ".json":
                json.loads(content)
            if path.suffix == ".md":
                for link in re.findall(r"\]\(([^)]+)\)", content):
                    if link.startswith(("https://", "http://", "#", "mailto:")):
                        continue
                    target = link.split("#", 1)[0]
                    if not (path.parent/target).exists():
                        failures.append("Broken local link in " + str(path.relative_to(root)) + ": " + target)
    comparison = None
    if baseline:
        preserved = {}
        for subject in ("chromosome", "mitochondrion", "pipette"):
            for suffix in ("svg", "png"):
                relative = Path("assets/examples")/subject/("asset."+suffix)
                preserved[str(relative)] = (root/relative).read_bytes() == (baseline/relative).read_bytes()
        if not all(preserved.values()):
            failures.append("Existing vector or preview changed during language refinement")
        palettes = {str(Path("assets/examples")/subject/"palette.json"):
                    (root/"assets/examples"/subject/"palette.json").read_bytes() == (baseline/"assets/examples"/subject/"palette.json").read_bytes()
                    for subject in ("chromosome", "mitochondrion", "pipette")}
        core_tools = {str(Path("scripts")/name): (root/"scripts"/name).read_bytes() == (baseline/"scripts"/name).read_bytes()
                      for name in ("asset_tool.py", "codex_reference.py")}
        if not all(palettes.values()) or not all(core_tools.values()):
            failures.append("Core vector/image tools or palettes changed during language refinement")
        comparison = {"baseline_language": language_metrics(baseline),
                      "candidate_language": language,
                      "native_assets_byte_identical": preserved,
                      "palette_files_byte_identical": palettes,
                      "core_tool_files_byte_identical": core_tools,
                      "baseline_skill_bytes": (baseline/"SKILL.md").stat().st_size,
                      "candidate_skill_bytes": len(skill.encode())}
    return {"ok": not failures, "name": manifest["name"], "version": manifest["version"],
            "display_name": manifest["display_name"], "failures": failures,
            "language": language, "single_entrypoint": single_entrypoint, "trigger_smoke": triggers,
            "baseline_comparison": comparison,
            "evidence_scope": "Package language, identity, links, and unchanged fixtures; not a model or scientific-quality evaluation."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, help="Frozen package directory for optional preservation checks")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = validate(ROOT, args.baseline)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2)+"\n")
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
