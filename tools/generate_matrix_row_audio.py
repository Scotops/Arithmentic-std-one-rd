"""Generate reviewed row narration for visual object-counting matrices."""

import asyncio
import json
from pathlib import Path

import edge_tts


PHRASES = {
    "pg014_matrix_row_1": "Seven oranges. Number one.",
    "pg014_matrix_row_2": "Four oranges. Number eight.",
    "pg014_matrix_row_3": "Two oranges. Number two.",
    "pg014_matrix_row_4": "Six oranges. Number seven.",
    "pg014_matrix_row_5": "Five oranges. Number four.",
    "pg014_matrix_row_6": "Three oranges. Number six.",
    "pg014_matrix_row_7": "Nine oranges. Number nine.",
    "pg014_matrix_row_8": "Eight oranges. Number five.",
}


async def main() -> None:
    root = Path("content/i18n/en-US")
    audio_dir = root / "audio"

    async def make_clip(text_id: str, phrase: str) -> tuple[str, str]:
        name = f"{text_id}.matrix-row-20260908.mp3"
        await edge_tts.Communicate(phrase, voice="en-US-AriaNeural").save(str(audio_dir / name))
        return text_id, name

    clips = await asyncio.gather(*(make_clip(*item) for item in PHRASES.items()))
    path = root / "audios.json"
    mappings = json.loads(path.read_text(encoding="utf-8"))
    mappings.update(dict(clips))
    path.write_text(json.dumps(mappings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # The targets are injected at runtime to preserve the printed matrix, so
    # include their text in the normal localization map for queue validation.
    texts_path = root / "texts.json"
    texts = json.loads(texts_path.read_text(encoding="utf-8"))
    texts.update(PHRASES)
    texts_path.write_text(json.dumps(texts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for text_id, name in clips:
        print(f"{text_id}: {name}")


if __name__ == "__main__":
    asyncio.run(main())
