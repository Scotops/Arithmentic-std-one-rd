"""Audit page narration coverage and the generated offline cache."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCALE_ROOT = ROOT / "content" / "i18n" / "en-US"
AUDIO_DIR = LOCALE_ROOT / "audio"
RUNTIME_IDS = ("pg014_n0013", "pg043_im002b_crop1", "pg080_im015")


class IdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.images: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        text_id = values.get("data-id")
        if text_id:
            self.ids.append(text_id)
            if tag == "img":
                self.images.append(text_id)


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_inline_cache() -> dict[str, object]:
    source = (ROOT / "assets" / "offline-preloader-fixed.js").read_text(
        encoding="utf-8"
    )
    match = re.search(r"var INLINE = (\{.*\});\n  var BASE_DIR", source, re.DOTALL)
    if not match:
        raise RuntimeError("Could not parse assets/offline-preloader-fixed.js")
    return json.loads(match.group(1))


def main() -> None:
    pages = load(ROOT / "content" / "pages.json")
    texts = load(LOCALE_ROOT / "texts.json")
    audio_map = load(LOCALE_ROOT / "audios.json")
    inline = parse_inline_cache()
    issues: dict[str, list[dict[str, str]]] = defaultdict(list)
    totals = {"pages": len(pages), "targets": 0, "images": 0}

    for text_id in RUNTIME_IDS:
        text = str(texts.get(text_id, "")).strip()
        filename = audio_map.get(text_id)
        if not text:
            issues["missing_runtime_text"].append({"id": text_id})
        if not filename:
            issues["missing_runtime_audio_mapping"].append({"id": text_id})
        else:
            audio_path = AUDIO_DIR / filename.split("?", 1)[0]
            if not audio_path.is_file() or audio_path.stat().st_size < 500:
                issues["invalid_runtime_audio_file"].append(
                    {"id": text_id, "audio": filename}
                )

    for entry in pages:
        href = entry["href"].split("?", 1)[0]
        path = ROOT / href
        parser = IdCollector()
        parser.feed(path.read_text(encoding="utf-8"))
        for text_id in parser.ids:
            totals["targets"] += 1
            text = str(texts.get(text_id, "")).strip()
            if not text:
                issues["missing_text"].append({"page": href, "id": text_id})
            filename = audio_map.get(text_id)
            if not filename:
                issues["missing_audio_mapping"].append(
                    {"page": href, "id": text_id}
                )
            else:
                audio_path = AUDIO_DIR / filename.split("?", 1)[0]
            if filename and not audio_path.is_file():
                issues["missing_audio_file"].append(
                    {"page": href, "id": text_id, "audio": filename}
                )
            elif filename and audio_path.stat().st_size < 500:
                issues["invalid_audio_file"].append(
                    {"page": href, "id": text_id, "audio": filename}
                )
        for image_id in parser.images:
            totals["images"] += 1
            description = str(texts.get(image_id, "")).strip()
            if not description or description.casefold() in {
                "image",
                "illustration",
                "picture",
            }:
                issues["invalid_image_description"].append(
                    {"page": href, "id": image_id, "description": description}
                )

    cache_sources = {
        "./assets/config.json": ROOT / "assets" / "config.json",
        "./content/pages.json": ROOT / "content" / "pages.json",
        "./content/toc.json": ROOT / "content" / "toc.json",
        "./content/i18n/en-US/texts.json": LOCALE_ROOT / "texts.json",
        "./content/i18n/en-US/audios.json": LOCALE_ROOT / "audios.json",
        "./content/i18n/en-US/videos.json": LOCALE_ROOT / "videos.json",
        "./content/i18n/en-US/glossary.json": LOCALE_ROOT / "glossary.json",
        "./content/i18n/en-US/timecode/timecode_output.json": LOCALE_ROOT
        / "timecode"
        / "timecode_output.json",
    }
    for url, path in cache_sources.items():
        if inline.get(url) != load(path):
            issues["stale_offline_cache"].append({"source": str(path), "url": url})

    summary = {name: len(items) for name, items in sorted(issues.items())}
    report = {"totals": totals, "issues": issues, "summary": summary}
    report_path = ROOT / "tmp" / "readaloud-audit.json"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({**totals, **summary}, indent=2))
    if any(summary.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
