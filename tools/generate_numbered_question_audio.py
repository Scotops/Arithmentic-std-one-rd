"""Give every combined numbered question a clear spoken question marker.

The textbook uses two patterns for questions: a standalone label (``1.``)
followed by its content, and a single text item such as ``1. 26 + 71 = []``.
Standalone labels use the shared ``question-number-N.mp3`` clip.  This helper
rebuilds the second pattern so it starts with "Question number N" as well.
"""

import asyncio
import argparse
import json
import re
from pathlib import Path

import edge_tts


ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def cardinal(value: str) -> str:
    number = int(value)
    if number < 20:
        return ONES[number]
    if number < 100:
        return TENS[number // 10] + (f"-{ONES[number % 10]}" if number % 10 else "")
    if number < 1_000:
        return f"{ONES[number // 100]} hundred" + (f" {cardinal(str(number % 100))}" if number % 100 else "")
    return value


def spoken_question(value: str) -> str | None:
    plain = re.sub(r"<[^>]+>", " ", value)
    match = re.match(r"^\s*(\d{1,3})\.\s*(.+?)\s*$", plain, re.S)
    if not match:
        return None
    number, body = match.groups()
    body = re.sub(r"(?:\[\s*\]|_{2,})", " dash ", body)
    body = body.replace("�", " minus ")
    body = re.sub(r"(?<=\d)\s*[-–−]\s*(?=\d)", " minus ", body)
    body = body.replace("+", " plus ").replace("=", " equals ").replace("÷", " divided by ").replace("×", " multiplied by ")
    body = re.sub(r"\b\d+\b", lambda item: cardinal(item.group()), body)
    body = re.sub(r"\s+", " ", body).strip(" .")
    return f"Question number {cardinal(number)}. {body}."


async def main(start: int = 0, limit: int | None = None) -> None:
    root = Path("content/i18n/en-US")
    texts = json.loads((root / "texts.json").read_text(encoding="utf-8"))
    audios_path = root / "audios.json"
    audios = json.loads(audios_path.read_text(encoding="utf-8"))
    output = root / "audio"
    targets = []
    for text_id, value in texts.items():
        if not isinstance(value, str):
            continue
        phrase = spoken_question(value)
        if not phrase:
            continue
        targets.append((text_id, phrase))
    targets = targets[start:] if limit is None else targets[start:start + limit]
    count = 0
    for text_id, phrase in targets:
        target = output / f"{text_id}.question-number-20260906.mp3"
        if not target.exists() or target.stat().st_size <= 500:
            await edge_tts.Communicate(phrase, voice="en-US-AriaNeural").save(str(target))
        audios[text_id] = target.name
        count += 1
    audios_path.write_text(json.dumps(audios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {count} numbered-question clips.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    asyncio.run(main(args.start, args.limit))
