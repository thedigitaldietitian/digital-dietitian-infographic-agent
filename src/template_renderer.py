"""Deterministic Pillow renderer for approved Build Your infographic templates."""

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
PALE_YELLOW = "#fff8d9"
SOFT_CREAM = "#f9fff3"
PALE_GREEN = "#e2efcc"
PALE_BLUSH = "#fff3f6"
LAYOUT_MODES = {"choice_row", "column_combo"}


@dataclass(frozen=True)
class TemplateRenderResult:
    """Result of one deterministic template render."""

    image_path: str
    asset_report: FoodAssetReport
    layout_mode: str


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


def render_infographic_template(
    settings: Settings,
    package: InfographicPackage,
    output_path: str | None = None,
    generate_missing_assets: bool = False,
    layout_mode: str = "choice_row",
) -> TemplateRenderResult:
    """Render a fixed-layout 1080 x 1350 PNG from a parsed content package."""
    validate_template_package(package)
    if layout_mode not in LAYOUT_MODES:
        raise ValueError(f"Unsupported layout mode: {layout_mode}.")

    output_dir = Path(settings.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_post_id = re.sub(r"[^A-Za-z0-9._-]+", "-", package.post_id).strip("-")
    version_suffix = "v2-4" if layout_mode == "choice_row" else "column-combo"
    final_path = (
        Path(output_path)
        if output_path
        else output_dir / f"{safe_post_id}-rendered-{version_suffix}.png"
    )

    image = Image.new("RGBA", CANVAS_SIZE, PALE_BLUSH)
    draw = ImageDraw.Draw(image)
    fonts = TemplateFonts()
    asset_library = FoodAssetLibrary(
        settings=settings,
        generate_missing_assets=generate_missing_assets,
    )

    draw_background(draw)
    draw_header(draw, fonts, package)
    if layout_mode == "choice_row":
        draw_choice_row_matrix(image, draw, fonts, package, asset_library)
    else:
        draw_column_combo_matrix(image, draw, fonts, package, asset_library)
    draw_footer(draw, fonts, settings)

    image.convert("RGB").save(final_path, "PNG", optimize=True)
    return TemplateRenderResult(str(final_path), asset_library.report, layout_mode)


def validate_template_package(package: InfographicPackage) -> None:
    """Fail early if the Sheet package cannot render into the approved matrix."""
    if len(package.columns) != 4:
        raise ValueError(f"Expected exactly 4 columns, found {len(package.columns)}.")
    if len(package.rows) != 5:
        raise ValueError(f"Expected exactly 5 rows, found {len(package.rows)}.")
    if len(package.matrix) != 5 or any(len(row) != 4 for row in package.matrix):
        raise ValueError("Expected a 4x5 ingredient matrix.")


def draw_background(draw: ImageDraw.ImageDraw) -> None:
    """Draw the soft blush background without a large outer border."""
    draw.rectangle((0, 0, CANVAS_SIZE[0], CANVAS_SIZE[1]), fill=PALE_BLUSH)
    draw.rounded_rectangle((34, 38, 1046, 1312), radius=34, fill=SOFT_CREAM)
    draw.rectangle((34, 38, 1046, 292), fill=SOFT_CREAM)


def draw_header(
    draw: ImageDraw.ImageDraw,
    fonts: TemplateFonts,
    package: InfographicPackage,
) -> None:
    """Draw the Canva-style hero heading and bookmark save prompt."""
    draw.text((72, 52), "BUILD YOUR", font=fonts.bold(54), fill=DEEP_GREEN)
    draw.text((70, 103), "BLOAT-FREE", font=fonts.bold(104), fill=SOFT_PINK)
    draw.text((74, 218), extract_subtitle(package), font=fonts.bold(42), fill=DEEP_GREEN)
    draw_bookmark_save_prompt(draw, fonts)


def draw_bookmark_save_prompt(draw: ImageDraw.ImageDraw, fonts: TemplateFonts) -> None:
    """Draw a yellow ribbon/bookmark-style save prompt in the top-right."""
    points = [(812, 58), (990, 58), (990, 160), (901, 132), (812, 160)]
    draw.polygon(points, fill=WARM_YELLOW)
    draw.line(points + [points[0]], fill=DEEP_GREEN, width=3, joint="curve")
    draw_centered_text(
        draw,
        "SAVE it",
        (826, 74, 976, 110),
        fonts.bold(24),
        SOFT_PINK,
        line_spacing=0,
    )
    draw_centered_text(
        draw,
        "FOR LATER",
        (826, 108, 976, 146),
        fonts.bold(23),
        DEEP_GREEN,
        line_spacing=0,
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


def draw_choice_row_matrix(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    fonts: TemplateFonts,
    package: InfographicPackage,
    asset_library: FoodAssetLibrary,
) -> None:
    """Draw the approved row-based choice matrix style."""
    left = 60
    top = 318
    label_width = 222
    option_width = 176
    option_gap = 18
    row_height = 164
    row_gap = 14

    for row_index, row_label in enumerate(package.rows):
        y0 = top + row_index * (row_height + row_gap)
        y1 = y0 + row_height
        row_fill = SOFT_CREAM if row_index % 2 == 0 else PALE_BLUSH
        draw.rounded_rectangle((left, y0, 1020, y1), radius=32, fill=row_fill)
        draw.line((label_width + 92, y0 + 22, label_width + 92, y1 - 22), fill=PALE_GREEN, width=3)

        label_box = (left + 10, y0 + 38, left + label_width - 8, y0 + 126)
        draw.rounded_rectangle(label_box, radius=30, fill=PALE_YELLOW)
        icon_box = (label_box[0] + 14, label_box[1] + 16, label_box[0] + 68, label_box[1] + 70)
        draw_category_icon(draw, icon_box, row_label)
        draw_wrapped_text(
            draw,
            format_row_label(row_label),
            (label_box[0] + 82, label_box[1] + 17, label_box[2] - 12, label_box[3] - 12),
            fonts.bold(23),
            DEEP_GREEN,
            max_chars=12,
            line_spacing=4,
        )

        for col_index, ingredient in enumerate(package.matrix[row_index]):
            x0 = left + label_width + 20 + col_index * (option_width + option_gap)
            x1 = x0 + option_width
            option_box = (x0, y0 + 10, x1, y1 - 8)
            draw_food_option(image, draw, fonts, option_box, ingredient, row_index, col_index, asset_library)


def draw_food_option(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    fonts: TemplateFonts,
    box: tuple[int, int, int, int],
    ingredient: str,
    row_index: int,
    col_index: int,
    asset_library: FoodAssetLibrary,
) -> None:
    """Draw one option as a large food image with real text underneath."""
    x0, y0, x1, y1 = box
    asset = asset_library.resolve(ingredient)
    if asset.path:
        paste_food_asset(image, asset.path, (x0, y0, x1, y1), max_size=(128, 92))
    else:
        draw_food_placeholder(draw, (x0, y0, x1, y1), row_index, col_index)

    draw_wrapped_text(
        draw,
        normalize_ingredient_text(ingredient),
        (x0 + 5, y0 + 98, x1 - 5, y1 - 2),
        fonts.bold(19),
        DEEP_GREEN,
        max_chars=14,
        line_spacing=3,
        center=True,
    )


def draw_column_combo_matrix(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    fonts: TemplateFonts,
    package: InfographicPackage,
    asset_library: FoodAssetLibrary,
) -> None:
    """Draw a lighter four-column combo layout for complete meal combinations."""
    left = 62
    top = 316
    label_width = 190
    cell_width = 182
    gap = 14
    header_height = 74
    row_height = 156

    for col_index, column in enumerate(package.columns):
        x0 = left + label_width + gap + col_index * (cell_width + gap)
        x1 = x0 + cell_width
        draw.rounded_rectangle((x0, top, x1, top + header_height), radius=28, fill=PALE_GREEN)
        draw_centered_text(draw, fit_text(column, 13), (x0 + 8, top + 8, x1 - 8, top + 66), fonts.bold(24), DEEP_GREEN)

    for row_index, row_label in enumerate(package.rows):
        y0 = top + header_height + gap + row_index * (row_height + gap)
        y1 = y0 + row_height
        draw.rounded_rectangle((left, y0, 1018, y1), radius=28, fill=SOFT_CREAM if row_index % 2 == 0 else PALE_BLUSH)
        draw_wrapped_text(draw, format_row_label(row_label), (left + 20, y0 + 40, left + label_width - 12, y1 - 18), fonts.bold(22), DEEP_GREEN, max_chars=12, line_spacing=4)
        for col_index, ingredient in enumerate(package.matrix[row_index]):
            x0 = left + label_width + gap + col_index * (cell_width + gap)
            x1 = x0 + cell_width
            draw_food_option(image, draw, fonts, (x0, y0 + 5, x1, y1 - 5), ingredient, row_index, col_index, asset_library)


def draw_category_icon(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    row_label: str,
) -> None:
    """Draw required pink circular category icons directly in code."""
    x0, y0, x1, y1 = box
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    draw.ellipse(box, fill=SOFT_PINK)
    kind = row_icon_kind(row_label)
    icon_fill = SOFT_CREAM

    if kind == "protein":
        draw.ellipse((cx - 17, cy - 10, cx + 17, cy + 10), fill=icon_fill)
        draw.ellipse((cx - 8, cy - 8, cx + 8, cy + 8), fill=WARM_YELLOW)
    elif kind == "carb":
        draw.arc((cx - 18, cy - 16, cx + 18, cy + 20), 200, 340, fill=icon_fill, width=5)
        draw.line((cx - 16, cy + 8, cx + 16, cy + 8), fill=icon_fill, width=5)
        draw.line((cx - 6, cy - 4, cx + 6, cy + 8), fill=icon_fill, width=4)
    elif kind == "leaf":
        draw.ellipse((cx - 22, cy - 12, cx + 4, cy + 18), fill=icon_fill)
        draw.ellipse((cx - 2, cy - 20, cx + 22, cy + 10), fill=icon_fill)
        draw.line((cx - 14, cy + 14, cx + 16, cy - 14), fill=SOFT_PINK, width=3)
    elif kind == "dip":
        draw.ellipse((cx - 20, cy + 2, cx + 20, cy + 20), fill=icon_fill)
        draw.arc((cx - 20, cy - 10, cx + 20, cy + 12), 0, 180, fill=icon_fill, width=5)
        draw.ellipse((cx - 8, cy - 2, cx + 8, cy + 8), fill=WARM_YELLOW)
    else:
        for offset in (-14, 0, 14):
            draw.ellipse((cx + offset - 7, cy - 8, cx + offset + 7, cy + 8), fill=icon_fill)
        draw.line((cx - 20, cy + 15, cx + 20, cy + 15), fill=icon_fill, width=4)


def row_icon_kind(row_label: str) -> str:
    """Map row labels to category icon types."""
    text = row_label.lower()
    if "protein" in text:
        return "protein"
    if "carb" in text:
        return "carb"
    if "fruit" in text or "veg" in text:
        return "leaf"
    if "dip" in text or "flavour" in text or "sauce" in text:
        return "dip"
    return "crunch"


def format_row_label(row_label: str) -> str:
    """Convert row labels into the approved title-case label style."""
    lower = row_label.lower().replace("choose your ", "")
    replacements = {
        "fruit or veg": "Fruit/Veg",
        "protein": "Protein",
        "carb": "Carb",
        "dip": "Dip",
        "crunch": "Crunch",
    }
    title = replacements.get(lower, lower.title())
    return f"Choose Your\n{title}:"


def paste_food_asset(
    image: Image.Image,
    asset_path: str,
    box: tuple[int, int, int, int],
    max_size: tuple[int, int],
) -> None:
    """Paste a transparent food asset with a soft brand-colour shadow."""
    x0, y0, x1, _ = box
    with Image.open(asset_path) as asset:
        asset = asset.convert("RGBA")
        asset.thumbnail(max_size, Image.Resampling.LANCZOS)
        x = x0 + ((x1 - x0) - asset.width) // 2
        y = y0 + 8 + ((84 - asset.height) // 2)
        shadow = Image.new("RGBA", asset.size, (29, 59, 42, 0))
        alpha = asset.getchannel("A").point(lambda value: min(70, value // 4))
        shadow.putalpha(alpha)
        image.alpha_composite(shadow, (x + 5, y + 7))
        image.alpha_composite(asset, (x, y))


def draw_food_placeholder(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    row_index: int,
    col_index: int,
) -> None:
    """Draw larger image-like placeholders until approved food assets exist."""
    x0, y0, x1, _ = box
    cx = (x0 + x1) // 2
    cy = y0 + 50
    palette = [WARM_YELLOW, SOFT_PINK, PALE_GREEN, PALE_YELLOW]
    fill = palette[(row_index + col_index) % len(palette)]
    draw.ellipse((cx - 58, cy - 34, cx + 58, cy + 34), fill=PALE_GREEN)
    draw.ellipse((cx - 50, cy - 40, cx + 50, cy + 40), fill=fill, outline=DEEP_GREEN, width=2)
    if row_index in (2, 4):
        for offset in (-28, 0, 28):
            draw.ellipse((cx + offset - 14, cy - 14, cx + offset + 14, cy + 14), fill=PALE_YELLOW, outline=DEEP_GREEN, width=2)


def draw_footer(
    draw: ImageDraw.ImageDraw,
    fonts: TemplateFonts,
    settings: Settings,
) -> None:
    """Draw the centered Instagram handle."""
    font = fonts.bold(31)
    text = settings.instagram_handle
    width = text_width(draw, text, font)
    draw.text(((CANVAS_SIZE[0] - width) // 2, 1262), text, font=font, fill=DEEP_GREEN)


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
