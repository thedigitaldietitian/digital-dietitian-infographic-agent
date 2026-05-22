"""Image generation workflow for v2 of the infographic agent."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from src.config import Settings


BRAND_COLOURS = [
    "#1d3b2a",
    "#ff9cb7",
    "#ffe78b",
    "#fff8d9",
    "#f9fff3",
    "#e2efcc",
    "#fff3f6",
]

OUTPUT_HEADERS = [
    "Image Asset Link",
    "Local Image Path",
    "Google Drive Image Link",
    "Image Generation Status",
    "Visual QA",
    "Human Review Needed",
    "Next Action",
    "Ready for Buffer",
    "Buffer Status",
]


@dataclass(frozen=True)
class InfographicPackage:
    """Structured content read from one completed Content Calendar row."""

    row_number: int
    post_id: str
    topic: str
    design_prompt: str
    draft_text: str
    columns: list[str]
    rows: list[str]
    matrix: list[list[str]]


@dataclass(frozen=True)
class VisualQAResult:
    """Basic QA status for the generated infographic workflow."""

    status: str
    human_review_needed: str
    next_action: str
    checks: dict[str, bool]

    def to_sheet_text(self) -> str:
        passed = [name for name, ok in self.checks.items() if ok]
        failed = [name for name, ok in self.checks.items() if not ok]
        parts = [f"{self.status}."]
        if passed:
            parts.append("Recorded checks passed: " + ", ".join(passed) + ".")
        if failed:
            parts.append("Needs human review for: " + ", ".join(failed) + ".")
        return " ".join(parts)


def find_latest_eligible_infographic_row(
    rows: list[dict[str, str]],
) -> InfographicPackage | None:
    """Return the newest infographic row that has content but no generated image."""
    for row in reversed(rows):
        if not is_eligible_for_image_generation(row):
            continue
        return package_from_sheet_row(row)
    return None


def is_eligible_for_image_generation(row: dict[str, str]) -> bool:
    """Check whether a sheet row is ready for v2 image generation."""
    format_value = row.get("Format", "").lower()
    has_image = any(
        row.get(header, "").strip()
        for header in ("Image Asset Link", "Local Image Path", "Google Drive Image Link")
    )
    has_content = bool(row.get("Draft Text", "").strip() and row.get("Design Prompt", "").strip())
    return "infographic" in format_value and has_content and not has_image


def package_from_sheet_row(row: dict[str, str]) -> InfographicPackage:
    """Parse the draft text in a sheet row into the 4 x 5 infographic package."""
    draft_text = row.get("Draft Text", "")
    columns = parse_pipe_list(draft_text, "Columns")
    row_labels = parse_pipe_list(draft_text, "Rows")
    matrix = parse_ingredient_matrix(draft_text, row_labels)

    return InfographicPackage(
        row_number=int(row["_sheet_row_number"]),
        post_id=row.get("Post ID", "infographic").strip() or "infographic",
        topic=row.get("Topic / Hook", "").strip(),
        design_prompt=row.get("Design Prompt", "").strip(),
        draft_text=draft_text,
        columns=columns,
        rows=row_labels,
        matrix=matrix,
    )


def parse_pipe_list(text: str, label: str) -> list[str]:
    """Parse a line like 'Columns: A | B | C | D'."""
    match = re.search(rf"^{re.escape(label)}:\s*(.+)$", text, flags=re.MULTILINE)
    if not match:
        return []
    return [part.strip() for part in match.group(1).split("|") if part.strip()]


def parse_ingredient_matrix(text: str, row_labels: list[str]) -> list[list[str]]:
    """Parse the matrix lines from the v1 draft text format."""
    matrix = []
    for row_label in row_labels:
        match = re.search(rf"^{re.escape(row_label)}:\s*(.+)$", text, flags=re.MULTILINE)
        if not match:
            continue
        matrix.append([part.strip() for part in match.group(1).split("|") if part.strip()])
    return matrix


def build_final_image_prompt(
    settings: Settings,
    package: InfographicPackage,
) -> str:
    """Create the strict v2 image prompt from the completed content package."""
    matrix_lines = []
    for row_index, row_label in enumerate(package.rows):
        matrix_lines.append(f"{row_label}: " + " | ".join(package.matrix[row_index]))

    return "\n".join(
        [
            "Generate one final Instagram infographic image.",
            "Canvas and layout rules:",
            "- 4:5 portrait ratio. The final file will be saved at 1080 x 1350 px.",
            "- Use a strict matrix layout only: exactly 4 columns and exactly 5 rows.",
            "- Do not use a freeform collage layout.",
            "- Use a soft blush background.",
            "- Use Open Sans-style typography.",
            "- Use only these brand colours: " + ", ".join(BRAND_COLOURS) + ".",
            "- Include realistic food visuals in every cell, matched to the ingredients.",
            "- Keep all text readable, aligned, and inside the grid.",
            "",
            "Required visible text:",
            "- BUILD YOUR",
            "- BLOAT-FREE",
            "- SAVE IT FOR LATER",
            f"- {settings.instagram_handle}",
            "",
            "Brand context:",
            "- Aleks Jagiello BSc (Hons), MSc, RD",
            "- The Digital Dietitian",
            f"- Instagram handle: {settings.instagram_handle}",
            "",
            "Content package to preserve:",
            f"- Topic: {package.topic}",
            "- Column names: " + " | ".join(package.columns),
            "- Row labels: " + " | ".join(package.rows),
            "- Ingredient matrix:",
            *matrix_lines,
            "",
            "Low FODMAP logic:",
            "- Preserve the exact ingredient pairings from the content package.",
            "- Keep portions and label-check wording visible where provided.",
            "- Do not add high FODMAP swaps or extra ingredients.",
            "",
            "Approved template style:",
            package.design_prompt,
        ]
    )


def run_basic_visual_qa(package: InfographicPackage) -> VisualQAResult:
    """Record deterministic QA checks and flag human review for visual fidelity."""
    prompt_text = package.design_prompt + "\n" + package.draft_text
    checks = {
        "4 columns present in content package": len(package.columns) == 4,
        "5 rows present in content package": len(package.rows) == 5,
        "4x5 ingredient matrix present": len(package.matrix) == 5
        and all(len(row) == 4 for row in package.matrix),
        "handle present in prompt": "@ibs.gutdietitian" in prompt_text,
        "save badge present in prompt": "SAVE IT FOR LATER" in prompt_text,
        "BLOAT-FREE headline present in prompt": "BLOAT-FREE" in prompt_text,
        "approved matrix style requested": "exactly 4" in prompt_text.lower()
        and "exactly 5" in prompt_text.lower(),
    }

    if all(checks.values()):
        return VisualQAResult(
            status="PASS WITH HUMAN REVIEW",
            human_review_needed="Yes",
            next_action=(
                "Human review needed before Buffer scheduling: confirm generated image "
                "visually contains the 4x5 matrix, food visuals, handle, save badge and headline."
            ),
            checks=checks,
        )

    return VisualQAResult(
        status="NEEDS FIX",
        human_review_needed="Yes",
        next_action="Fix the content package before image generation, then rerun v2.",
        checks=checks,
    )


def generate_infographic_image(
    settings: Settings,
    prompt: str,
    post_id: str,
) -> str:
    """Generate an infographic image with OpenAI and save it under outputs/."""
    from openai import OpenAI

    output_dir = Path(settings.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_post_id = re.sub(r"[^A-Za-z0-9._-]+", "-", post_id).strip("-") or "infographic"
    raw_path = output_dir / f"{safe_post_id}-raw.png"
    final_path = output_dir / f"{safe_post_id}.png"

    client = OpenAI()
    result = client.images.generate(
        model=settings.openai_image_model,
        prompt=prompt,
        size=settings.image_generation_size,
        quality="high",
    )

    image_data = result.data[0].b64_json
    if not image_data:
        raise RuntimeError("OpenAI image generation did not return base64 image data.")

    raw_path.write_bytes(base64.b64decode(image_data))
    fit_image_to_4x5(raw_path, final_path)
    raw_path.unlink(missing_ok=True)
    return str(final_path)


def fit_image_to_4x5(source_path: Path, output_path: Path) -> None:
    """Center-crop and resize any generated image to 1080 x 1350."""
    from PIL import Image

    target_width = 1080
    target_height = 1350
    target_ratio = target_width / target_height

    with Image.open(source_path) as image:
        image = image.convert("RGB")
        width, height = image.size
        ratio = width / height

        if ratio > target_ratio:
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            crop_box = (left, 0, left + new_width, height)
        else:
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            crop_box = (0, top, width, top + new_height)

        image.crop(crop_box).resize(
            (target_width, target_height),
            Image.Resampling.LANCZOS,
        ).save(output_path, "PNG", optimize=True)


def dry_run_summary(package: InfographicPackage, prompt: str) -> dict[str, Any]:
    """Return a compact dry-run payload for CLI output."""
    qa = run_basic_visual_qa(package)
    return {
        "row_number": package.row_number,
        "post_id": package.post_id,
        "topic": package.topic,
        "columns": package.columns,
        "rows": package.rows,
        "matrix": package.matrix,
        "visual_qa": qa.to_sheet_text(),
        "human_review_needed": qa.human_review_needed,
        "next_action": qa.next_action,
        "image_prompt": prompt,
    }
