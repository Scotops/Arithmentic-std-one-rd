"""Generate neural narration for explicitly selected text IDs."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import edge_tts


ROOT = Path(__file__).resolve().parents[1]
LOCALE_ROOT = ROOT / "content" / "i18n" / "en-US"


async def generate(ids: list[str], suffix: str, voice: str) -> None:
    texts = json.loads((LOCALE_ROOT / "texts.json").read_text(encoding="utf-8"))
    audio_path = LOCALE_ROOT / "audios.json"
    audios = json.loads(audio_path.read_text(encoding="utf-8"))
    output = LOCALE_ROOT / "audio"
    semaphore = asyncio.Semaphore(8)

    async def one(text_id: str) -> tuple[str, str]:
        if text_id not in texts:
            raise KeyError(f"Unknown text ID: {text_id}")
        filename = f"{text_id}.{suffix}.mp3"
        destination = output / filename
        async with semaphore:
            await edge_tts.Communicate(str(texts[text_id]), voice=voice).save(
                str(destination)
            )
        if destination.stat().st_size < 500:
            raise RuntimeError(f"Generated clip is empty: {destination}")
        return text_id, filename

    results = await asyncio.gather(*(one(text_id) for text_id in ids))
    for text_id, filename in results:
        audios[text_id] = f"{filename}?{suffix}"
        print(f"{text_id}: {texts[text_id]}")
    audio_path.write_text(
        json.dumps(audios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ids", nargs="+")
    parser.add_argument("--suffix", default="reader-fix-20260906")
    parser.add_argument("--voice", default="en-US-AriaNeural")
    args = parser.parse_args()
    asyncio.run(generate(args.ids, args.suffix, args.voice))


if __name__ == "__main__":
    main()
