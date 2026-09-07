"""Regenerate math and abbreviation clips from approved spoken forms."""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import re
from pathlib import Path

import edge_tts


ROOT = Path(__file__).resolve().parents[1]
LOCALE = ROOT / "content" / "i18n" / "en-US"
CONFIG = json.loads((ROOT / "adt-narration-config.json").read_text(encoding="utf-8"))
TRIGGER = re.compile(r"[+=−–÷×_]|(?<=\d)-(?=\d)|\b(?:TIE|ICT|UDSM|UDOM|SQA|OK|ISBN|MARUCo)\b", re.IGNORECASE)


def spoken(identifier: str, source: str) -> str:
    override = CONFIG.get("spoken_overrides", {}).get(identifier)
    if override:
        return str(override)
    value = html.unescape(str(source))
    value = value.replace("\ufffd", "'")
    value = re.sub(r"<span[^>]*adt-blank-line[^>]*>.*?</span>", " dash ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"(?:\[\s*\]|_+)", " dash ", value)
    value = re.sub(r"(?<=\d)\s*[−–-]\s*(?=\d)", " minus ", value)
    value = value.replace("+", " plus ").replace("=", " equals ")
    value = value.replace("÷", " divided by ").replace("×", " multiplied by ")
    for source_word, replacement in CONFIG.get("pronunciations", {}).items():
        value = re.sub(rf"(?<!\w){re.escape(source_word)}(?!\w)", str(replacement), value, flags=re.I)
    return " ".join(value.split())


async def generate(voice: str, suffix: str, dry_run: bool) -> None:
    texts = json.loads((LOCALE / "texts.json").read_text(encoding="utf-8"))
    audio_path = LOCALE / "audios.json"
    audios = json.loads(audio_path.read_text(encoding="utf-8"))
    candidates = {
        identifier: spoken(identifier, value)
        for identifier, value in texts.items()
        if identifier in audios and (TRIGGER.search(str(value)) or identifier in CONFIG.get("spoken_overrides", {}))
    }
    print(f"Approved contextual clips: {len(candidates)}")
    if dry_run:
        for identifier, value in list(candidates.items())[:30]:
            print(f"{identifier}: {value}")
        return

    output = LOCALE / "audio"
    semaphore = asyncio.Semaphore(8)

    async def one(identifier: str, value: str) -> tuple[str, str]:
        filename = f"{identifier}.{suffix}.mp3"
        destination = output / filename
        async with semaphore:
            await edge_tts.Communicate(value, voice=voice).save(str(destination))
        if destination.stat().st_size < 500:
            raise RuntimeError(f"Empty narration clip: {destination}")
        return identifier, filename

    results = await asyncio.gather(*(one(identifier, value) for identifier, value in candidates.items()))
    for identifier, filename in results:
        audios[identifier] = f"{filename}?{suffix}"
    audio_path.write_text(json.dumps(audios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="")
    print(f"Generated {len(results)} contextual narration clips with {voice}.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", default="en-US-GuyNeural")
    parser.add_argument("--suffix", default="contextual-20260907")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(generate(args.voice, args.suffix, args.dry_run))


if __name__ == "__main__":
    main()
