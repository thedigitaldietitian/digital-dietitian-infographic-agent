"""Deterministic Pillow renderer for the approved Build Your infographic template."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import textwrap

from PIL import Image, ImageDraw, ImageFont

from src.config import Settings
from src.food_assets import FoodAssetLibrary, FoodAssetReport
from src.image_generation import InfographicPackage


CANVAS_SIZE = (1080, 1350)
DEEP_GREEN = "#1d3b2a"
SOFT_PINK = "#ff9cb7"
WARM_YELLOW = "#ffe78b"
SOFT_CREAM = "#f9fff3"
PALE_BLUSH = "#fff3f6"
PALE_GREEN = "#e2efcc"


@dataclass(frozen=True)
class TemplateRenderResult:
    """Result of one deterministic template render."""

    image_path: str
    asset_report: FoodAssetReport


def render_infographic_template(
    settings: Settings,
    package: InfographicPackage,
    output_path: str | None = None,
    generate_missing_assets: bool = False,
) -> TemplateRenderResult:
    """Render a fixed-layout 1080 x 1350 PNG from a parsed content package."""
    validate_template_package(package)

    output_dir = Path(settings.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_post_id = re.sub(r"[^A-Za-z0-9._-]+", "-", package.post_id).strip("-")
    final_path = (
        Path(output_path)
        if output_path
        else output_dir / f"{safe_post_id}-rendered-v2-3.png"
    )

    image = Image.new("RGBA", CANVAS_SIZE, PALE_BLUSH)
    draw = ImageDraw.Draw(image)
    asset_library = FoodAssetLibrary(
        settings=settings,
        generate_missing_assets=generate_missing_assets,
    )

    fonts = TemplateFonts()
    draw_background(draw)
    draw_header(draw, fonts, package)
    draw_matrix(image, draw, fonts, package, asset_library)
    draw_footer(draw, fonts, settings)

    image.convert("RGB").save(final_path, "PNG", optimize=True)
    return TemplateRenderResult(str(final_path), asset_library.report)


def validate_template_package(package: InfographicPackage) -> None:
    """Fail early if the Sheet package cannot render into the approved matrix."""
    if len(package.columns) != 4:
        raise ValueError(f"Expected exactly 4 columns, found {len(package.columns)}.")
    if len(package.rows) != 5:
        raise ValueError(f"Expected exactly 5 rows, found {len(package.rows)}.")
    if len(package.matrix) != 5 or any(len(row) != 4 for row in package.matrix):
        raise ValueError("Expected a 4x5 ingredient matrix.")


class TemplateFonts:
    """Load Open Sans when available, otherwise fall back to a clean sans-serif."""

    def __init__(self) -> None:
        regular_path = find_font(
            [
                "fonts/OpenSans-Regular.ttf",
                "/Library/Fonts/OpenSans-Regular.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/System/Library/Fonts/Supplemental/Helvetica.ttf",
            ]
        )
        bold_path = find_font(
            [
                "fonts/OpenSans-Bold.ttf",
                "/Library/Fonts/OpenSans-Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Supplemental/Helvetica Bold.ttf",
            ]
        )
        self.regular_path = regular_path
        self.bold_path = bold_path or regular_path

    def regular(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return load_font(self.regular_path, size)

    def bold(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        return load_font(self.bold_path, size)


def find_font(paths: list[str]) -> str | None:
    """Return the first available local font path."""
    for path in paths:
        if Path(path).exists():
            return path
    return None


def load_font(path: str | None, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a TrueType font or Pillow's default fallback."""
    if path:
        return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def draw_background(draw: ImageDraw.ImageDraw) -> None:
    """Draw the soft template background and subtle brand accents."""
    draw.rectangle((0, 0, CANVAS_SIZE[0], CANVAS_SIZE[1]), fill=PALE_BLUSH)
    draw.rounded_rectangle((36, 36, 1044, 1314), radius=34, fill=SOFT_CREAM)
    draw.rounded_rectangle((58, 58, 1022, 1292), radius=28, outline=PALE_GREEN, width=4)
    draw.rectangle((36, 0, 1044, 46), fill=PALE_BLUSH)
    draw.rectangle((36, 1304, 1044, 1350), fill=PALE_BLUSH)


def draw_header(
    draw: ImageDraw.ImageDraw,
    fonts: TemplateFonts,
    package: InfographicPackage,
) -> None:
    """Draw the fixed heading block."""
    draw.text((72, 58), "BUILD YOUR", font=fonts.bold(52), fill=DEEP_GREEN)
    draw.text((72, 112), "BLOAT-FREE", font=fonts.bold(86), fill=SOFT_PINK)
    draw.text((76, 212), extract_subtitle(package), font=fonts.bold(41), fill=DEEP_GREEN)

    badge_box = (782, 70, 1006, 142)
    draw.rounded_rectangle(badge_box, radius=28, fill=WARM_YELLOW, outline=DEEP_GREEN, width=3)
    draw_centered_text(
        draw,
        "SAVE IT\nFOR LATER",
        badge_box,
        fonts.bold(22),
        DEEP_GREEN,
        line_spacing=5,
    )


def extract_subtitle(package: InfographicPackage) -> str:
    """Use the subtitle from the draft text where possible."""
    for line in package.draft_text.splitlines():
        text = line.strip()
        if text and text not in {"BUILD YOUR", "BLOAT-FREE", "SAVE IT FOR LATER"}:
            if text.startswith(("Columns:", "Rows:", "Ingredient matrix:")):
                continue
            return text.upper()
    topic = package.topic.upper().replace("BUILD YOUR BLOAT-FREE", "").strip()
    return topic or "LOW FODMAP SNACK PLATE"


def draw_matrix(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    fonts: TemplateFonts,
    package: InfographicPackage,
    asset_library: FoodAssetLibrary,
) -> None:
    """Draw the exact 4 column x 5 row matrix plus left label column."""
    left = 60
    top = 304
    label_width = 200
    cell_width = 196
    gap = 10
    header_height = 92
    row_height = 156

    for col_index, column in enumerate(package.columns):
        x0 = left + label_width + gap + col_index * (cell_width + gap)
        x1 = x0 + cell_width
        draw.rounded_rectangle((x0, top, x1, top + header_height), radius=20, fill=PALE_GREEN)
        draw_centered_text(
            draw,
            fit_text(column, 13),
            (x0 + 8, top + 8, x1 - 8, top + header_height - 8),
            fonts.bold(25),
            DEEP_GREEN,
            line_spacing=5,
        )

    for row_index, row_label in enumerate(package.rows):
        y0 = top + header_height + gap + row_index * (row_height + gap)
        y1 = y0 + row_height
        label_box = (left, y0, left + label_width, y1)
        draw.rounded_rectangle(label_box, radius=18, fill=PALE_GREEN)
        draw_wrapped_text(
            draw,
            row_label,
            (left + 18, y0 + 26, left + label_width - 18, y1 - 22),
            fonts.bold(26),
            DEEP_GREEN,
            max_chars=12,
            line_spacing=6,
        )

        for col_index, ingredient in enumerate(package.matrix[row_index]):
            x0 = left + label_width + gap + col_index * (cell_width + gap)
            x1 = x0 + cell_width
            cell_box = (x0, y0, x1, y1)
            fill = SOFT_CREAM if (row_index + col_index) % 2 == 0 else "#fff8d9"
            draw.rounded_rectangle(cell_box, radius=18, fill=fill, outline=PALE_BLUSH, width=2)
            asset = asset_library.resolve(ingredient)
            if asset.path:
                paste_food_asset(image, asset.path, cell_box)
            else:
                draw_food_placeholder(draw, cell_box, row_index, col_index)
            draw_wrapped_text(
                draw,
                normalize_ingredient_text(ingredient),
                (x0 + 12, y0 + 78, x1 - 12, y1 - 12),
                fonts.bold(20),
                DEEP_GREEN,
                max_chars=15,
                line_spacing=4,
                center=True,
            )


def paste_food_asset(
    image: Image.Image,
    asset_path: str,
    box: tuple[int, int, int, int],
) -> None:
    """Paste a transparent food asset at the top center of a cell."""
    x0, y0, x1, _ = box
    with Image.open(asset_path) as asset:
        asset = asset.convert("RGBA")
        asset.thumbnail((94, 64), Image.Resampling.LANCZOS)
        x = x0 + ((x1 - x0) - asset.width) // 2
        y = y0 + 10 + ((58 - asset.height) // 2)
        image.alpha_composite(asset, (x, y))


def draw_food_placeholder(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    row_index: int,
    col_index: int,
) -> None:
    """Draw neat non-AI food markers until approved food image assets exist."""
    x0, y0, x1, _ = box
    cx = (x0 + x1) // 2
    cy = y0 + 43
    palette = [WARM_YELLOW, SOFT_PINK, PALE_GREEN, "#fff8d9"]
    fill = palette[(row_index + col_index) % len(palette)]
    outline = DEEP_GREEN

    if row_index == 0:
        draw.rounded_rectangle((cx - 44, cy - 24, cx + 44, cy + 24), radius=12, fill=fill, outline=outline, width=2)
    elif row_index == 1:
        draw.ellipse((cx - 42, cy - 28, cx + 42, cy + 28), fill=fill, outline=outline, width=2)
        draw.ellipse((cx - 24, cy - 18, cx + 24, cy + 18), outline=outline, width=2)
    elif row_index == 2:
        for offset in (-34, 0, 34):
            draw.ellipse((cx + offset - 20, cy - 24, cx + offset + 20, cy + 24), fill=fill, outline=outline, width=2)
    elif row_index == 3:
        draw.ellipse((cx - 50, cy - 30, cx + 50, cy + 30), fill=SOFT_CREAM, outline=outline, width=2)
        draw.ellipse((cx - 34, cy - 18, cx + 34, cy + 18), fill=fill)
    else:
        for offset in (-36, -12, 12, 36):
            draw.ellipse((cx + offset - 13, cy - 14, cx + offset + 13, cy + 14), fill=fill, outline=outline, width=2)


def draw_footer(
    draw: ImageDraw.ImageDraw,
    fonts: TemplateFonts,
    settings: Settings,
) -> None:
    """Draw the handle and a small review-safe note at the bottom."""
    draw.text((72, 1260), settings.instagram_handle, font=fonts.bold(28), fill=DEEP_GREEN)
    draw.text(
        (676, 1266),
        "Template render for review",
        font=fonts.regular(18),
        fill=DEEP_GREEN,
    )


def normalize_ingredient_text(text: str) -> str:
    """Clean compact ingredient text for readable cell rendering."""
    text = text.replace("; check label", "\ncheck label")
    text = text.replace(", check label", "\ncheck label")
    text = text.replace(", ", "\n", 1)
    return text


def fit_text(text: str, max_chars: int) -> str:
    """Wrap short headings without changing their words."""
    return "\n".join(textwrap.wrap(text, width=max_chars, break_long_words=False))


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
    max_chars: int,
    line_spacing: int = 4,
    center: bool = False,
) -> None:
    """Draw wrapped text clipped to the provided box."""
    x0, y0, x1, y1 = box
    lines = []
    for part in text.splitlines():
        lines.extend(textwrap.wrap(part, width=max_chars, break_long_words=False) or [""])

    line_height = text_height(draw, "Ag", font) + line_spacing
    total_height = len(lines) * line_height - line_spacing
    y = y0 if not center else max(y0, y0 + ((y1 - y0) - total_height) // 2)

    for line in lines:
        if y + line_height > y1 + line_spacing:
            break
        if center:
            width = text_width(draw, line, font)
            x = x0 + ((x1 - x0) - width) // 2
        else:
            x = x0
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
    line_spacing: int = 4,
) -> None:
    """Draw multi-line text centered in a box."""
    x0, y0, x1, y1 = box
    lines = text.splitlines()
    line_height = text_height(draw, "Ag", font) + line_spacing
    total_height = len(lines) * line_height - line_spacing
    y = y0 + ((y1 - y0) - total_height) // 2
    for line in lines:
        width = text_width(draw, line, font)
        draw.text((x0 + ((x1 - x0) - width) // 2, y), line, font=font, fill=fill)
        y += line_height


def text_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> int:
    """Return rendered text width."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def text_height(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> int:
    """Return rendered text height."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]
