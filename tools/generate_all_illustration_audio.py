"""Generate one concise read-aloud clip for every active book illustration."""

import argparse
import asyncio
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import edge_tts


class ImageIdParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "img":
            return
        values = dict(attrs)
        image_id = values.get("data-id")
        if image_id and values.get("aria-hidden") != "true":
            self.ids.append(image_id)


def active_image_ids() -> list[str]:
    found: list[str] = []
    for page in sorted(Path(".").glob("*.html")):
        parser = ImageIdParser()
        parser.feed(page.read_text(encoding="utf-8"))
        found.extend(parser.ids)
    return list(dict.fromkeys(found))


def concise(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", text).strip()
    # A single complete sentence is enough for a young listener and avoids
    # repeating decorative details that do not help solve the exercise.
    sentence = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
    return sentence or "Illustration."


async def main(start: int = 0, limit: int | None = None) -> None:
    root = Path("content/i18n/en-US")
    texts = json.loads((root / "texts.json").read_text(encoding="utf-8"))
    audios_path = root / "audios.json"
    audios = json.loads(audios_path.read_text(encoding="utf-8"))
    ids = [image_id for image_id in active_image_ids() if isinstance(texts.get(image_id), str) and texts[image_id].strip()]
    selected = ids[start:start + limit] if limit else ids[start:]
    output = root / "audio"

    async def generate(image_id: str) -> None:
        target = output / f"{image_id}.concise-illustration-20260905.mp3"
        if not target.exists() or target.stat().st_size <= 500:
            phrase = concise(texts[image_id])
            await edge_tts.Communicate(phrase, voice="en-US-AriaNeural").save(str(target))
            print(image_id, phrase)
        audios[image_id] = target.name

    # Generate a small batch concurrently. This keeps the first page ready
    # quickly without queuing hundreds of browser/audio requests at once.
    for offset in range(0, len(selected), 8):
        await asyncio.gather(*(generate(image_id) for image_id in selected[offset:offset + 8]))
    audios_path.write_text(json.dumps(audios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    asyncio.run(main(args.start, args.limit))
