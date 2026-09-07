"""Rebuild the ADT's inline JSON cache from the current source manifests.

The reader loads this cache before its normal runtime.  Keeping it generated from
the canonical JSON files prevents stale text and audio mappings from overriding
later accessibility corrections.
"""

from __future__ import annotations

import json
import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "offline-preloader-fixed.js"
SOURCES = (
    ("./assets/config.json", ROOT / "assets" / "config.json"),
    ("./content/pages.json", ROOT / "content" / "pages.json"),
    ("./content/toc.json", ROOT / "content" / "toc.json"),
    (
        "./content/i18n/en-US/texts.json",
        ROOT / "content" / "i18n" / "en-US" / "texts.json",
    ),
    (
        "./content/i18n/en-US/audios.json",
        ROOT / "content" / "i18n" / "en-US" / "audios.json",
    ),
    (
        "./content/i18n/en-US/videos.json",
        ROOT / "content" / "i18n" / "en-US" / "videos.json",
    ),
    (
        "./content/i18n/en-US/glossary.json",
        ROOT / "content" / "i18n" / "en-US" / "glossary.json",
    ),
    (
        "./content/i18n/en-US/timecode/timecode_output.json",
        ROOT
        / "content"
        / "i18n"
        / "en-US"
        / "timecode"
        / "timecode_output.json",
    ),
)


def read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def build_preloader() -> str:
    inline = {url: read_json(path) for url, path in SOURCES}
    payload = json.dumps(inline, ensure_ascii=True, separators=(",", ":"))
    return f'''// Offline reader data generated from the current ADT content.
(function () {{
  var INLINE = {payload};
  var BASE_DIR = (function () {{ var href = location.href.split("?")[0].split("#")[0]; return href.slice(0, href.lastIndexOf("/") + 1); }})();
  function lookup(url) {{ var clean = String(url).split("?")[0].split("#")[0]; if (BASE_DIR && clean.indexOf(BASE_DIR) === 0) clean = clean.slice(BASE_DIR.length); if (clean.indexOf("./") === 0) clean = clean.slice(2); var withDot = "./" + clean; return INLINE[withDot] || INLINE[clean] || null; }}
  var originalFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {{ var url = typeof input === "string" ? input : input && input.url; var value = lookup(url); if (value !== null) return Promise.resolve(new Response(JSON.stringify(value), {{status:200, headers:{{"Content-Type":"application/json"}}}})); return originalFetch(input, init); }};
}})();
'''


def update_html(version: str) -> int:
    patterns = (
        re.compile(r"offline-preloader-fixed\.js\?v=[^\"']+"),
        re.compile(r"image-caption-narration\.js\?v=[^\"']+"),
    )
    changed = 0
    texts = read_json(ROOT / "content" / "i18n" / "en-US" / "texts.json")
    image_tag = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
    data_id = re.compile(r"\bdata-id=([\"'])(.*?)\1", re.IGNORECASE)
    alt = re.compile(r"\balt=([\"'])(.*?)\1", re.IGNORECASE)

    def sync_alt(match: re.Match[str]) -> str:
        tag = match.group(0)
        identifier = data_id.search(tag)
        if not identifier or identifier.group(2) not in texts:
            return tag
        value = html.escape(str(texts[identifier.group(2)]), quote=True)
        if alt.search(tag):
            return alt.sub(f'alt="{value}"', tag, count=1)
        return tag[:-1] + f' alt="{value}">'

    for path in sorted(ROOT.glob("*.html")):
        original = path.read_text(encoding="utf-8")
        updated = re.sub(
            r"\s*<script\b[^>]*src=[\"'][^\"']*(?:pdf-facsimile|static-textbook)\.js[^\"']*[\"'][^>]*>\s*</script>",
            "",
            original,
            flags=re.IGNORECASE,
        )
        for pattern in patterns:
            asset = pattern.pattern.split(r"\.", 1)[0]
            updated = pattern.sub(f"{asset}.js?v={version}", updated)
        updated = re.sub(r"reference-layout\.css\?v=[^\"']+", f"reference-layout.css?v={version}", updated)
        updated = re.sub(r"tts-pipeline\.js\?v=[^\"']+", f"tts-pipeline.js?v={version}", updated)
        updated = re.sub(r"media-sync\.js\?v=[^\"']+", f"media-sync.js?v={version}", updated)
        updated = re.sub(r"accessible-reading-order\.js\?v=[^\"']+", f"accessible-reading-order.js?v={version}", updated)
        updated = image_tag.sub(sync_alt, updated)
        if updated != original:
            path.write_text(updated, encoding="utf-8", newline="")
            changed += 1
    return changed


def main() -> None:
    config = read_json(ROOT / "assets" / "config.json")
    version = str(config["bundleVersion"])
    OUTPUT.write_text(build_preloader(), encoding="utf-8", newline="")
    changed = update_html(version)
    print(f"Rebuilt {OUTPUT.relative_to(ROOT)} for bundle version {version}.")
    print(f"Updated cache keys in {changed} HTML files.")


if __name__ == "__main__":
    main()
