"""Apply source-reviewed, assessment-safe illustration descriptions."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXTS = ROOT / "content" / "i18n" / "en-US" / "texts.json"


def repeated(intro: str, item: str, count: int) -> str:
    return f"{intro}: " + "; ".join([item] * count) + "."


OVERRIDES = {
    "pg007_im030_seg001_v1_crop_v1_crop2": repeated("First orange group", "orange", 6),
    "pg007_im030_seg002_v1_crop1": repeated("Second orange group", "orange", 3),
    "pg007_im030_seg003_v1_crop1": repeated("First football group", "football", 4),
    "pg007_im030_seg004_v1_crop1": repeated("Second football group", "football", 7),
    "pg008_im018_seg001_v1_crop_v1": repeated("Cow option", "cow", 7),
    "pg008_im018_seg002_v1": repeated("Chicken option", "chicken", 6),
    "pg012_im015_seg001_v1_crop_v1_crop1": repeated("A row to count", "football", 9),
    "pg012_im015_seg002_v1_crop_v1_crop1": repeated("A row to count", "backpack", 6),
    "pg012_im015_seg003_v1_crop_v1": repeated("A row to count", "bicycle", 3),
    "pg012_im015_seg004_v1_crop_v1": repeated("A row to count", "dress", 1),
    "pg012_im015_seg005_v1_crop_v1": repeated("A row to count", "pen", 2),
    "pg012_im015_seg006_v1_crop_v1": repeated("A row to count", "red car", 5),
    "pg012_im015_seg007_v1_crop_v1_crop1": repeated("A row to count", "pair of shoes", 2),
    "pg012_im015_seg008_v1_crop_v1": repeated("A row to count", "umbrella", 7),
    "pg015_im013_seg001_v1_crop_v1": repeated("A fruit group to count", "apple", 3),
    "pg015_im013_seg002_v1_crop_v1": repeated("A fruit group to count", "watermelon", 4),
    "pg015_im013_seg003_v1_crop_v1": repeated("A fruit group to count", "avocado", 6),
    "pg015_im013_seg004_v1_crop_v1": repeated("A fruit group to count", "mango", 7),
    "pg015_im013_seg005_v1_crop_v1": repeated("A fruit group to count", "pineapple", 8),
    "pg024_im011": (
        "Fruit-counting picture. " + repeated("Tomatoes", "tomato", 6)
        + " " + repeated("Green fruits", "green fruit", 10)
        + " " + repeated("Mangoes", "mango", 7)
        + " " + repeated("Bunches of grapes", "bunch of grapes", 8)
        + " " + repeated("Pineapples", "pineapple", 4)
        + " " + repeated("Watermelons", "watermelon", 5)
        + " " + repeated("Bananas", "banana", 4)
        + " " + repeated("Soursops", "soursop", 2)
        + " " + repeated("Papayas", "papaya", 1)
    ),
    "pg052_im028_crop_v1_crop1": (
        repeated("First row to count", "tomato", 8)
        + " " + repeated("Second row to count", "bell", 10)
        + " " + repeated("Third row to count", "green fruit", 9)
    ),
    "pg054_im006_crop1": "Five tomatoes arranged in two rows.",
    "pg054_im009_crop1": "Four birds arranged in two rows.",
    "pg054_im010_seg003_v1_crop1_crop1": "Three red cars arranged in two rows.",
    "pg054_im010_seg004_v1_crop1": "One red car.",
    "pg126_im008_seg001_v1_crop1": "Figure one is pale yellow, curved, closed, wider than it is tall, and has no corners.",
    "pg126_im008_seg002_v1_crop1": "Figure five is blue and has four straight sides with corners at the top, bottom, left, and right.",
    "pg126_im008_seg003_v1_crop1": "Figure two is yellow and has four equal straight sides and four right-angle corners.",
    "pg126_im008_seg004_v1_crop1": "Figure six is gold and has five pointed arms.",
    "pg126_im008_seg005_v1_crop1": "Figure three is light blue and has four right-angle corners, with two longer horizontal sides and two shorter vertical sides.",
    "pg126_im008_seg006_v1_crop1": "Figure seven is green and has four right-angle corners, with two longer horizontal sides and two shorter vertical sides.",
    "pg126_im008_seg007_v1_crop_v1_crop1": "Figure four is light green and has four equal straight sides and four right-angle corners.",
    "pg126_im008_seg008_v1_crop1": "Figure eight is purple and has three straight sides and three corners.",
    "pg129_im013": "Figure a is a blue, ball-like round form with curved shading and a bright highlight.",
    "pg129_im014": "Figure b is red, pointed at the bottom, wide and curved at the top, with shaded sides.",
    "pg129_im018_seg003_v1_crop_v1": "Figure c is flat, orange, curved, wider than it is tall, and has no corners.",
    "pg129_im003": "Figure d is flat and yellow with four equal straight sides and four right-angle corners.",
    "pg129_im018_seg005_v1_crop1": "Figure e is flat and green with three straight sides and three corners.",
    "pg129_im018_seg006_v1_crop_v1_crop1": "Figure f is an orange box-like form with a visible top, front, and side.",
    "pg129_im018_seg007_v1_crop_v1_crop1": "Figure g is a flat blue round shape with no corners.",
    "pg129_im018_seg008_v1_crop_v1_crop1": "Figure h is a red box-like form with a visible top and two shaded sides.",
    "pg129_im018_seg009_v1_crop1": "Figure i is flat and yellow with four right-angle corners and two longer horizontal sides.",
    "pg129_im018_seg010_v1_crop_v1_crop1": "Figure j is a blue tube-like form with a curved side and a circular end.",
    "pg131_im005_crop1": "A pale pink figure with four equal straight sides and four right-angle corners.",
    "pg132_im006": "An abacus to solve. Tens rod: bead; bead. Ones rod: bead; bead; bead; bead; bead.",
    "pg132_im008_crop_v1": "A yellow figure with three straight sides and three corners.",
}


def repair_page_54() -> None:
    path = ROOT / "pg054_sec001.html"
    source = path.read_text(encoding="utf-8")
    old = '<img src="images/pg054_im010_seg003_v1_crop1_crop1.png" data-id="pg054_im010_seg003_v1_crop1_crop1" alt="A group of seven cars." class="max-h-[225px] max-w-full object-contain max-sm:max-h-[70px]" style="max-width: 100%; height: auto;">'
    one = '<img src="images/pg054_im010_seg004_v1_crop1.png" data-id="pg054_im010_seg004_v1_crop1" alt="One red car." class="max-w-full h-auto">'
    replacement = '<div class="grid grid-cols-4 gap-1 max-sm:gap-0.5" aria-label="Seven individual cars to count">' + one * 7 + "</div>"
    if old not in source:
        if "Seven individual cars to count" in source:
            return
        raise SystemExit("Could not locate the incorrect seven-car image on page 54")
    path.write_text(source.replace(old, replacement, 1), encoding="utf-8", newline="")


def main() -> None:
    texts = json.loads(TEXTS.read_text(encoding="utf-8"))
    answer_keys = [identifier for identifier in texts if "_ans_" in identifier]
    for identifier in answer_keys:
        del texts[identifier]
    missing = sorted(set(OVERRIDES) - set(texts))
    unexpected = sorted(set(missing) - {"pg054_im010_seg004_v1_crop1"})
    if unexpected:
        raise SystemExit(f"Unknown description IDs: {unexpected}")
    texts.update(OVERRIDES)
    TEXTS.write_text(json.dumps(texts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="")
    repair_page_54()
    print(f"Applied {len(OVERRIDES)} reviewed descriptions.")
    print(f"Removed {len(answer_keys)} hidden answer-key values from narration text.")


if __name__ == "__main__":
    main()
