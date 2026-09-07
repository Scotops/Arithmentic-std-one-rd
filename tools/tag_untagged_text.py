"""Wrap every remaining visible book-text node in a stable narration ID."""

from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCALE = ROOT / "content" / "i18n" / "en-US"
TOKEN = re.compile(r"<!--.*?-->|<![^>]*>|</?[^>]+>|[^<]+", re.DOTALL)
TAG = re.compile(r"<\s*(/?)\s*([a-zA-Z0-9:-]+)([^>]*)>", re.DOTALL)
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def normalized(value: str) -> str:
    return " ".join(html.unescape(value).split())


def main() -> None:
    pages = json.loads((ROOT / "content" / "pages.json").read_text(encoding="utf-8"))
    texts = json.loads((LOCALE / "texts.json").read_text(encoding="utf-8-sig"))
    audios = json.loads((LOCALE / "audios.json").read_text(encoding="utf-8-sig"))
    reusable: dict[str, list[str]] = defaultdict(list)
    for identifier, value in texts.items():
        if identifier in audios and normalized(str(value)):
            reusable[normalized(str(value))].append(str(audios[identifier]))

    added = 0
    changed_pages = 0
    for entry in pages:
        path = ROOT / entry["href"].split("#", 1)[0]
        original = path.read_text(encoding="utf-8")
        source = original
        removed_comment_ids: list[str] = []

        def unwrap_comment(match: re.Match[str]) -> str:
            removed_comment_ids.append(match.group(1))
            return match.group(2)

        source = re.sub(
            r'<span\s+data-id="([^"]+_auto\d{3})">\s*(<!--.*?-->)\s*</span>',
            unwrap_comment,
            source,
            flags=re.DOTALL,
        )
        for identifier in removed_comment_ids:
            texts.pop(identifier, None)
            audios.pop(identifier, None)
            for audio_file in (LOCALE / "audio").glob(f"{identifier}.*"):
                audio_file.unlink()
        main_match = re.search(r"<main\b[^>]*>.*?</main>", source, re.I | re.S)
        if not main_match:
            continue
        page_id = "pg001" if path.name == "index.html" else path.name[:5]
        existing = [int(number) for number in re.findall(rf'{page_id}_auto(\d{{3}})', source)]
        counter = max(existing, default=0)
        stack: list[tuple[str, bool, bool]] = []
        output: list[str] = []

        for token in TOKEN.findall(main_match.group(0)):
            if token.startswith("<!--") or token.startswith("<!"):
                output.append(token)
                continue
            tag_match = TAG.fullmatch(token)
            if tag_match:
                closing, tag, attrs = tag_match.groups()
                tag = tag.lower()
                if closing:
                    for index in range(len(stack) - 1, -1, -1):
                        if stack[index][0] == tag:
                            del stack[index:]
                            break
                else:
                    parent_tagged = stack[-1][1] if stack else False
                    parent_skip = stack[-1][2] if stack else False
                    tagged = parent_tagged or bool(re.search(r'\bdata-id\s*=', attrs, re.I))
                    classes = re.search(r'\bclass\s*=\s*(["\'])(.*?)\1', attrs, re.I | re.S)
                    class_names = set(classes.group(2).split()) if classes else set()
                    skip = parent_skip or tag in {"script", "style", "template", "noscript", "button"}
                    skip = skip or bool(re.search(r'(?:^|\s)hidden(?:\s|=|$)|\baria-hidden\s*=\s*["\']true', attrs, re.I))
                    skip = skip or bool(class_names & {"sr-only", "printed-folio", "ai-narration-disclosure"})
                    if tag not in VOID and not token.rstrip().endswith("/>"):
                        stack.append((tag, tagged, skip))
                output.append(token)
                continue

            value = normalized(token)
            tagged = stack[-1][1] if stack else False
            skip = stack[-1][2] if stack else False
            if not value or tagged or skip or not re.search(r"[A-Za-z0-9+−–=_]", value):
                output.append(token)
                continue
            counter += 1
            identifier = f"{page_id}_auto{counter:03d}"
            leading = token[: len(token) - len(token.lstrip())]
            trailing = token[len(token.rstrip()) :]
            inner = token[len(leading) : len(token) - len(trailing) if trailing else None]
            output.append(f'{leading}<span data-id="{identifier}">{inner}</span>{trailing}')
            texts[identifier] = value
            choices = reusable.get(value, [])
            audios[identifier] = choices[0] if choices else f"{identifier}.pending.mp3"
            added += 1

        updated_main = "".join(output)
        updated = source[: main_match.start()] + updated_main + source[main_match.end() :]
        if updated != original:
            path.write_text(updated, encoding="utf-8", newline="")
            changed_pages += 1

    (LOCALE / "texts.json").write_text(json.dumps(texts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="")
    (LOCALE / "audios.json").write_text(json.dumps(audios, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="")
    print(f"Tagged {added} visible text nodes across {changed_pages} pages.")


if __name__ == "__main__":
    main()
