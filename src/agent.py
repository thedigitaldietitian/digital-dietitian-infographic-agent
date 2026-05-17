"""Content generation logic for v1 of the infographic agent."""

from __future__ import annotations

from src.config import Settings
from src.models import ContentPackage


def build_content_package(
    settings: Settings,
    recent_rows: list[dict[str, str]] | None = None,
) -> ContentPackage:
    """Build one complete low FODMAP infographic content package.

    v1 is deterministic and conservative. The recent row input is included so the
    agent can avoid repeating a meal type as the project grows.
    """
    recent_rows = recent_rows or []
    post_id = next_post_id(recent_rows)

    columns = [
        "Savoury Crunch",
        "Sweet & Creamy",
        "Protein Picnic",
        "Tofu Crunch",
    ]
    rows = [
        "Choose your protein",
        "Choose your carb",
        "Choose your fruit or veg",
        "Choose your dip",
        "Choose your crunch",
    ]
    matrix = [
        [
            "Cheddar cheese, 40 g",
            "Lactose-free Greek yoghurt, 170 g",
            "Boiled eggs, 2",
            "Firm tofu, 100 g",
        ],
        [
            "Rice cakes, 2",
            "Plain oatcakes, 2; check label",
            "Gluten-free crackers, 1 serve; check label",
            "Rice crackers, 1 serve; check label",
        ],
        [
            "Cucumber sticks, 75 g",
            "Strawberries, 65 g",
            "Carrot sticks, 75 g",
            "Red pepper strips, 75 g",
        ],
        [
            "Lactose-free cream cheese with chives, 2 tbsp",
            "Peanut butter, 2 tbsp",
            "Garlic-free yoghurt herb dip, 2 tbsp",
            "Tamari-lime dip, 1 tbsp",
        ],
        [
            "Walnuts, 30 g",
            "Pumpkin seeds, 2 tbsp",
            "Green olives, 15 small",
            "Sesame seeds, 1 tbsp",
        ],
    ]

    draft_text = format_draft_text(columns, rows, matrix)
    caption = build_caption(columns, matrix)
    seo_keywords = (
        "low FODMAP snack ideas, IBS snack ideas, bloat friendly snacks, "
        "low FODMAP diet, IBS dietitian, gut health dietitian, low FODMAP UK, "
        "IBS food ideas, low FODMAP meal prep"
    )
    design_prompt = build_design_prompt(settings, columns, rows, matrix)
    qa_summary = build_qa_summary()

    return ContentPackage(
        post_id=post_id,
        week_commencing="2026-05-18",
        post_date="2026-05-20",
        post_time="11:00",
        platform="Instagram",
        format="Infographic",
        content_pillar="Low FODMAP meal ideas",
        topic="Build your bloat-free low FODMAP snack plate",
        objective="Saveable value / practical low FODMAP snack ideas",
        cta_offer="Save this for later and send it to someone who needs simple IBS-friendly food ideas.",
        risk_level="Low",
        draft_text=draft_text,
        caption=caption,
        seo_keywords=seo_keywords,
        design_prompt=design_prompt,
        image_asset_link="",
        source_notes=(
            "Created from SOP - Build Your Infographics. Portion guidance kept "
            "conservative and caption reminds readers to check Monash University "
            "FODMAP app or FODMAP Friendly app for latest serving guidance. "
            f"QA summary: {qa_summary}"
        ),
        clinical_qa="PASS - general education, cautious IBS/FODMAP wording, no symptom cure claims.",
        food_pairing_qa="PASS - 4 coherent snack plates with protein, carb, produce, dip and crunch.",
        brand_qa="PASS - British English, warm expert tone, approved CTA style.",
        visual_qa="NOT RUN - final image intentionally not generated in v1.",
        human_review_needed="Yes",
        ready_for_buffer="No",
        buffer_channel_id="",
        buffer_status="Not scheduled",
        buffer_post_id="",
    )


def next_post_id(recent_rows: list[dict[str, str]]) -> str:
    """Create the next INFO-style post ID from existing sheet rows."""
    numbers = []
    for row in recent_rows:
        post_id = row.get("Post ID", "")
        if post_id.startswith("INFO-"):
            try:
                numbers.append(int(post_id.rsplit("-", maxsplit=1)[1]))
            except ValueError:
                continue
    next_number = max(numbers, default=2) + 1
    return f"INFO-2026-{next_number:03d}"


def format_draft_text(
    columns: list[str],
    rows: list[str],
    matrix: list[list[str]],
) -> str:
    """Format the title, row labels and 4 x 5 matrix for the sheet."""
    lines = [
        "BUILD YOUR",
        "BLOAT-FREE",
        "LOW FODMAP SNACK PLATE",
        "SAVE IT FOR LATER",
        "",
        "Columns: " + " | ".join(columns),
        "Rows: " + " | ".join(rows),
        "",
        "Ingredient matrix:",
    ]
    for index, label in enumerate(rows):
        values = " | ".join(matrix[index])
        lines.append(f"{label}: {values}")
    return "\n".join(lines)


def build_caption(columns: list[str], matrix: list[list[str]]) -> str:
    """Build the Instagram caption for the content package."""
    combo_lines = []
    for column_index, column in enumerate(columns):
        ingredients = [row[column_index] for row in matrix]
        combo_lines.append(
            f"{column}: " + "; ".join(ingredients) + "."
        )

    return "\n\n".join(
        [
            "Save this if you want simple low FODMAP snack plate ideas.",
            (
                "Snack plates can be a practical option when you want something "
                "quick, filling and IBS-aware. These combinations use realistic "
                "low FODMAP portions and include protein, carbohydrate, colour, "
                "dip and crunch."
            ),
            "Try one of these combinations:\n" + "\n".join(combo_lines),
            (
                "A few helpful notes: check labels on oatcakes, gluten-free "
                "crackers and rice crackers for added onion, garlic, inulin, "
                "chicory root, honey, apple fibre or polyols. Low FODMAP guidance "
                "can change, and tolerance varies, so use the Monash University "
                "FODMAP app or FODMAP Friendly app for the latest portion guidance."
            ),
            (
                "Save this for later and send it to someone who needs simple "
                "IBS-friendly food ideas."
            ),
            (
                "Keywords: low FODMAP snack ideas, IBS snack ideas, bloat "
                "friendly snacks, low FODMAP diet, IBS dietitian, gut health "
                "dietitian, low FODMAP UK."
            ),
        ]
    )


def build_design_prompt(
    settings: Settings,
    columns: list[str],
    rows: list[str],
    matrix: list[list[str]],
) -> str:
    """Create the final image-generation prompt without generating the image."""
    matrix_lines = []
    for index, row_label in enumerate(rows):
        matrix_lines.append(f"{row_label}: " + " | ".join(matrix[index]))

    return "\n".join(
        [
            "Create a 1080 x 1350 px Instagram infographic in a clean editorial style.",
            f"Brand: {settings.brand_name}, handle {settings.instagram_handle}.",
            "Use Open Sans-style typography only.",
            "Use only these colours: #1d3b2a, #ff9cb7, #ffe78b, #fff8d9, #f9fff3, #e2efcc, #fff3f6.",
            "Do not add extra colours, leaves, random decorative elements, or clutter.",
            "Top text must include: BUILD YOUR, BLOAT-FREE, LOW FODMAP SNACK PLATE.",
            "Top-right save prompt must read: SAVE IT FOR LATER.",
            f"Footer must include: {settings.instagram_handle}.",
            "Main body must have exactly 4 meal columns and exactly 5 labelled rows.",
            "Column names: " + " | ".join(columns),
            "Rows and ingredients:",
            *matrix_lines,
            "Keep text readable on mobile, with generous spacing and no overlapping text.",
        ]
    )


def build_qa_summary() -> str:
    """Summarise the v1 quality gate result."""
    return (
        "Risk Low; exactly 4 columns; exactly 5 rows; ingredients use realistic "
        "low FODMAP portions; packaged items are label-check flagged; pairings "
        "are practical and texture-balanced; caption complete with save/send CTA; "
        "Buffer-ready No because final image has not been generated and visual QA "
        "has not run."
    )
