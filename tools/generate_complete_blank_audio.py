"""Generate reviewed narration for sentence-owned blanks and one shared dash.

Visible textbook wording is never changed. The generated clips use the exact
HTML reading order and replace each learner writing space with spoken “dash”.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path

from lxml import html

from audit_blank_narration import audit, is_blank


SUFFIX = "blank-dash-guy-20260912"


def cardinal(value: str) -> str:
    number = int(value)
    ones = [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
        "eighteen", "nineteen",
    ]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    if number < 20:
        return ones[number]
    if number < 100:
        return tens[number // 10] + (f" {ones[number % 10]}" if number % 10 else "")
    if number < 1000:
        return f"{ones[number // 100]} hundred" + (
            f" {cardinal(str(number % 100))}" if number % 100 else ""
        )
    return value


def text_with_blanks(element) -> str:
    parts = [element.text or ""]
    for child in element:
        if is_blank(child):
            parts.append(" dash ")
        else:
            parts.append(text_with_blanks(child))
        parts.append(child.tail or "")
    return "".join(parts)


def spoken_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip()
    marker = re.match(r"^(\d{1,3})\.\s*", value)
    prefix = ""
    if marker:
        prefix = f"Question number {cardinal(marker.group(1))}. "
        value = value[marker.end():]
    value = value.replace("−", " minus ").replace("–", " minus ")
    value = re.sub(r"(?<=\d)\s*-\s*(?=\d)", " minus ", value)
    value = re.sub(r"\s+-\s+", " minus ", value)
    value = value.replace("+", " plus ").replace("=", " equals ")
    value = value.replace("÷", " divided by ").replace("×", " multiplied by ")
    value = re.sub(r"\b\d+\b", lambda match: cardinal(match.group()), value)
    return prefix + re.sub(r"\s+", " ", value).strip(" ,;:")


def build_plan(root: Path, include_generated: bool = False) -> list[dict]:
    report = audit(root)
    rows = report["owner_targets_needing_audio"]
    if include_generated:
        rows = [row for row in report["owner_target_details"] if SUFFIX in row["audio"]]
    documents = {}
    plan = []
    for row in rows:
        page = row["page"]
        document = documents.setdefault(
            page, html.fromstring((root / page).read_text(encoding="utf-8"))
        )
        matches = document.xpath("//*[@data-id=$source_id]", source_id=row["id"])
        if len(matches) != 1:
            raise RuntimeError(f"{page}: expected one source for {row['id']}, found {len(matches)}")
        spoken = spoken_text(text_with_blanks(matches[0]))
        actual_dashes = len(re.findall(r"\bdash\b", spoken, flags=re.IGNORECASE))
        if actual_dashes != row["required_dashes"]:
            raise RuntimeError(
                f"{page} {row['id']}: expected {row['required_dashes']} dashes, got {actual_dashes}: {spoken}"
            )
        plan.append({
            "id": row["id"],
            "page": page,
            "required_dashes": row["required_dashes"],
            "spoken_text": spoken,
            "filename": f"{row['id']}.{SUFFIX}.mp3",
            "review_status": "review",
            "reason": "A printed learner blank must be spoken as dash in its exact sentence position.",
        })
    return plan


async def generate(plan: list[dict], output: Path, voice: str) -> None:
    import edge_tts

    semaphore = asyncio.Semaphore(8)

    async def one(item: dict) -> None:
        target = output / item["filename"]
        async with semaphore:
            await edge_tts.Communicate(item["spoken_text"], voice=voice).save(str(target))
        if not target.exists() or target.stat().st_size < 1_000:
            raise RuntimeError(f"Empty narration file: {target}")

    await asyncio.gather(*(one(item) for item in plan))
    shared = output / f"adt-dash.{SUFFIX}.mp3"
    await edge_tts.Communicate("dash", voice=voice).save(str(shared))
    if not shared.exists() or shared.stat().st_size < 1_000:
        raise RuntimeError(f"Empty shared dash file: {shared}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("book", nargs="?", default=".")
    parser.add_argument("--plan", default="tmp/blank-dash-narration-plan.json")
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--apply-overrides", action="store_true")
    parser.add_argument("--include-generated", action="store_true")
    parser.add_argument("--voice", default="en-US-GuyNeural")
    args = parser.parse_args()

    root = Path(args.book).resolve()
    plan = build_plan(root, include_generated=args.include_generated)
    plan_path = root / args.plan
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PLAN={plan_path}")
    print(f"TARGETS={len(plan)} DASHES={sum(item['required_dashes'] for item in plan)}")
    for item in plan:
        print(f"{item['id']}: {item['spoken_text']}")

    if args.apply_overrides:
        config_path = root / "adt-narration-config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        overrides = config.setdefault("spoken_overrides", {})
        for item in plan:
            overrides[item["id"]] = item["spoken_text"]
            item["review_status"] = "approved"
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"OVERRIDES={len(plan)}")

    if not args.generate:
        return
    output = root / "content/i18n/en-US/audio"
    asyncio.run(generate(plan, output, args.voice))
    audios_path = root / "content/i18n/en-US/audios.json"
    audios = json.loads(audios_path.read_text(encoding="utf-8"))
    for item in plan:
        audios[item["id"]] = item["filename"]
        item["review_status"] = "approved"
    audios_path.write_text(json.dumps(audios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"GENERATED={len(plan) + 1} VOICE={args.voice}")


if __name__ == "__main__":
    main()
