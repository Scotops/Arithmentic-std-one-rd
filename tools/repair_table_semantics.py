"""Add non-visual captions and column associations to book tables."""

from __future__ import annotations

import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TABLE = re.compile(r"<table\b[^>]*>.*?</table>", re.IGNORECASE | re.DOTALL)


def clean_text(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def repair_table(block: str, caption: str) -> str:
    # The first post-processor revision accidentally matched ``<thead`` as
    # ``<th``. Repair that historical token before applying the safe rule.
    block = re.sub(r'<th\s+scope="col"ead\b', '<thead', block, flags=re.IGNORECASE)
    opening = re.match(r"<table\b[^>]*>", block, re.IGNORECASE)
    if not opening:
        return block
    insert = ""
    if not re.search(r"<caption\b", block, re.IGNORECASE):
        insert += f'<caption class="sr-only">{html.escape(caption)}</caption>'
    if not re.search(r"<th\b", block, re.IGNORECASE):
        rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", block, re.IGNORECASE | re.DOTALL)
        columns = max((len(re.findall(r"<td\b", row, re.IGNORECASE)) for row in rows), default=1)
        headers = "".join(
            f'<th scope="col">Column {index}</th>' for index in range(1, max(1, columns) + 1)
        )
        insert += f'<thead class="sr-only"><tr>{headers}</tr></thead>'
    block = block[: opening.end()] + insert + block[opening.end() :]
    block = re.sub(r"<th\b(?![^>]*\sscope=)(?![^>]*\sheaders=)", '<th scope="col"', block, flags=re.IGNORECASE)
    return block


def main() -> None:
    changed = 0
    for path in sorted(ROOT.glob("*.html")):
        source = path.read_text(encoding="utf-8")
        heading = re.search(r"<h1\b[^>]*>(.*?)</h1>", source, re.IGNORECASE | re.DOTALL)
        label = clean_text(heading.group(1)) if heading else path.stem.replace("_", " ")
        counter = 0

        def replace(match: re.Match[str]) -> str:
            nonlocal counter
            counter += 1
            return repair_table(match.group(0), f"{label}, table {counter}")

        updated = TABLE.sub(replace, source)
        if updated != source:
            path.write_text(updated, encoding="utf-8", newline="")
            changed += 1
    print(f"Repaired table semantics in {changed} HTML files.")


if __name__ == "__main__":
    main()
