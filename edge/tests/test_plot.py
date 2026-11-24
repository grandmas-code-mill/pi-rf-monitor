# tests for rfmon.plot and the `rfmon waterfall` command.

from pathlib import Path

import numpy as np
import pytest

from rfmon.cli import main
from rfmon.dsp import spectrogram
from rfmon.iq import save_npy
from rfmon.plot import save_waterfall

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"  # first 8 bytes of every png file
SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"


def tone(freq, sample_rate, n):
    t = np.arange(n) / sample_rate
    return np.exp(2j * np.pi * freq * t).astype(np.complex64)


def is_png(path):
    return path.exists() and path.read_bytes()[:8] == PNG_SIGNATURE


def test_save_waterfall_writes_a_png(tmp_path):
    freqs, times, power_db = spectrogram(tone(100, 2048, 2048 * 8), sample_rate=2048)
    out = save_waterfall(freqs, times, power_db, tmp_path / "w.png", title="test")
    assert is_png(out)


def test_cli_writes_png_next_to_recording(tmp_path, capsys):
    rec = tmp_path / "tone.cf32"
    tone(100, 2048, 2048 * 8).tofile(rec)
    assert main(["waterfall", str(rec), "--sample-rate", "2048"]) == 0
    assert is_png(tmp_path / "tone.png")
    assert "8 rows x 2048 bins" in capsys.readouterr().out


def test_cli_output_and_format_flags(tmp_path):
    # np.save always adds .npy, so save first, then rename to an extension the loader doesn't know
    save_npy(tmp_path / "samples.npy", tone(-300, 2048, 2048 * 4))
    rec = (tmp_path / "samples.npy").rename(tmp_path / "samples.dat")
    out = tmp_path / "custom.png"
    code = main(["waterfall", str(rec), "-r", "2048", "-f", "npy", "-o", str(out), "-n", "512"])
    assert code == 0
    assert is_png(out)


def test_cli_missing_file_fails_cleanly(tmp_path, capsys):
    assert main(["waterfall", str(tmp_path / "nope.cu8"), "-r", "2.048e6"]) == 1
    assert "rfmon waterfall:" in capsys.readouterr().err


def test_cli_too_short_recording_fails_cleanly(tmp_path, capsys):
    rec = tmp_path / "short.cf32"
    tone(100, 2048, 100).tofile(rec)
    assert main(["waterfall", str(rec), "-r", "2048"]) == 1
    assert "need at least 2048 samples" in capsys.readouterr().err


def test_cli_needs_sample_rate_or_sidecar(tmp_path, capsys):
    rec = tmp_path / "x.cf32"
    tone(100, 2048, 2048 * 2).tofile(rec)
    assert main(["waterfall", str(rec)]) == 1
    assert "no --sample-rate" in capsys.readouterr().err


def test_cli_on_fm_recording(tmp_path):
    rec = SAMPLES_DIR / "fm_rds_250k_1Msamples.iq"
    if not rec.exists():
        pytest.skip("FM recording not downloaded; run scripts/fetch_samples.sh")
    out = tmp_path / "fm.png"
    assert main(["waterfall", str(rec), "-r", "250e3", "-c", "99.5e6", "-o", str(out)]) == 0
    assert is_png(out)