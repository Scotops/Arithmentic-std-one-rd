"""Project-specific release gate for the 134-page Arithmetic Standard One ADT."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "tmp" / "adt-quality-final.json" / "adt-audit.json"
LOCALE = ROOT / "content" / "i18n" / "en-US"


def fail(message: str) -> None:
    raise AssertionError(message)


def main() -> None:
    report = json.loads(AUDIT.read_text(encoding="utf-8"))
    unexpected = []
    for issue in report["issues"]:
        code = issue["code"]
        file = issue.get("file", "")
        element = issue.get("element_id", "")
        allowed = False
        if issue["severity"] == "error" and code == "missing-text-mapping":
            allowed = bool(re.fullmatch(r"qz\d{3}\.html", file) and element == file[:5])
        elif issue["severity"] == "warning" and code in {
            "possible-answer-leak", "small-image-source", "html-not-in-manifest"
        }:
            allowed = True
        elif issue["severity"] == "warning" and code in {
            "missing-h1", "missing-language", "missing-main", "missing-title"
        }:
            allowed = file == "content/navigation/nav.html"
        if not allowed:
            unexpected.append(issue)
    if unexpected:
        fail(f"Unexpected static-audit issues: {unexpected[:5]}")

    pages = json.loads((ROOT / "content" / "pages.json").read_text(encoding="utf-8"))
    expected_folios = ["Front Cover", "Cover", "ii", "iii", "iv", "v", "vi"] + [str(i) for i in range(1, 127)] + ["Back Cover"]
    if len(pages) != 134:
        fail(f"Expected 134 physical pages, got {len(pages)}")
    if [str(page.get("page_number")) for page in pages] != expected_folios:
        fail("Physical-to-printed page mapping is not Front Cover, Cover, ii-vi, 1-126, Back Cover.")

    all_html = "\n".join(path.read_text(encoding="utf-8") for path in ROOT.glob("*.html"))
    forbidden = ["pdf-facsimile.js", "static-textbook.js", "offline-preloader-audio-dash-only.js", "images/pdf-pages/", "_page.png"]
    for token in forbidden:
        if token in all_html:
            fail(f"Forbidden screenshot/static-reader reference remains: {token}")
    if (ROOT / "images" / "pdf-pages").exists():
        fail("Full-page screenshot asset directory still exists.")

    for index, (page, folio) in enumerate(zip(pages, expected_folios), start=1):
        page_file = ROOT / page["href"].split("#", 1)[0]
        if not page_file.is_file():
            fail(f"Manifest page is missing: {page_file}")
        source = page_file.read_text(encoding="utf-8")
        section_meta = re.search(
            r'<meta\b(?=[^>]*\bname=["\']page-section-id["\'])(?=[^>]*\bcontent=["\']([^"\']+)["\'])[^>]*>',
            source,
            re.IGNORECASE,
        )
        if not section_meta or section_meta.group(1) != str(index):
            fail(f"Incorrect page-section-id in {page_file.name}")
        footer = re.search(r'<(?:p|footer)\b[^>]*class="[^"]*printed-folio[^"]*"[^>]*>(.*?)</(?:p|footer)>', source, re.I | re.S)
        footer_text = re.sub(r'<[^>]+>', ' ', footer.group(1)) if footer else ''
        if " ".join(footer_text.split()) != folio:
            fail(f"Incorrect visible printed folio in {page_file.name}: expected {folio}")
        if "ai-narration-disclosure" in source:
            fail(f"Unwanted narration disclosure remains in {page_file.name}")

    disclosure_text = "Read-aloud narration uses an AI-generated voice."
    unwanted_disclosures = [
        page_file.name
        for page_file in ROOT.glob("*.html")
        if "ai-narration-disclosure" in page_file.read_text(encoding="utf-8")
        or disclosure_text in page_file.read_text(encoding="utf-8")
    ]
    if unwanted_disclosures:
        fail(f"Unwanted narration disclosure remains: {unwanted_disclosures[:10]}")

    config = json.loads((ROOT / "assets" / "config.json").read_text(encoding="utf-8"))
    features = config["features"]
    for feature in ("readAloud", "describeImages", "signLanguage"):
        if not features.get(feature):
            fail(f"Required feature is disabled: {feature}")
    if features.get("activities"):
        fail("Activities must be disabled because the source exercises are static.")

    texts = json.loads((LOCALE / "texts.json").read_text(encoding="utf-8-sig"))
    audios = json.loads((LOCALE / "audios.json").read_text(encoding="utf-8-sig"))
    leaked = [key for key, value in texts.items() if "_ans_" in key or "_ans_" in str(value)]
    if leaked:
        fail(f"Hidden answer-key localization remains: {leaked[:10]}")
    if set(texts) != set(audios):
        fail(f"Text/audio key mismatch: texts={len(texts)}, audios={len(audios)}")
    for identifier, mapping in audios.items():
        audio_file = LOCALE / "audio" / str(mapping).split("?", 1)[0]
        if not audio_file.is_file() or audio_file.stat().st_size < 500:
            fail(f"Missing or empty audio for {identifier}: {audio_file.name}")

    static_exercises = 0
    static_answer_spaces = 0
    controls = 0
    disabled = 0
    images = 0
    for path in ROOT.glob("*.html"):
        source_html = path.read_text(encoding="utf-8")
        static_exercises += len(re.findall(r'\bdata-section-type=["\']static_exercise["\']', source_html, re.I))
        static_answer_spaces += len(re.findall(r'\badt-(?:answer-space|answer-space--multiline|static-drawing-space)\b', source_html, re.I))
        controls += len(re.findall(r'<(?:input|button|select|textarea|canvas)\b|\brole=["\'](?:activity|button)["\']', source_html, re.I))
        disabled += len(re.findall(r'\sdisabled(?:\s|=|>)|aria-disabled=["\']true["\']', source_html, re.I))
        for token in ("data-submit-target", "data-activity-item", "data-correct-answers", "data-option-explanations", "feedback-container"):
            if token in source_html:
                fail(f"Generated answering metadata remains in {path.name}: {token}")
        for source in re.findall(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\']', source_html, re.I):
            images += 1
            source = source.split("?", 1)[0]
            if source.startswith(("http://", "https://", "data:")):
                continue
            if not (path.parent / source).resolve().is_file():
                fail(f"Missing image in {path.name}: {source}")
    if static_exercises < 20 or static_answer_spaces < 100 or controls or disabled:
        fail(
            "Static exercise gate failed: "
            f"sections={static_exercises}, spaces={static_answer_spaces}, "
            f"controls={controls}, disabled={disabled}"
        )

    print(json.dumps({
        "physical_pages": len(pages),
        "printed_folios": "Front Cover, Cover, ii-vi, 1-126, Back Cover",
        "text_audio_targets": len(audios),
        "static_exercise_sections": static_exercises,
        "static_answer_spaces": static_answer_spaces,
        "interactive_answer_controls": controls,
        "image_occurrences": images,
        "accepted_structural_container_findings": 0,
        "unexpected_issues": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
