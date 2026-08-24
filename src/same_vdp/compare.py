from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import math
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageChops


@dataclass(frozen=True)
class Comparison:
    width: int
    height: int
    differing_pixels: int
    total_pixels: int
    maximum_channel_delta: int
    mean_absolute_channel_delta: float
    root_mean_square_channel_delta: float
    bounding_box: tuple[int, int, int, int] | None

    @property
    def exact(self) -> bool:
        return self.differing_pixels == 0

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["exact"] = self.exact
        return result


def parse_crop(value: str | None) -> tuple[int, int, int, int] | None:
    if value is None:
        return None
    parts = [int(part.strip(), 0) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("crop must be x,y,width,height")
    x, y, width, height = parts
    if width <= 0 or height <= 0:
        raise ValueError("crop width and height must be positive")
    return x, y, x + width, y + height


def compare_images(
    expected_path: str | Path,
    actual_path: str | Path,
    *,
    crop: tuple[int, int, int, int] | None = None,
    diff_path: str | Path | None = None,
    result_path: str | Path | None = None,
) -> Comparison:
    expected = Image.open(expected_path).convert("RGB")
    actual = Image.open(actual_path).convert("RGB")
    if crop is not None:
        actual = actual.crop(crop)
    if expected.size != actual.size:
        raise ValueError(f"image dimensions differ: expected {expected.size}, actual {actual.size}")

    difference = ImageChops.difference(expected, actual)
    extrema = difference.getextrema()
    maximum = max(high for _low, high in extrema)
    raw = list(difference.getdata())
    differing = sum(1 for red, green, blue in raw if red or green or blue)
    channel_values = [component for pixel in raw for component in pixel]
    mean_absolute = sum(channel_values) / len(channel_values) if channel_values else 0.0
    rms = math.sqrt(sum(value * value for value in channel_values) / len(channel_values)) if channel_values else 0.0
    comparison = Comparison(
        width=expected.width,
        height=expected.height,
        differing_pixels=differing,
        total_pixels=expected.width * expected.height,
        maximum_channel_delta=maximum,
        mean_absolute_channel_delta=mean_absolute,
        root_mean_square_channel_delta=rms,
        bounding_box=difference.getbbox(),
    )
    if diff_path is not None:
        path = Path(diff_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Amplification keeps one-bit/channel errors visible without changing metrics.
        difference.point(lambda value: min(255, value * 4)).save(path)
    if result_path is not None:
        path = Path(result_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(comparison.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return comparison
