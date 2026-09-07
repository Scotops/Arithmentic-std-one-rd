"""Find visible book text that cannot enter the ID-based narration queue."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool, bool]] = []
        self.untagged: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        classes = set(values.get("class", "").split())
        parent_tagged = self.stack[-1][1] if self.stack else False
        parent_skip = self.stack[-1][2] if self.stack else False
        tagged = parent_tagged or "data-id" in values
        skip = parent_skip or tag in {"head", "title", "script", "style", "template", "noscript", "button"}
        skip = skip or "hidden" in values or values.get("aria-hidden") == "true"
        skip = skip or "sr-only" in classes or "printed-folio" in classes or "ai-narration-disclosure" in classes
        self.stack.append((tag, tagged, skip))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if not value or not self.stack:
            return
        _tag, tagged, skip = self.stack[-1]
        if not tagged and not skip and re.search(r"[A-Za-z0-9+−–=_]", value):
            self.untagged.append(value)


def main() -> None:
    pages = json.loads((ROOT / "content" / "pages.json").read_text(encoding="utf-8"))
    findings = {}
    for entry in pages:
        path = ROOT / entry["href"].split("#", 1)[0]
        parser = VisibleTextParser()
        parser.feed(path.read_text(encoding="utf-8"))
        # Standalone red question numbers are registered by accessible-reading-order.js.
        remaining = [value for value in parser.untagged if not re.fullmatch(r"\d{1,3}\.", value)]
        if remaining:
            findings[path.name] = remaining
    print(json.dumps(findings, ensure_ascii=False, indent=2))
    print(f"Pages with untagged visible narration: {len(findings)}")


if __name__ == "__main__":
    main()
