"""Reusable food asset lookup and generation for template-rendered infographics."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
import json
from pathlib import Path
import re

from PIL import Image

from src.config import Settings


@dataclass
class FoodAssetReport:
    """Track asset lookup outcomes for one render."""

    found: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    generated: list[str] = field(default_factory=list)

    def record_found(self, key: str) -> None:
        if key not in self.found:
            self.found.append(key)

    def record_missing(self, key: str) -> None:
        if key not in self.missing:
            self.missing.append(key)

    def record_generated(self, key: str) -> None:
        if key not in self.generated:
            self.generated.append(key)
        self.record_found(key)
        if key in self.missing:
            self.missing.remove(key)

    def to_dict(self) -> dict[str, list[str]]:
        """Return a JSON-friendly report."""
        return {
            "found": sorted(self.found),
            "missing": sorted(self.missing),
            "generated": sorted(self.generated),
        }


@dataclass(frozen=True)
class FoodAssetResult:
    """Resolved image asset for a matrix ingredient."""

    ingredient_label: str
    asset_key: str
    path: str | None
    generated: bool = False


class FoodAssetLibrary:
    """Resolve food labels to reusable local PNG assets."""

    def __init__(
        self,
        settings: Settings,
        generate_missing_assets: bool = False,
    ) -> None:
        self.settings = settings
        self.generate_missing_assets = generate_missing_assets
        self.asset_dir = Path(settings.food_asset_dir)
        self.map_file = Path(settings.food_asset_map_file)
        self.asset_map = load_asset_map(self.map_file)
        self.report = FoodAssetReport()

    def resolve(self, ingredient_label: str) -> FoodAssetResult:
        """Return an existing or optionally generated asset for an ingredient."""
        asset_key = self.asset_map.get(ingredient_label) or ingredient_to_asset_key(
            ingredient_label
        )
        asset_path = self.asset_dir / f"{asset_key}.png"

        if asset_path.exists():
            self.report.record_found(asset_key)
            return FoodAssetResult(ingredient_label, asset_key, str(asset_path))

        if not self.generate_missing_assets:
            self.report.record_missing(asset_key)
            return FoodAssetResult(ingredient_label, asset_key, None)

        generated_path = generate_food_asset(
            settings=self.settings,
            ingredient_label=ingredient_label,
            asset_key=asset_key,
            output_path=asset_path,
        )
        self.report.record_generated(asset_key)
        return FoodAssetResult(
            ingredient_label,
            asset_key,
            str(generated_path),
            generated=True,
        )


def load_asset_map(path: Path) -> dict[str, str]:
    """Load phrase-to-key mappings from JSON if available."""
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return {str(label): str(key) for label, key in data.items()}


def ingredient_to_asset_key(label: str) -> str:
    """Convert an ingredient label into a reusable snake_case asset key."""
    cleaned = label.lower()
    cleaned = re.sub(r";?\s*check label", "", cleaned)
    cleaned = re.sub(r"\b\d+([./]\d+)?\b", "", cleaned)
    cleaned = re.sub(
        r"\b(g|kg|ml|l|cup|cups|tbsp|tsp|serve|serves|small|cooked)\b",
        "",
        cleaned,
    )
    cleaned = cleaned.replace("lactose-free", "lactose free")
    cleaned = cleaned.replace("gluten-free", "gluten free")
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "food_asset"


def generate_food_asset(
    settings: Settings,
    ingredient_label: str,
    asset_key: str,
    output_path: Path,
) -> Path:
    """Generate one isolated food cutout with OpenAI and save a 512px PNG."""
    from openai import OpenAI

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prompt = build_food_asset_prompt(ingredient_label)
    client = OpenAI()

    try:
        result = client.images.generate(
            model=settings.food_asset_image_model,
            prompt=prompt,
            size="1024x1024",
            quality="medium",
            background="transparent",
        )
    except TypeError:
        result = client.images.generate(
            model=settings.food_asset_image_model,
            prompt=prompt,
            size="1024x1024",
            quality="medium",
        )

    image_data = result.data[0].b64_json
    if not image_data:
        raise RuntimeError(f"OpenAI did not return image data for {asset_key}.")

    raw_path = output_path.with_name(output_path.stem + "-raw.png")
    raw_path.write_bytes(base64.b64decode(image_data))
    normalise_asset_png(raw_path, output_path)
    raw_path.unlink(missing_ok=True)
    return output_path


def build_food_asset_prompt(ingredient_label: str) -> str:
    """Build a no-text prompt for a reusable food cutout asset."""
    return "\n".join(
        [
            f"Create a realistic isolated food cutout of: {ingredient_label}.",
            "Transparent background if possible.",
            "Square composition, centered subject, clean studio lighting.",
            "Appetising but simple, suitable for a nutrition infographic.",
            "No text, no labels, no packaging, no hands, no people, no utensils.",
            "Do not include multiple unrelated foods.",
        ]
    )


def normalise_asset_png(source_path: Path, output_path: Path) -> None:
    """Save a square transparent 512 x 512 PNG for consistent rendering."""
    with Image.open(source_path) as image:
        image = image.convert("RGBA")
        image.thumbnail((456, 456), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (512, 512), (255, 255, 255, 0))
        x = (512 - image.width) // 2
        y = (512 - image.height) // 2
        canvas.alpha_composite(image, (x, y))
        canvas.save(output_path, "PNG", optimize=True)
