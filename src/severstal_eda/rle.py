"""Strict utilities for Severstal's one-indexed, column-major RLE masks."""

from __future__ import annotations

import numpy as np


def parse_rle(
    rle: str,
    *,
    height: int,
    width: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Validate RLE text and return zero-indexed starts plus lengths."""

    tokens = str(rle).split()
    if not tokens or len(tokens) % 2:
        raise ValueError("RLE must contain start/length pairs")
    try:
        values = np.asarray(tokens, dtype=np.int64)
    except ValueError as exc:
        raise ValueError("RLE tokens must be integers") from exc

    starts = values[0::2] - 1
    lengths = values[1::2]
    ends = starts + lengths
    pixel_count = int(height) * int(width)
    if height <= 0 or width <= 0:
        raise ValueError("Image dimensions must be positive")
    if np.any(starts < 0) or np.any(lengths <= 0) or np.any(ends > pixel_count):
        raise ValueError("RLE span is outside the image")
    if len(starts) > 1 and np.any(starts[1:] < ends[:-1]):
        raise ValueError("RLE runs overlap or are not ordered")
    return starts, lengths


def decode_rle(rle: str, *, height: int, width: int) -> np.ndarray:
    """Decode a validated RLE string using Fortran/column-major order."""

    starts, lengths = parse_rle(rle, height=height, width=width)
    flat = np.zeros(height * width, dtype=np.uint8)
    for start, length in zip(starts, lengths, strict=True):
        flat[start : start + length] = 1
    return flat.reshape((height, width), order="F")


def rle_area(rle: str, *, height: int, width: int) -> int:
    """Return encoded foreground area without allocating a full mask."""

    _, lengths = parse_rle(rle, height=height, width=width)
    return int(lengths.sum())

