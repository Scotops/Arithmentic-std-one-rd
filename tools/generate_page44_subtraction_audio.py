"""Create the complete child-friendly narration for page 44 picture questions."""

import asyncio
import json
from pathlib import Path

import edge_tts


IDS = (
    "pg044_im022_crop1", "pg044_n0006",
    "pg044_im023_crop1", "pg044_n0011",
    "pg044_im024_crop1", "pg044_n0016",
)


async def main() -> None:
    root = Path("content/i18n/en-US")
    texts = json.loads((root / "texts.json").read_text(encoding="utf-8"))
    audios_path = root / "audios.json"
    audios = json.loads(audios_path.read_text(encoding="utf-8"))
    output = root / "audio"
    for text_id in IDS:
        target = output / f"{text_id}.complete-subtraction-20260906.mp3"
        await edge_tts.Communicate(texts[text_id], voice="en-US-AriaNeural").save(str(target))
        audios[text_id] = target.name
        print(f"{text_id}: {texts[text_id]}")
    audios_path.write_text(json.dumps(audios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
