"""Regenerate book narration entries containing an answer blank as “dash”."""

import argparse
import asyncio
import html
import json
import re
from pathlib import Path

import edge_tts


BLANK_PATTERN = re.compile(
    r"adt-blank-line|(?:\[\s*\]|_{2,})", re.IGNORECASE
)
BLANK_ELEMENT = re.compile(
    r"<span\b[^>]*\badt-blank-line\b[^>]*>.*?</span>", re.IGNORECASE | re.DOTALL
)
TAG = re.compile(r"<[^>]+>")


def cardinal(value: str) -> str:
    number = int(value)
    ones = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
            "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
            "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    if number < 20:
        return ones[number]
    if number < 100:
        return tens[number // 10] + (f" {ones[number % 10]}" if number % 10 else "")
    if number < 1000:
        return f"{ones[number // 100]} hundred" + (f" {cardinal(str(number % 100))}" if number % 100 else "")
    return value


def spoken_text(value: str) -> str:
    text = BLANK_ELEMENT.sub(" dash ", value)
    text = BLANK_PATTERN.sub(" dash ", text)
    text = html.unescape(TAG.sub(" ", text)).replace("&nbsp;", " ")
    text = re.sub(r"[−–-]", " minus ", text)
    text = text.replace("+", " plus ").replace("=", " equals ")
    text = re.sub(r"\b\d+\b", lambda match: cardinal(match.group()), text)
    return re.sub(r"\s+", " ", text).strip(" ,;:")


async def generate(entries: list[tuple[str, str]], output: Path) -> list[tuple[str, Path, str]]:
    semaphore = asyncio.Semaphore(10)

    async def one(text_id: str, text: str) -> tuple[str, Path, str]:
        target = output / f"{text_id}.blank-dash-20260906.mp3"
        async with semaphore:
            await edge_tts.Communicate(text, voice="en-US-AriaNeural").save(str(target))
        return text_id, target, text

    return await asyncio.gather(*(one(text_id, text) for text_id, text in entries))


def main(start: int, limit: int | None, dry_run: bool) -> None:
    root = Path("content/i18n/en-US")
    texts = json.loads((root / "texts.json").read_text(encoding="utf-8"))
    matches = [(text_id, spoken_text(value)) for text_id, value in texts.items() if BLANK_PATTERN.search(value)]
    selected = matches[start:] if limit is None else matches[start:start + limit]
    print(f"TOTAL={len(matches)} SELECTED={len(selected)}")
    if dry_run:
        for text_id, text in selected:
            print(f"{text_id}: {text}")
        return
    generated = asyncio.run(generate(selected, root / "audio"))
    audios_path = root / "audios.json"
    audios = json.loads(audios_path.read_text(encoding="utf-8"))
    for text_id, target, text in generated:
        audios[text_id] = target.name
        print(f"{text_id}: {text}")
    audios_path.write_text(json.dumps(audios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(args.start, args.limit, args.dry_run)
