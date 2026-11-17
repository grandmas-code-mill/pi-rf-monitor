"""tests for rfmon.dsp. generated tones have known answers, so no hardware is needed."""

from pathlib import Path

import numpy as np
import pytest

from rfmon.dsp import spectrum
from rfmon.iq import load_iq

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"


def tone(freq, sample_rate, n):
    """make a complex tone at freq hz."""
    t = np.arange(n) / sample_rate
    return np.exp(2j * np.pi * freq * t).astype(np.complex64)


def peak_freq(freqs, power_db):
    return freqs[np.argmax(power_db)]


def test_positive_tone_peaks_at_its_frequency():
    # 1 hz per bin
    freqs, power_db = spectrum(tone(100, 2048, 2048), sample_rate=2048)
    assert peak_freq(freqs, power_db) == 100


def test_negative_tone_peaks_below_center():
    # a mirrored spectrum would put this at +300
    freqs, power_db = spectrum(tone(-300, 2048, 2048), sample_rate=2048)
    assert peak_freq(freqs, power_db) == -300


def test_tone_at_real_sample_rate():
    fs, n = 250e3, 2048
    f = 40 * fs / n  # exactly on bin 40
    freqs, power_db = spectrum(tone(f, fs, n), sample_rate=fs, fft_size=n)
    assert peak_freq(freqs, power_db) == pytest.approx(f)


def test_center_frequency_shifts_the_axis():
    fs, n = 250e3, 2048
    f = 40 * fs / n
    freqs, power_db = spectrum(tone(f, fs, n), sample_rate=fs, center_freq=99.5e6, fft_size=n)
    assert peak_freq(freqs, power_db) == pytest.approx(99.5e6 + f)
    assert freqs[0] == pytest.approx(99.5e6 - fs / 2)


def test_full_scale_tone_peaks_at_zero_db():
    _, power_db = spectrum(tone(100, 2048, 2048), sample_rate=2048)
    assert power_db.max() == pytest.approx(0.0, abs=1e-3)


def test_output_shape_and_order():
    freqs, power_db = spectrum(tone(100, 2048, 4096), sample_rate=2048, fft_size=1024)
    assert freqs.shape == power_db.shape == (1024,)
    assert np.all(np.diff(freqs) > 0)


def test_too_few_samples_raises():
    with pytest.raises(ValueError, match="need at least 2048 samples"):
        spectrum(np.zeros(100, dtype=np.complex64), sample_rate=2048)


@pytest.mark.parametrize("kwargs", [{"fft_size": 0}, {"sample_rate": 0}])
def test_bad_settings_raise(kwargs):
    args = {"sample_rate": 2048, **kwargs}
    with pytest.raises(ValueError):
        spectrum(np.zeros(2048, dtype=np.complex64), **args)


def test_fm_recording_shows_station_near_center():
    path = SAMPLES_DIR / "fm_rds_250k_1Msamples.iq"
    if not path.exists():
        pytest.skip("FM recording not downloaded; run scripts/fetch_samples.sh")
    freqs, power_db = spectrum(load_iq(path), sample_rate=250e3, center_freq=99.5e6)
    assert 99.45e6 < peak_freq(freqs, power_db) < 99.55e6