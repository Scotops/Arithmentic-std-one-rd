"""Audit every visible learner blank in the canonical ADT reading spine.

The audit distinguishes blanks owned by an existing narration target from
standalone answer/drawing spaces. Owned blanks must be spoken in their
sentence audio; standalone blanks receive runtime ``adt_blank_*`` targets.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from lxml import html


EXPLICIT_BLANK_CLASSES = {
    "adt-answer-space",
    "adt-static-drawing-space",
    "adt-blank-line",
}
WIDTH_CLASS = re.compile(r"^(?:w-|min-w-|max-w-|h-|min-h-|flex-1$)")
LINE_CLASS = re.compile(r"^border-b(?:-|$)")
TEXT_BLANK = re.compile(r"(?:\[\s*\]|_{1,})")


def classes(element) -> set[str]:
    return set((element.get("class") or "").split())


def is_blank(element) -> bool:
    tokens = classes(element)
    if tokens & EXPLICIT_BLANK_CLASSES:
        return True
    if element.tag not in {"span", "div"}:
        return False
    if "".join(element.itertext()).strip() or element.xpath(".//img|.//svg|.//math"):
        return False
    style = (element.get("style") or "").lower()
    # L-shaped corner decorations and bracket stems are not writing spaces.
    if "pointer-events-none" in tokens or any(
        token.startswith(("border-l", "border-r")) for token in tokens
    ):
        return False
    has_line = any(LINE_CLASS.match(token) for token in tokens) or "border-bottom" in style
    looks_like_space = (
        any(WIDTH_CLASS.match(token) for token in tokens)
        or "inline-block" in tokens
        or "border-dotted" in tokens
        or "width:" in style
    )
    return has_line and looks_like_space


def closest_owner(element):
    parent = element.getparent()
    while parent is not None:
        if parent.get("data-id"):
            return parent
        parent = parent.getparent()
    return None


def text_blank_count(value: str) -> int:
    fragment = html.fragment_fromstring(f"<div>{value}</div>", create_parent=False)
    count = sum(1 for element in fragment.iterdescendants() if is_blank(element))
    plain = " ".join(fragment.itertext())
    return count + len(TEXT_BLANK.findall(plain))


def audit(root: Path) -> dict:
    pages = json.loads((root / "content/pages.json").read_text(encoding="utf-8"))
    texts = json.loads((root / "content/i18n/en-US/texts.json").read_text(encoding="utf-8"))
    audios = json.loads((root / "content/i18n/en-US/audios.json").read_text(encoding="utf-8"))
    occurrences = []
    owners: dict[str, list[dict]] = defaultdict(list)
    page_counts: Counter[str] = Counter()

    for page in pages:
        href = page["href"].split("#", 1)[0]
        document = html.fromstring((root / href).read_text(encoding="utf-8"))
        page_sequence = 0
        for element in document.xpath("//*[@id='content']//*[self::span or self::div]"):
            if not is_blank(element):
                continue
            page_sequence += 1
            owner = closest_owner(element)
            item = {
                "page": href,
                "sequence": page_sequence,
                "tag": element.tag,
                "classes": sorted(classes(element)),
                "owner_id": owner.get("data-id") if owner is not None else None,
            }
            occurrences.append(item)
            page_counts[href] += 1
            if item["owner_id"]:
                owners[item["owner_id"]].append(item)

    owner_rows = []
    for owner_id, items in sorted(owners.items()):
        mapping = str(audios.get(owner_id, ""))
        mapped_count = text_blank_count(str(texts.get(owner_id, "")))
        required_count = len(items)
        # The historical generator appended one spoken dash when a single
        # drawn underline existed only in HTML, so text_dashes may be zero
        # for a correctly generated one-blank clip.
        guaranteed = ".blank-dash-" in mapping and (
            mapped_count == required_count or (mapped_count == 0 and required_count == 1)
        )
        owner_rows.append({
            "id": owner_id,
            "page": items[0]["page"],
            "required_dashes": required_count,
            "text_dashes": mapped_count,
            "audio": mapping,
            "guaranteed": guaranteed,
        })

    standalone = [item for item in occurrences if not item["owner_id"]]
    return {
        "canonical_pages": len(pages),
        "blank_occurrences": len(occurrences),
        "owned_blank_occurrences": len(occurrences) - len(standalone),
        "standalone_blank_occurrences": len(standalone),
        "owner_targets": len(owner_rows),
        "owner_target_details": owner_rows,
        "guaranteed_owner_targets": sum(row["guaranteed"] for row in owner_rows),
        "owner_targets_needing_audio": [row for row in owner_rows if not row["guaranteed"]],
        "standalone": standalone,
        "pages_with_blanks": dict(sorted(page_counts.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("book", nargs="?", default=".")
    parser.add_argument("--output")
    parser.add_argument("--fail-on-uncovered", action="store_true")
    args = parser.parse_args()
    report = audit(Path(args.book).resolve())
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(json.dumps({
        key: value for key, value in report.items()
        if key not in {"owner_target_details", "owner_targets_needing_audio", "standalone", "pages_with_blanks"}
    }, indent=2))
    print(f"Owner targets needing dash audio: {len(report['owner_targets_needing_audio'])}")
    if args.fail_on_uncovered and report["owner_targets_needing_audio"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
