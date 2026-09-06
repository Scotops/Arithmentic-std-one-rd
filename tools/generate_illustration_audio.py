"""Create child-friendly narration clips for repaired illustration labels."""

import argparse
import asyncio
import json
from pathlib import Path

import edge_tts


IDS = (
    "pg029_im009", "pg029_im010", "pg029_im011",
    "pg031_im010_seg001_v1_crop1", "pg031_im010_seg002_v1_crop1", "pg031_im010_seg003_v1_crop1",
    "pg042_im018_seg001_v1_crop1", "pg042_im018_seg002_v1_crop1",
    "pg042_im018_seg003_v1_crop1", "pg042_im018_seg004_v1_crop1",
    "pg054_im010_seg001_v1_crop1", "pg054_im006_crop1", "pg054_im010_seg002_v1_crop1",
    "pg054_im009_crop1", "pg054_im010_seg003_v1_crop1_crop1",
    "pg080_im003", "pg080_im004", "pg080_im009", "pg080_im011", "pg080_im012",
    "pg131_im005_crop1", "pg132_im006", "pg132_im008_crop_v1",
)


async def main(start: int = 0, limit: int | None = None) -> None:
    root = Path("content/i18n/en-US")
    texts = json.loads((root / "texts.json").read_text(encoding="utf-8"))
    audios_path = root / "audios.json"
    audios = json.loads(audios_path.read_text(encoding="utf-8"))
    selected = IDS[start:start + limit] if limit else IDS[start:]
    output = root / "audio"

    for text_id in selected:
        target = output / f"{text_id}.kid-friendly-illustration-20260905.mp3"
        if not target.exists() or target.stat().st_size <= 500:
            await edge_tts.Communicate(texts[text_id], voice="en-US-AriaNeural").save(str(target))
            print(text_id, texts[text_id])
        audios[text_id] = target.name
    audios_path.write_text(json.dumps(audios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    asyncio.run(main(args.start, args.limit))
