"""tests for the iq loaders (scrum-19, scrum-42).

the real-recording test skips unless scripts/fetch_samples.sh has been run.
"""

from pathlib import Path

import numpy as np
import pytest

from rfmon.iq import cu8_to_complex, load_iq, save_npy

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"


def test_cu8_known_bytes_convert_correctly():
    # 0, 255 are the extremes; 127, 128 sit just around the 127.5 midpoint
    raw = np.array([0, 255, 127, 128], dtype=np.uint8)
    samples = cu8_to_complex(raw)

    step = 0.5 / 127.5
    expected = np.array([-1 + 1j, -step + step * 1j], dtype=np.complex64)
    assert samples.dtype == np.complex64
    np.testing.assert_allclose(samples, expected, atol=1e-7)


def test_cu8_keeps_i_and_q_in_order():
    # swapped i/q would mirror the spectrum
    samples = cu8_to_complex(np.array([255, 0], dtype=np.uint8))
    assert samples[0].real > 0 and samples[0].imag < 0


def test_cu8_odd_byte_count_raises():
    with pytest.raises(ValueError, match="odd number of bytes"):
        cu8_to_complex(np.array([1, 2, 3], dtype=np.uint8))


def test_cu8_file_loads_by_extension(tmp_path):
    path = tmp_path / "capture.bin"
    np.array([0, 255, 255, 0], dtype=np.uint8).tofile(path)
    samples = load_iq(path)
    np.testing.assert_allclose(samples, [-1 + 1j, 1 - 1j], atol=1e-7)


def test_cf32_round_trips_without_changing_data(tmp_path):
    rng = np.random.default_rng(0)
    original = (rng.standard_normal(1000) + 1j * rng.standard_normal(1000)).astype(np.complex64)
    path = tmp_path / "capture.iq"
    original.tofile(path)
    np.testing.assert_array_equal(load_iq(path), original)


def test_cf32_wrong_size_raises(tmp_path):
    path = tmp_path / "truncated.iq"
    path.write_bytes(b"\x00" * 12)  # 1.5 samples
    with pytest.raises(ValueError, match="not a multiple of 8"):
        load_iq(path)


def test_npy_round_trips_without_changing_data(tmp_path):
    original = np.array([0.5 - 0.25j, -1 + 1j], dtype=np.complex64)
    path = tmp_path / "samples.npy"
    save_npy(path, original)
    loaded = load_iq(path)
    assert loaded.dtype == np.complex64
    np.testing.assert_array_equal(loaded, original)


def test_explicit_format_overrides_extension(tmp_path):
    path = tmp_path / "capture.dat"
    np.array([255, 0], dtype=np.uint8).tofile(path)
    assert load_iq(path, fmt="cu8").shape == (1,)


def test_unknown_extension_raises(tmp_path):
    path = tmp_path / "capture.xyz"
    path.write_bytes(b"\x00\x00")
    with pytest.raises(ValueError, match="can't tell the format"):
        load_iq(path)


@pytest.mark.parametrize(
    ("name", "expected_samples"),
    [("fm_rds_250k_1Msamples.iq", 1_000_000), ("modes1.bin", 356_868)],
)
def test_reference_recordings_load(name, expected_samples):
    path = SAMPLES_DIR / name
    if not path.exists():
        pytest.skip(f"{name} not downloaded; run scripts/fetch_samples.sh")
    samples = load_iq(path)
    assert samples.shape == (expected_samples,)
    assert samples.dtype == np.complex64
    assert np.all(np.abs(samples.real) <= 1.01) and np.all(np.abs(samples.imag) <= 1.01)