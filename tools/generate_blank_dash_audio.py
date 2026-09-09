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
UNDERLINE_ELEMENT = re.compile(
    r"<span\b(?=[^>]*\baria-hidden=[\"']true[\"'])(?=[^>]*\bborder-bottom)[^>]*>.*?</span>",
    re.IGNORECASE | re.DOTALL,
)
TAG = re.compile(r"<[^>]+>")
INLINE_UNDERLINE_ID = re.compile(
    r'data-id="([^"]+)"[^>]*>(?:(?!data-id=).)*?'
    r'aria-hidden=["\']true["\'](?:(?!data-id=).)*?border-bottom',
    re.IGNORECASE | re.DOTALL,
)


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
    # Some later exercise tables keep the printed question marker and its
    # equation in one reading item ("1. 26 - 20 = [blank]").  Make that
    # marker unambiguous for a child before spelling out the calculation.
    marker = re.match(r"^\s*(\d{1,2})\.\s*", value)
    prefix = ""
    if marker:
        prefix = f"Question number {cardinal(marker.group(1))}. "
        value = value[marker.end():]
    text = BLANK_ELEMENT.sub(" dash ", value)
    text = UNDERLINE_ELEMENT.sub(" dash ", text)
    text = BLANK_PATTERN.sub(" dash ", text)
    text = re.sub(r"(?<!\w)_(?!\w)", " dash ", text)
    text = html.unescape(TAG.sub(" ", text)).replace("&nbsp;", " ")
    text = re.sub(r"[−–-]", " minus ", text)
    text = text.replace("+", " plus ").replace("=", " equals ")
    text = re.sub(r"\b\d+\b", lambda match: cardinal(match.group()), text)
    return prefix + re.sub(r"\s+", " ", text).strip(" ,;:")


async def generate(entries: list[tuple[str, str]], output: Path) -> list[tuple[str, Path, str]]:
    semaphore = asyncio.Semaphore(10)

    async def one(text_id: str, text: str) -> tuple[str, Path, str]:
        target = output / f"{text_id}.blank-dash-20260906.mp3"
        async with semaphore:
            await edge_tts.Communicate(text, voice="en-US-AriaNeural").save(str(target))
        return text_id, target, text

    return await asyncio.gather(*(one(text_id, text) for text_id, text in entries))


def main(start: int, limit: int | None, dry_run: bool, only_unmapped: bool,
         only_question_labels: bool) -> None:
    root = Path("content/i18n/en-US")
    texts = json.loads((root / "texts.json").read_text(encoding="utf-8"))
    inline_underline_ids = set()
    for page in Path(".").glob("pg*.html"):
        inline_underline_ids.update(INLINE_UNDERLINE_ID.findall(page.read_text(encoding="utf-8")))

    matches = []
    for text_id, value in texts.items():
        has_blank = BLANK_PATTERN.search(value) or UNDERLINE_ELEMENT.search(value) or str(value).strip() == "_"
        if has_blank or text_id in inline_underline_ids:
            # Older source pages keep the drawn blank only in the HTML, while
            # the localized string contains the visible numbers. Add its
            # equivalent dash only to spoken narration.
            source = value if has_blank else f"{value} <span class='adt-blank-line'></span>"
            matches.append((text_id, spoken_text(source)))
    if only_unmapped:
        mappings = json.loads((root / "audios.json").read_text(encoding="utf-8"))
        matches = [item for item in matches if not str(mappings.get(item[0], "")).endswith(".blank-dash-20260906.mp3")]
    if only_question_labels:
        matches = [item for item in matches if item[1].startswith("Question number ")]
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
    parser.add_argument("--only-unmapped", action="store_true")
    parser.add_argument("--only-question-labels", action="store_true")
    args = parser.parse_args()
    main(args.start, args.limit, args.dry_run, args.only_unmapped, args.only_question_labels)
