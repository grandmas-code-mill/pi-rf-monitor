# tests for rfmon.dsp. generated tones have known answers, so no hardware is needed.

from pathlib import Path

import numpy as np
import pytest

from rfmon.dsp import spectrogram, spectrum
from rfmon.iq import load_iq

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "samples"


def tone(freq, sample_rate, n):
    # make a complex tone at freq hz.
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


# spectrogram: many spectrums in a row, one per block of time


def test_spectrogram_shape_and_times():
    # 5000 samples / 1024 per block = 4 full rows, 904 leftovers dropped
    freqs, times, power_db = spectrogram(tone(100, 2048, 5000), sample_rate=2048, fft_size=1024)
    assert power_db.shape == (4, 1024)
    assert freqs.shape == (1024,)
    assert times == pytest.approx([0.0, 0.5, 1.0, 1.5])  # 1024 samples at 2048/s = 0.5 s


def test_spectrogram_first_row_matches_spectrum():
    samples = tone(100, 2048, 8192)
    freqs, _, power_db = spectrogram(samples, sample_rate=2048, center_freq=1e6)
    s_freqs, s_power = spectrum(samples, sample_rate=2048, center_freq=1e6)
    np.testing.assert_allclose(freqs, s_freqs)
    np.testing.assert_allclose(power_db[0], s_power, atol=1e-6)


def test_steady_tone_peaks_in_the_same_column_every_row():
    freqs, _, power_db = spectrogram(tone(100, 2048, 2048 * 6), sample_rate=2048)
    assert np.all(freqs[np.argmax(power_db, axis=1)] == 100)


def test_tone_that_changes_frequency_moves_between_rows():
    # first half at +200 hz, second half at -400 hz
    samples = np.concatenate([tone(200, 2048, 2048 * 3), tone(-400, 2048, 2048 * 3)])
    freqs, _, power_db = spectrogram(samples, sample_rate=2048)
    peaks = freqs[np.argmax(power_db, axis=1)]
    assert list(peaks) == [200, 200, 200, -400, -400, -400]


def test_spectrogram_too_few_samples_raises():
    with pytest.raises(ValueError, match="need at least 2048 samples"):
        spectrogram(np.zeros(100, dtype=np.complex64), sample_rate=2048)


def test_fm_recording_spectrogram_keeps_station_near_center():
    path = SAMPLES_DIR / "fm_rds_250k_1Msamples.iq"
    if not path.exists():
        pytest.skip("FM recording not downloaded; run scripts/fetch_samples.sh")
    freqs, times, power_db = spectrogram(load_iq(path), sample_rate=250e3, center_freq=99.5e6)
    assert power_db.shape[0] == 1_000_000 // 2048
    assert times[-1] == pytest.approx((power_db.shape[0] - 1) * 2048 / 250e3)
    peaks = freqs[np.argmax(power_db, axis=1)]
    # the station should be the strongest thing in most rows
    assert np.mean((peaks > 99.45e6) & (peaks < 99.55e6)) > 0.9