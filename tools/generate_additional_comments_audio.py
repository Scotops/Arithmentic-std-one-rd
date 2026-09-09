"""Generate reviewed narration replacements from the Additional Comments matrix.

The visual book is left intact.  Only the audio mapping is replaced for
illustrations whose original generic alt text omitted the count or sequence.
"""

import asyncio
import json
from pathlib import Path

import edge_tts


PHRASES = {
    # Page 17: the example label was accidentally merged into the word.
    "pg017_n0004": "Two.",
    # Page 27: count the illustrated objects before asking for the answer.
    "pg027_im004": "Nine eggs on a tray.",
    "pg027_im009": "Seven carrots in a box.",
    "pg027_im011": "Three matches in a matchbox.",
    "pg027_im013": "Two snacks on a plate.",
    # Pages 41–46: visual subtraction examples are read from left to right.
    "pg041_im022_seg001_v1_crop_v1_crop1": "Example one. Six kettles take away three kettles. Three kettles remain.",
    "pg041_im022_seg002_v1_crop_v1": "Example two. Seven spoons take away one spoon. Six spoons remain.",
    "pg042_im018_seg001_v1_crop1": "Five bottles take away one bottle. Four bottles remain.",
    "pg042_im018_seg002_v1_crop1": "Seven bells take away three bells. Four bells remain.",
    "pg042_im018_seg003_v1_crop1": "Seven footballs take away five footballs. Two footballs remain.",
    "pg042_im018_seg004_v1_crop1": "Eight chickens take away six chickens. Two chickens remain.",
    "pg045_im011_seg001_v1_crop_v1": "Four pens take away three pens. One pen remains. Four minus three equals dash.",
    "pg046_im008": "Six headphones take away three headphones. Three headphones remain. Four satellite dishes take away two satellite dishes. Two satellite dishes remain.",
    # Page 84, Exercise 6: speak tens and ones and the number represented.
    "pg084_im011_seg001_v1_crop_v1": "Three tens and five ones. Thirty-five.",
    "pg084_im011_seg002_v1_crop_v1": "Four tens and zero ones. Forty.",
    # Page 124 previously pointed at three absent/reused audio files, which
    # stopped narration before the exercise questions could be read.
    "pg124_auto001": "Exercise fourteen.",
    "pg124_auto002": "Write the correct answer in the space provided.",
    "pg124_auto019": "Thirty-five.",
}


async def main() -> None:
    root = Path("content/i18n/en-US")
    audio_dir = root / "audio"

    async def make_clip(text_id: str, phrase: str) -> tuple[str, str]:
        filename = f"{text_id}.additional-comments-20260908.mp3"
        await edge_tts.Communicate(phrase, voice="en-US-AriaNeural").save(str(audio_dir / filename))
        return text_id, filename

    clips = await asyncio.gather(*(make_clip(*item) for item in PHRASES.items()))
    audio_path = root / "audios.json"
    audios = json.loads(audio_path.read_text(encoding="utf-8"))
    audios.update(dict(clips))
    audio_path.write_text(json.dumps(audios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for text_id, filename in clips:
        print(f"{text_id}: {filename}")


if __name__ == "__main__":
    asyncio.run(main())
