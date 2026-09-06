"""Generate the specific image-description clips required by the QA matrix."""

import asyncio
import json
from pathlib import Path

import edge_tts


DESCRIPTION_IDS = (
    [f"pg026_im010_seg{number:03}_v1" + ("" if number == 5 else "_crop_v1") for number in range(1, 9)]
    + ["pg079_im016_seg001_v1_crop1", "pg079_im016_seg002_v1_crop1"]
    + [f"pg085_im012_seg{number:03}_v1_crop_v1" for number in range(1, 7)]
    + [
        "pg126_im008_seg001_v1_crop1", "pg126_im008_seg002_v1_crop1",
        "pg126_im008_seg003_v1_crop1", "pg126_im008_seg004_v1_crop1",
        "pg126_im008_seg005_v1_crop1", "pg126_im008_seg006_v1_crop1",
        "pg126_im008_seg007_v1_crop_v1_crop1", "pg126_im008_seg008_v1_crop1",
        "pg129_im013", "pg129_im014", "pg129_im018_seg003_v1_crop_v1",
        "pg129_im003", "pg129_im018_seg005_v1_crop1",
        "pg129_im018_seg006_v1_crop_v1_crop1", "pg129_im018_seg007_v1_crop_v1_crop1",
        "pg129_im018_seg008_v1_crop_v1_crop1", "pg129_im018_seg009_v1_crop1",
        "pg129_im018_seg010_v1_crop_v1_crop1",
    ]
)


async def main() -> None:
    root = Path("content/i18n/en-US")
    texts = json.loads((root / "texts.json").read_text(encoding="utf-8"))
    output = root / "audio"
    voice = "en-US-AriaNeural"
    for text_id in DESCRIPTION_IDS:
        target = output / f"{text_id}.matrix-description-20260902.mp3"
        if target.exists() and target.stat().st_size > 500:
            continue
        await edge_tts.Communicate(texts[text_id], voice=voice).save(str(target))
        print(target)


if __name__ == "__main__":
    asyncio.run(main())
