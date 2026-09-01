import numpy as np
import pytest

from severstal_eda.rle import decode_rle, rle_area


def test_decode_uses_severstal_column_major_order():
    mask = decode_rle("1 2 5 2", height=2, width=4)

    np.testing.assert_array_equal(
        mask,
        np.array([[1, 0, 1, 0], [1, 0, 1, 0]], dtype=np.uint8),
    )


@pytest.mark.parametrize("rle", ["", "1", "0 2", "8 2", "1 -2", "a b"])
def test_decode_rejects_malformed_or_out_of_bounds_runs(rle: str):
    with pytest.raises(ValueError):
        decode_rle(rle, height=2, width=4)


def test_rle_area_sums_run_lengths_without_decoding():
    assert rle_area("1 2 5 2", height=2, width=4) == 4


def test_overlapping_runs_are_rejected():
    with pytest.raises(ValueError, match="overlap"):
        decode_rle("1 3 3 2", height=2, width=4)
