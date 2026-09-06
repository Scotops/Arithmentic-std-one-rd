"""Generate corrected clips for the matrix entries that require math narration.

The source audio was produced before the page markup was cleaned.  This tool
rebuilds only the affected clips and updates their mappings, so a visible
minus sign is always spoken as "minus" and an answer line as "dash".
"""

import asyncio
import argparse
import json
import re
from pathlib import Path

import edge_tts


PAGES = (49, 51, 54, 55, 61, 72, 107, 110, 114, 116, 117, 120, 122)


def cardinal(value: str) -> str:
    number = int(value)
    ones = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    if number < 20:
        return ones[number]
    if number == 100:
        return "one hundred"
    if number < 100:
        return tens[number // 10] + (f"-{ones[number % 10]}" if number % 10 else "")
    return str(number)


def speak_math(text: str) -> str:
    # The web pages intentionally use a presentational span for an answer
    # line. It is not source text and must not leak HTML or CSS into speech.
    text = re.sub(r"<[^>]+>", " ", text)
    label = re.match(r"^\s*(\d{1,2})\.\s*", text)
    prefix = ""
    if label:
        prefix = f"Question number {cardinal(label.group(1))}. "
        text = text[label.end():]
    text = re.sub(r"_{2,}", " dash ", text)
    text = re.sub(r"(?<=\d)\s*[-–−]\s*(?=\d)", " minus ", text)
    # A subtraction sign can begin a money expression, e.g. “− 20 shillings”.
    text = re.sub(r"(^|\s)[−–-]\s*(?=\d)", r"\1minus ", text)
    text = text.replace("+", " plus ").replace("=", " equals ")
    text = re.sub(r"\b\d+\b", lambda match: cardinal(match.group()), text)
    return prefix + re.sub(r"\s+", " ", text).strip()


def needs_rebuilt_clip(value: str) -> bool:
    return (
        "_" in value
        or bool(re.search(r"\d\s*[-–−]\s*\d", value))
        or bool(re.search(r"^[\s−–-]+\d", value))
    )


async def main(start: int = 0, limit: int | None = None) -> None:
    root = Path("content/i18n/en-US")
    texts = json.loads((root / "texts.json").read_text(encoding="utf-8"))
    audios_path = root / "audios.json"
    audios = json.loads(audios_path.read_text(encoding="utf-8"))
    output = root / "audio"
    targets = {"pg002_n0005": "ISBN: nine seven eight dash nine nine eight seven dash zero nine dash nine three three dash seven."}
    targets.update({
        "pg070_n0033": "six",
        "pg070_n0044": "four",
    })
    for page in PAGES:
        prefix = f"pg{page:03}_"
        targets.update({
            key: speak_math(value)
            for key, value in texts.items()
            if key.startswith(prefix) and isinstance(value, str) and needs_rebuilt_clip(value)
        })
    items = list(targets.items())
    if limit is not None:
        items = items[start:start + limit]
    else:
        items = items[start:]
    for text_id, phrase in items:
        target = output / f"{text_id}.matrix-math-20260902.mp3"
        if target.exists() and target.stat().st_size > 500:
            pass
        else:
            await edge_tts.Communicate(phrase, voice="en-US-AriaNeural").save(str(target))
            print(text_id, phrase)
        audios[text_id] = target.name
    audios_path.write_text(json.dumps(audios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    asyncio.run(main(args.start, args.limit))
