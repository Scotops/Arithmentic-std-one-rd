#!/usr/bin/env python3
"""Convert generated ADT answer widgets into source-faithful static exercises.

The printed questions, options, blank spaces, source answers, images, and narration
IDs remain.  Form controls, answer metadata, generated feedback, and drawing
scripts are removed so the runtime cannot inject Submit/Check/Reset controls.
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
from pathlib import Path


TAG_FLAGS = re.IGNORECASE | re.DOTALL
INTERACTIVE_CLASS_PREFIXES = (
    "active:",
    "disabled:",
    "focus:",
    "focus-visible:",
    "group-hover:",
    "has-[",
    "hover:",
    "peer-checked:",
)
INTERACTIVE_CLASSES = {
    "cursor-pointer",
    "duration-200",
    "duration-300",
    "transition",
    "transition-all",
    "transition-colors",
    "transition-transform",
}


def get_attr(attrs: str, name: str) -> str:
    match = re.search(
        rf"\b{re.escape(name)}\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))",
        attrs,
        TAG_FLAGS,
    )
    if not match:
        return ""
    return next((group for group in match.groups() if group is not None), "")


def remove_attr(attrs: str, name: str) -> str:
    return re.sub(
        rf"\s+{re.escape(name)}(?![\w:-])(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+))?",
        "",
        attrs,
        flags=TAG_FLAGS,
    )


def strip_interactive_attrs(attrs: str) -> str:
    for name in (
        "aria-checked",
        "aria-disabled",
        "aria-selected",
        "data-activity-item",
        "data-answer",
        "data-aria-id",
        "data-correct",
        "data-explanation",
        "data-explanation-id",
        "data-submit-target",
        "disabled",
        "for",
        "tabindex",
    ):
        attrs = remove_attr(attrs, name)
    return attrs


def static_classes(value: str, extra: str) -> str:
    tokens = []
    for token in value.split():
        if token in INTERACTIVE_CLASSES:
            continue
        if token.startswith(INTERACTIVE_CLASS_PREFIXES):
            continue
        if token in {"selected-option", "pointer-events-none"}:
            continue
        tokens.append(token)
    if extra not in tokens:
        tokens.append(extra)
    return " ".join(tokens)


def class_attr(attrs: str, extra: str) -> str:
    old = get_attr(attrs, "class")
    attrs = remove_attr(attrs, "class")
    value = static_classes(old, extra)
    return f'{attrs} class="{html.escape(value, quote=True)}"'


def convert_section(match: re.Match[str]) -> str:
    attrs = match.group("attrs")
    if not re.search(r"\brole\s*=\s*['\"]activity['\"]", attrs, TAG_FLAGS):
        return match.group(0)
    attrs = re.sub(
        r"\brole\s*=\s*(['\"])activity\1",
        'role="article"',
        attrs,
        flags=TAG_FLAGS,
    )
    attrs = re.sub(
        r"\bdata-section-type\s*=\s*(['\"])activity_[^'\"]+\1",
        'data-section-type="static_exercise"',
        attrs,
        flags=TAG_FLAGS,
    )
    for name in ("data-correct-answers", "data-option-explanations"):
        attrs = remove_attr(attrs, name)
    if re.search(r"\bdata-id\s*=\s*['\"]qz\d{3}['\"]", attrs, TAG_FLAGS):
        attrs = remove_attr(attrs, "data-id")
        attrs = remove_attr(attrs, "data-area-id")
    return f"<section{attrs}>"


def convert_input(match: re.Match[str]) -> str:
    attrs = match.group("attrs")
    input_type = get_attr(attrs, "type").lower() or "text"
    if input_type in {"button", "checkbox", "hidden", "radio", "reset", "submit"}:
        return ""

    value = html.unescape(get_attr(attrs, "value"))
    classes = get_attr(attrs, "class")
    style = get_attr(attrs, "style")
    extra = "adt-static-answer-value" if value else "adt-answer-space"
    class_value = static_classes(classes, extra)
    style_attr = f' style="{html.escape(style, quote=True)}"' if style else ""
    text = html.escape(value) if value else ""
    return (
        f'<span class="{html.escape(class_value, quote=True)}"'
        f'{style_attr} aria-hidden="true">{text}</span>'
    )


def convert_textarea(match: re.Match[str]) -> str:
    attrs = match.group("attrs")
    classes = static_classes(get_attr(attrs, "class"), "adt-answer-space--multiline")
    style = get_attr(attrs, "style")
    style_attr = f' style="{html.escape(style, quote=True)}"' if style else ""
    return (
        f'<span class="{html.escape(classes, quote=True)}"'
        f'{style_attr} aria-hidden="true"></span>'
    )


def convert_canvas(match: re.Match[str]) -> str:
    attrs = match.group("attrs")
    classes = static_classes(get_attr(attrs, "class"), "adt-static-drawing-space")
    style = get_attr(attrs, "style")
    style_attr = f' style="{html.escape(style, quote=True)}"' if style else ""
    return (
        f'<div class="{html.escape(classes, quote=True)}"'
        f'{style_attr} aria-hidden="true"></div>'
    )


def convert_label(match: re.Match[str]) -> str:
    attrs = match.group("attrs")
    body = match.group("body")
    plain = re.sub(r"<[^>]+>", "", body)
    has_visible_content = bool(html.unescape(plain).strip()) or bool(
        re.search(r"<(?:img|svg)\b", body, TAG_FLAGS)
    )
    is_option = "activity-option" in get_attr(attrs, "class")
    has_data_id = bool(get_attr(attrs, "data-id"))

    attrs = strip_interactive_attrs(attrs)
    if is_option:
        attrs = class_attr(attrs, "adt-static-option")
        return f"<div{attrs}>{body}</div>"
    if not has_visible_content and not has_data_id:
        return ""
    attrs = class_attr(attrs, "adt-static-label")
    return f"<span{attrs}>{body}</span>"


def convert_role_button(match: re.Match[str]) -> str:
    tag = match.group("tag")
    attrs = match.group("attrs")
    if not re.search(r"\brole\s*=\s*['\"]button['\"]", attrs, TAG_FLAGS):
        return match.group(0)
    attrs = remove_attr(attrs, "role")
    attrs = remove_attr(attrs, "draggable")
    attrs = remove_attr(attrs, "tabindex")
    classes = get_attr(attrs, "class")
    if "activity-item" in classes.split():
        classes = " ".join(token for token in classes.split() if token != "activity-item")
        attrs = remove_attr(attrs, "class")
        attrs += f' class="{html.escape(static_classes(classes, "adt-static-label"), quote=True)}"'
    return f"<{tag}{attrs}>"


def remove_generated_block(source: str, class_name: str) -> str:
    opening = re.compile(
        rf"<(?P<tag>div|span)\b(?=[^>]*\bclass\s*=\s*['\"][^'\"]*\b{re.escape(class_name)}\b[^'\"]*['\"])[^>]*>",
        TAG_FLAGS,
    )
    while True:
        match = opening.search(source)
        if not match:
            return source
        tag = match.group("tag")
        token = re.compile(rf"<{tag}\b[^>]*>|</{tag}\s*>", TAG_FLAGS)
        depth = 1
        end = None
        for candidate in token.finditer(source, match.end()):
            if candidate.group(0).lstrip().startswith("</"):
                depth -= 1
                if depth == 0:
                    end = candidate.end()
                    break
            else:
                depth += 1
        if end is None:
            raise RuntimeError(f"Unclosed {class_name} block")
        source = source[: match.start()] + source[end:]


def convert_file(path: Path, source_override: str | None = None) -> bool:
    current = path.read_text(encoding="utf-8-sig")
    source = source_override if source_override is not None else current
    if not re.search(
        r"role\s*=\s*['\"]activity['\"]|<(?:input|textarea|canvas|button)\b|data-section-type\s*=\s*['\"]static_exercise['\"]",
        source,
        TAG_FLAGS,
    ):
        return False

    updated = source
    updated = re.sub(r"<section(?P<attrs>[^>]*)>", convert_section, updated, flags=TAG_FLAGS)
    updated = re.sub(r"<input\b(?P<attrs>[^>]*)/?>", convert_input, updated, flags=TAG_FLAGS)
    updated = re.sub(
        r"<textarea\b(?P<attrs>[^>]*)>[\s\S]*?</textarea>",
        convert_textarea,
        updated,
        flags=TAG_FLAGS,
    )
    updated = re.sub(
        r"<select\b[^>]*>[\s\S]*?</select>",
        '<span class="adt-answer-space" aria-hidden="true"></span>',
        updated,
        flags=TAG_FLAGS,
    )
    updated = re.sub(
        r"<canvas\b(?P<attrs>[^>]*)>[\s\S]*?</canvas>",
        convert_canvas,
        updated,
        flags=TAG_FLAGS,
    )
    updated = re.sub(r"<button\b[^>]*>[\s\S]*?</button>", "", updated, flags=TAG_FLAGS)
    updated = re.sub(
        r"<div\b(?=[^>]*\bclass\s*=\s*['\"][^'\"]*\bdropzone\b[^'\"]*['\"])[^>]*>\s*<div\b[^>]*>[\s\S]*?</div>\s*</div>",
        "",
        updated,
        flags=TAG_FLAGS,
    )
    updated = re.sub(
        r"<div\b(?=[^>]*\bdata-submit-target\b)[^>]*>\s*</div>",
        "",
        updated,
        flags=TAG_FLAGS,
    )
    for class_name in ("feedback-container", "feedback-msg", "validation-mark"):
        updated = remove_generated_block(updated, class_name)
    updated = re.sub(
        r"<(?:p|div|span)\b(?=[^>]*\bid\s*=\s*['\"]overall-feedback['\"])[^>]*>[\s\S]*?</(?:p|div|span)>",
        "",
        updated,
        flags=TAG_FLAGS,
    )
    updated = re.sub(
        r"<label\b(?P<attrs>[^>]*)>(?P<body>[\s\S]*?)</label>",
        convert_label,
        updated,
        flags=TAG_FLAGS,
    )
    updated = re.sub(
        r"<(?P<tag>[a-z][a-z0-9:-]*)(?P<attrs>[^>]*)>",
        convert_role_button,
        updated,
        flags=TAG_FLAGS,
    )

    for name in (
        "data-activity-item",
        "data-answer",
        "data-aria-id",
        "data-correct",
        "data-explanation",
        "data-explanation-id",
        "data-submit-target",
    ):
        updated = re.sub(
            rf"\s+{re.escape(name)}(?![\w:-])(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+))?",
            "",
            updated,
            flags=TAG_FLAGS,
        )

    updated = re.sub(
        r"<script\b(?=[^>]*\bid\s*=\s*['\"]quiz-(?:correct-answers|explanations)['\"])[^>]*>[\s\S]*?</script>",
        "",
        updated,
        flags=TAG_FLAGS,
    )
    updated = re.sub(
        r"<script\b[^>]*>[\s\S]*?(?:window\.correctAnswers|\.getContext\(|clear-btn)[\s\S]*?</script>",
        "",
        updated,
        flags=TAG_FLAGS,
    )
    updated = re.sub(
        r"<style\b[^>]*>[\s\S]*?\.activity-option\.selected-option[\s\S]*?</style>",
        "",
        updated,
        flags=TAG_FLAGS,
    )

    if "static-exercises.css" not in updated:
        stylesheet = '    <link href="./assets/static-exercises.css?v=1" rel="stylesheet">\n'
        match = re.search(r"(?P<indent>\s*)</head>", updated, TAG_FLAGS)
        if not match:
            raise RuntimeError(f"Missing </head> in {path.name}")
        updated = updated[: match.start()] + "\n" + stylesheet + updated[match.start() :]

    ended_with_newline = updated.endswith(("\n", "\r"))
    updated = "\n".join(line.rstrip() for line in updated.splitlines())
    updated = re.sub(r"\n{4,}", "\n\n\n", updated)
    if ended_with_newline:
        updated += "\n"

    if updated == current:
        return False
    path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("book", nargs="?", default=".")
    parser.add_argument(
        "--from-git-head",
        action="store_true",
        help="Rebuild tracked HTML from HEAD before applying the conversion.",
    )
    args = parser.parse_args()
    root = Path(args.book).resolve()
    changed = []
    for path in sorted(root.glob("*.html")):
        source_override = None
        if args.from_git_head:
            relative = path.relative_to(root).as_posix()
            source_override = subprocess.check_output(
                ["git", "show", f"HEAD:{relative}"],
                cwd=root,
            ).decode("utf-8-sig")
        if convert_file(path, source_override):
            changed.append(path.name)
    print(f"Converted {len(changed)} HTML files to static exercises.")


if __name__ == "__main__":
    main()
