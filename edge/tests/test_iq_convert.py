"""tests that the c++ iq_convert matches the python loader (scrum-61).

skips unless the binary is built: cmake -S cpp -B cpp/build && cmake --build cpp/build
"""

import os
import subprocess
from pathlib import Path

import numpy as np
import pytest

from rfmon.iq import load_iq

EDGE_DIR = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("RFMON_IQ_CONVERT", EDGE_DIR / "cpp" / "build" / "iq_convert"))
SAMPLES_DIR = EDGE_DIR.parent / "data" / "samples"

pytestmark = pytest.mark.skipif(not BINARY.exists(), reason="iq_convert isn't built")


def run(*args):
    return subprocess.run([str(BINARY), *map(str, args)], capture_output=True, text=True, check=False)


def test_matches_python_loader(tmp_path):
    raw = np.random.default_rng(0).integers(0, 256, size=20_000, dtype=np.uint8)
    cu8, cf32 = tmp_path / "in.bin", tmp_path / "out.iq"
    raw.tofile(cu8)

    result = run(cu8, cf32)

    assert result.returncode == 0, result.stderr
    np.testing.assert_array_equal(load_iq(cf32), load_iq(cu8))


def test_known_bytes(tmp_path):
    cu8, cf32 = tmp_path / "in.bin", tmp_path / "out.iq"
    np.array([0, 255, 255, 0], dtype=np.uint8).tofile(cu8)
    assert run(cu8, cf32).returncode == 0
    np.testing.assert_array_equal(load_iq(cf32), np.array([-1 + 1j, 1 - 1j], dtype=np.complex64))


def test_odd_byte_count_fails(tmp_path):
    cu8 = tmp_path / "in.bin"
    cu8.write_bytes(b"\x01\x02\x03")
    result = run(cu8, tmp_path / "out.iq")
    assert result.returncode != 0
    assert "odd number of bytes" in result.stderr


def test_wrong_arguments_print_usage():
    result = run()
    assert result.returncode != 0
    assert "usage" in result.stderr


def test_reference_recording_matches(tmp_path):
    cu8 = SAMPLES_DIR / "modes1.bin"
    if not cu8.exists():
        pytest.skip("modes1.bin not downloaded; run scripts/fetch_samples.sh")
    cf32 = tmp_path / "modes1.iq"
    assert run(cu8, cf32).returncode == 0
    np.testing.assert_array_equal(load_iq(cf32), load_iq(cu8))