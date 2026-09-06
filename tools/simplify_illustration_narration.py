"""Replace positional illustration narration with simple child-friendly labels."""

import asyncio
import argparse
import json
from pathlib import Path

import edge_tts


REPLACEMENTS = {
    "pg045_im011_seg003_v1": "Nine blue tablets. Six tablets are taken away. Three tablets remain. Nine minus six equals dash.",
    "pg052_im029_crop_v1": "A number grid from one to ten.",
    "pg010_im028": "A blue ballpoint pen.",
    "pg015_im013_seg002_v1_crop_v1": "Four watermelons.",
    "pg074_im016": "A blue cylinder.",
    "pg070_im018": "Chapter Eleven: Arranging numbers sequentially.",
    "pg074_im015": "A blue pipe.",
    "pg039_im007": "Five circles and the equation two plus three.",
    "pg039_im006": "The equation two plus three and six empty circles.",
    "pg016_im018": "Chapter Three: Reading numbers from one to nine.",
    "pg025_im026_seg002_v1_crop_v1_crop2": "Two tomatoes and a dashed line.",
    "pg028_im023_seg001_v1_crop1_crop1": "Three bananas plus five bananas equals eight bananas.",
    "pg115_im006_crop_v1": "Seventy-two minus thirty-eight equals thirty-four.",
    "pg025_im026_seg004_v1_crop1_crop1": "Five red apples. Number five.",
    "pg045_im011_seg002_v1": "Nine flash drives. Eight flash drives are taken away. One flash drive remains. Nine minus eight equals dash.",
    "pg095_im007_crop_v1_crop1": "Two blue arrows and one red arrow.",
    "pg106_im019": "Chapter Fourteen: Subtracting numbers not exceeding ninety-nine.",
    "pg051_im008_seg003_v1_crop_v1_crop1": "Eight minus dash equals three.",
    "pg028_im022": "Chapter Six: Addition.",
    "pg051_im006": "Five empty circles and the subtraction expression five minus two.",
    "pg051_im007": "Five circles. Two circles are empty and three circles are brown. Five minus two.",
    "pg005_im003": "Five blue pencils. Number five.",
    "pg051_im008_seg002_v1_crop1": "Seven minus dash equals five.",
    "pg055_im007_crop1": "Two irons plus eight irons equals dash.",
    "pg032_im013_crop_v1_crop1": "Three toy cars plus four toy cars equals seven toy cars.",
    "pg015_im013_seg005_v1_crop_v1": "Eight pineapples. Number eight.",
    "pg056_im006": "Ten minus six equals four. Eight minus three equals five.",
    "pg012_im015_seg002_v1_crop_v1_crop1": "Five backpacks.",
    "pg079_im016_seg003_v1_crop1": "Two groups of ten sticks and eight single sticks.",
    "pg053_im013_seg001_v1_crop_v1_crop1": "Two hands showing five fingers each. Five plus five equals ten.",
    "pg084_im010_seg002_v1_crop_v1": "An abacus showing two tens and three ones. Number twenty-three.",
}


async def main(start: int = 0, limit: int | None = None) -> None:
    root = Path("content/i18n/en-US")
    texts_path = root / "texts.json"
    audios_path = root / "audios.json"
    texts = json.loads(texts_path.read_text(encoding="utf-8"))
    audios = json.loads(audios_path.read_text(encoding="utf-8"))
    output = root / "audio"
    entries = list(REPLACEMENTS.items())
    entries = entries[start:] if limit is None else entries[start:start + limit]
    for text_id, phrase in entries:
        texts[text_id] = phrase
        target = output / f"{text_id}.simple-illustration-20260906.mp3"
        await edge_tts.Communicate(phrase, voice="en-US-AriaNeural").save(str(target))
        audios[text_id] = target.name
        print(f"{text_id}: {phrase}")
    texts_path.write_text(json.dumps(texts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audios_path.write_text(json.dumps(audios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    asyncio.run(main(args.start, args.limit))
