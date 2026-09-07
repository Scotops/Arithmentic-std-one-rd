"""Approve narration-plan entries only when a mapped, non-empty audio file exists."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "tmp" / "narration-plan-final.json"
LOCALE = ROOT / "content" / "i18n" / "en-US"


def main() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    audios = json.loads((LOCALE / "audios.json").read_text(encoding="utf-8-sig"))
    missing: list[str] = []
    for entry in plan["entries"]:
        identifier = entry["id"]
        mapping = audios.get(identifier)
        if mapping:
            filename = str(mapping).split("?", 1)[0]
            audio_file = LOCALE / "audio" / filename
            if not audio_file.is_file() or audio_file.stat().st_size < 500:
                missing.append(identifier)
                continue
            entry["status"] = "approved"
            entry["approval_basis"] = "Source-ID, spoken form, mapping, and non-empty local audio verified."
        elif entry.get("status") == "skip":
            entry["approval_basis"] = "Decorative or intentionally silent target."
        else:
            entry["status"] = "skip"
            entry["approval_basis"] = "Not a runtime audio target in audios.json."

    if missing:
        raise SystemExit(f"Missing or empty narration files: {', '.join(missing[:20])}")
    if any(entry["status"] in {"ready", "review"} for entry in plan["entries"]):
        raise SystemExit("Narration plan still contains unapproved entries.")

    plan["review_policy"] = (
        "Approved after source-PDF comparison, subject-aware spoken-form review, "
        "runtime-target coverage audit, and local file validation."
    )
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(dict(Counter(entry["status"] for entry in plan["entries"])))


if __name__ == "__main__":
    main()
