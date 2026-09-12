"""Insert cover slots without changing which video belongs to each book page."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
META = re.compile(
    r'(<meta\s+name=["\']page-section-id["\']\s+content=["\'])(\d+)(["\']\s*/?>)',
    re.IGNORECASE,
)


def main() -> None:
    pages_path = ROOT / "content" / "pages.json"
    pages = json.loads(pages_path.read_text(encoding="utf-8"))
    if len(pages) != 134:
        raise SystemExit(f"Expected the new 134-entry spine, found {len(pages)}")
    if pages[0]["section_id"] != "cover_front_sec001" or pages[-1]["section_id"] != "cover_back_sec001":
        raise SystemExit("Front and back cover entries are not at the spine boundaries")

    interior = pages[1:-1]
    if len(interior) != 132:
        raise SystemExit(f"Expected 132 original interior pages, found {len(interior)}")
    for physical_index, entry in enumerate(interior, start=2):
        html_path = ROOT / entry["href"].split("#", 1)[0]
        source = html_path.read_text(encoding="utf-8")
        match = META.search(source)
        if not match:
            raise SystemExit(f"Missing page-section-id in {html_path.name}")
        current = int(match.group(2))
        if current not in {physical_index - 1, physical_index}:
            raise SystemExit(
                f"Unexpected page-section-id in {html_path.name}: {current}; "
                f"expected {physical_index - 1} or {physical_index}"
            )
        updated = META.sub(rf"\g<1>{physical_index}\g<3>", source, count=1)
        if updated != source:
            html_path.write_text(updated, encoding="utf-8", newline="")

    videos_path = ROOT / "content" / "i18n" / "en-US" / "videos.json"
    videos = json.loads(videos_path.read_text(encoding="utf-8"))
    legacy = {f"video-{index}": f"page_{index}.mp4" for index in range(1, 133)}
    shifted = {f"video-{index + 1}": f"page_{index}.mp4" for index in range(1, 133)}
    if videos == legacy:
        videos_path.write_text(
            json.dumps(shifted, indent=2) + "\n", encoding="utf-8", newline=""
        )
    elif videos != shifted:
        raise SystemExit("Video mappings were not in the expected original or shifted state")

    print("Inserted two cover slots; preserved all 132 page-to-video assignments.")


if __name__ == "__main__":
    main()
