"""Generate pronunciation and explicit-answer-box narration repairs."""

import asyncio
import json
from pathlib import Path

import edge_tts


PHRASES = {
    "pg002_n0008": "Mikocheni Area.",
    "pg047_n0003": "Five minus one equals dash.",
    "pg047_n0005": "Four minus one equals dash.",
    "pg047_n0007": "Three minus one equals dash.",
    "pg047_n0009": "Two minus one equals dash.",
    "pg047_n0011": "One minus one equals dash.",
    "pg047_n0013": "Nine minus five equals dash.",
    "pg047_n0015": "Seven minus three equals dash.",
    "pg047_n0017": "Nine minus six equals dash.",
    "pg047_n0019": "Five minus five equals dash.",
    "pg047_n0021": "Four minus two equals dash.",
    "pg047_n0023": "Seven minus six equals dash.",
    "pg047_n0025": "Six minus four equals dash.",
    "pg047_n0027": "Eight minus three equals dash.",
    "pg047_n0029": "Seven minus five equals dash.",
    "pg047_n0031": "Eight minus seven equals dash.",
    "pg047_n0033": "Five minus two equals dash.",
    "pg047_n0035": "Four minus three equals dash.",
    "pg047_n0037": "Six minus zero equals dash.",
    "pg053_im013_seg001_v1_crop_v1_crop1": "One hand showing five fingers, add one hand showing five fingers, equals two hands showing ten fingers.",
    "pg053_im013_seg002_v1_crop_v1_crop1": "Four pencils, add six pencils, equals ten pencils.",
}


async def main(start: int = 0, limit: int | None = None) -> None:
    root = Path("content/i18n/en-US")
    audios_path = root / "audios.json"
    audios = json.loads(audios_path.read_text(encoding="utf-8"))
    output = root / "audio"
    entries = list(PHRASES.items())
    entries = entries[start:] if limit is None else entries[start:start + limit]
    async def create_clip(text_id: str, phrase: str) -> tuple[str, str, Path]:
        suffix = "guided-example-20260906" if text_id.startswith("pg053_") else "pronunciation-and-dash-20260906"
        target = output / f"{text_id}.{suffix}.mp3"
        await edge_tts.Communicate(phrase, voice="en-US-AriaNeural").save(str(target))
        return text_id, phrase, target

    generated = await asyncio.gather(*(create_clip(text_id, phrase) for text_id, phrase in entries))
    for text_id, phrase, target in generated:
        audios[text_id] = target.name
        print(f"{text_id}: {phrase}")
    audios_path.write_text(json.dumps(audios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    asyncio.run(main(args.start, args.limit))
