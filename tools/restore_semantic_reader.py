"""Restore the semantic ADT pages and the source book's printed folios.

The repair is intentionally deterministic so future content rebuilds cannot
silently re-enable the old screenshot overlay or disable exercises again.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGES_PATH = ROOT / "content" / "pages.json"
TOC_PATH = ROOT / "content" / "toc.json"


def printed_folio(physical_page: int) -> str:
    if physical_page == 1:
        return "Cover"
    if 2 <= physical_page <= 6:
        return ("ii", "iii", "iv", "v", "vi")[physical_page - 2]
    return str(physical_page - 6)


def primary_href(physical_page: int) -> str:
    return "index.html" if physical_page == 1 else f"pg{physical_page:03d}_sec001.html"


def remove_obsolete_scripts(source: str) -> str:
    patterns = (
        r"\s*<script\b[^>]*src=[\"'][^\"']*pdf-facsimile\.js[^\"']*[\"'][^>]*>\s*</script>",
        r"\s*<script\b[^>]*src=[\"'][^\"']*static-textbook\.js[^\"']*[\"'][^>]*>\s*</script>",
    )
    for pattern in patterns:
        source = re.sub(pattern, "", source, flags=re.IGNORECASE)
    source = re.sub(
        r'(<script\b[^>]*src=["\'])[^"\']*offline-preloader-audio-dash-only\.js[^"\']*(["\'][^>]*>\s*</script>)',
        r'\1./assets/offline-preloader-fixed.js?v=15\2',
        source,
        flags=re.IGNORECASE,
    )
    return source


def add_media_sync(source: str) -> str:
    if re.search(r'src=["\'][^"\']*media-sync\.js', source, re.IGNORECASE):
        return source
    script = '\n    <script src="./assets/media-sync.js?v=16"></script>\n'
    return re.sub(r'(?i)</body>', script + '</body>', source, count=1)


def clean_image_semantics(source: str) -> str:
    hidden_fallback_ids = {
        "pg035_im007", "pg055_im009_crop_v1", "pg057_im007",
        "pg067_im020_seg001_v1_crop_v1", "pg080_im014",
        "pg096_im007_crop_v1",
    }
    image_pattern = re.compile(r"<img\b[^>]*>", flags=re.IGNORECASE)

    def clean(match: re.Match[str]) -> str:
        tag = match.group(0).replace("object-fill", "object-contain")
        identifier = re.search(r"\sdata-id=([\"'])([^\"']+)\1", tag, re.IGNORECASE)
        if identifier and identifier.group(2) in hidden_fallback_ids:
            tag = re.sub(r"\sdata-id=([\"'])[^\"']+\1", "", tag, flags=re.IGNORECASE)
            tag = re.sub(r"\salt=([\"'])[^\"']*\1", ' alt=""', tag, flags=re.IGNORECASE)
            if not re.search(r"\saria-hidden=", tag, re.IGNORECASE):
                tag = tag[:-1] + ' aria-hidden="true" role="presentation">'
        alt = re.search(r"\salt=([\"'])([^\"']*)\1", tag, re.IGNORECASE)
        if alt and not alt.group(2).strip() and not re.search(r"\saria-hidden=", tag, re.IGNORECASE):
            tag = tag[:-1] + ' aria-hidden="true" role="presentation">'
        return tag

    return image_pattern.sub(clean, source)


def add_section_ids(source: str) -> str:
    pattern = re.compile(r"<section\b[^>]*>", flags=re.IGNORECASE)

    def replace(match: re.Match[str]) -> str:
        tag = match.group(0)
        if re.search(r"\s+id\s*=", tag, flags=re.IGNORECASE):
            return tag
        section_id = re.search(
            r"\sdata-section-id=([\"'])([^\"']+)\1", tag, flags=re.IGNORECASE
        )
        if not section_id:
            return tag
        return tag.replace("<section", f'<section id="{section_id.group(2)}"', 1)

    return pattern.sub(replace, source)


def add_activity_roles(source: str) -> str:
    pattern = re.compile(r"<section\b[^>]*>", flags=re.IGNORECASE)

    def replace(match: re.Match[str]) -> str:
        tag = match.group(0)
        if not re.search(r'data-section-type=["\']activity_', tag, re.IGNORECASE):
            return tag
        if re.search(r'\srole=', tag, re.IGNORECASE):
            return tag
        return tag.replace("<section", '<section role="activity"', 1)

    return pattern.sub(replace, source)


def remove_disclosure(source: str) -> str:
    return re.sub(
        r"\s*<p\b[^>]*class=[\"'][^\"']*ai-narration-disclosure[^\"']*[\"'][^>]*>.*?</p>",
        "",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )


def add_disclosure(source: str) -> str:
    source = remove_disclosure(source)
    disclosure = (
        '\n      <p class="ai-narration-disclosure" role="note">'
        'Read-aloud narration uses an AI-generated voice.</p>\n'
    )
    return re.sub(r"(?i)</main>", disclosure + "    </main>", source, count=1)


def add_folio(source: str, physical_page: int) -> str:
    source = re.sub(
        r"\s*<footer\b[^>]*class=[\"'][^\"']*printed-folio[^\"']*[\"'][^>]*>.*?</footer>",
        "",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    folio = printed_folio(physical_page)
    if physical_page == 1:
        footer = (
            '\n      <footer class="printed-folio printed-folio-cover">'
            '<span class="sr-only">Cover</span></footer>\n'
        )
    else:
        variant = " printed-folio-body" if physical_page >= 7 else ""
        footer = (
            f'\n      <footer class="printed-folio{variant}" aria-label="Printed page {folio}">'
            f'{folio}</footer>\n'
        )
    container_close = re.compile(r"(?P<close>\s*</div>\s*)(?P<main></main>)", re.IGNORECASE)
    if not container_close.search(source):
        raise ValueError(f"Could not find the content container before </main> on page {physical_page}")
    return container_close.sub(footer + r"\g<close>\g<main>", source, count=1)


def update_primary_metadata(source: str, physical_page: int) -> str:
    source = re.sub(
        r'(<meta\s+name=["\']page-section-id["\']\s+content=["\'])[^"\']*(["\'])',
        rf"\g<1>{physical_page}\2",
        source,
        count=1,
        flags=re.IGNORECASE,
    )
    return source


def main() -> None:
    pages = json.loads(PAGES_PATH.read_text(encoding="utf-8"))
    if len(pages) != 132:
        raise SystemExit(f"Expected 132 physical pages, found {len(pages)}")

    primary_by_page: dict[int, Path] = {}
    for physical_page, entry in enumerate(pages, 1):
        entry["section_id"] = f"pg{physical_page:03d}_sec001"
        entry["href"] = primary_href(physical_page)
        entry["page_number"] = printed_folio(physical_page)
        primary_by_page[physical_page] = ROOT / primary_href(physical_page)

    PAGES_PATH.write_text(
        json.dumps(pages, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="",
    )

    changed = 0
    for path in sorted(ROOT.glob("*.html")):
        original = path.read_text(encoding="utf-8")
        updated = add_media_sync(remove_disclosure(clean_image_semantics(add_activity_roles(add_section_ids(remove_obsolete_scripts(original))))))
        physical_match = re.match(r"pg(\d{3})_sec001\.html$", path.name)
        physical_page = 1 if path.name == "index.html" else (
            int(physical_match.group(1)) if physical_match else None
        )
        if physical_page in primary_by_page:
            updated = update_primary_metadata(updated, physical_page)
            updated = add_folio(updated, physical_page)
        updated = add_disclosure(updated)
        if updated != original:
            path.write_text(updated, encoding="utf-8", newline="")
            changed += 1

    toc = json.loads(TOC_PATH.read_text(encoding="utf-8"))
    for entry in toc:
        match = re.match(r"pg(\d{3})_sec(\d{3})$", str(entry.get("section_id", "")))
        if not match:
            continue
        physical_page = int(match.group(1))
        section_number = int(match.group(2))
        href = primary_href(physical_page)
        if section_number > 1:
            href += f'#{entry["section_id"]}'
        entry["href"] = href
    TOC_PATH.write_text(
        json.dumps(toc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="",
    )
    print(f"Restored semantic reader structure in {changed} HTML files.")
    print("Mapped 132 physical pages to Cover, ii-vi, and 1-126.")


if __name__ == "__main__":
    main()
