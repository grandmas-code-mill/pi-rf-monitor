# signal processing for rfmon.

import numpy as np

# lowest power allowed before the log, so empty bins don't become -inf
_POWER_FLOOR = 1e-20


def _check_inputs(samples, sample_rate: float, fft_size: int) -> np.ndarray:
    """shared checks for spectrum() and spectrogram(); returns samples as an array."""
    samples = np.asarray(samples)
    if samples.ndim != 1:
        raise ValueError(f"expected a 1-D array of samples, got {samples.ndim}-D")
    if fft_size < 1:
        raise ValueError(f"fft_size must be at least 1, got {fft_size}")
    if sample_rate <= 0:
        raise ValueError(f"sample_rate must be positive, got {sample_rate}")
    if samples.size < fft_size:
        raise ValueError(f"need at least {fft_size} samples, got {samples.size}")
    return samples


def spectrum(
    samples: np.ndarray,
    sample_rate: float,
    center_freq: float = 0.0,
    fft_size: int = 2048,
) -> tuple[np.ndarray, np.ndarray]:
    """return (frequencies in hz, power in db) for the first fft_size samples."""
    samples = _check_inputs(samples, sample_rate, fft_size)

    # take one block and taper its edges
    window = np.hanning(fft_size)
    block = samples[:fft_size] * window

    # fft, with negative frequencies first
    bins = np.fft.fftshift(np.fft.fft(block))

    # power in db (a full-strength tone reads 0 db)
    power = np.abs(bins) ** 2 / np.sum(window) ** 2
    power_db = 10 * np.log10(np.maximum(power, _POWER_FLOOR))

    # frequency of each bin, shifted to the center frequency
    freqs = np.fft.fftshift(np.fft.fftfreq(fft_size, d=1 / sample_rate)) + center_freq

    return freqs, power_db


def spectrogram(
    samples: np.ndarray,
    sample_rate: float,
    center_freq: float = 0.0,
    fft_size: int = 2048,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """return (frequencies in hz, row start times in s, power in db).

    power has one row per block of fft_size samples, oldest first.
    each row is the same math as spectrum(), so every row covers the same
    frequencies; the rows step forward in time.
    leftover samples that don't fill a whole block are dropped.
    """
    samples = _check_inputs(samples, sample_rate, fft_size)

    # cut the samples into back-to-back blocks, one block per row
    n_blocks = samples.size // fft_size
    blocks = samples[: n_blocks * fft_size].reshape(n_blocks, fft_size)

    # taper every block, then fft each row (axis=1), negative frequencies first
    window = np.hanning(fft_size)
    bins = np.fft.fftshift(np.fft.fft(blocks * window, axis=1), axes=1)

    # power in db, same scaling as spectrum()
    power = np.abs(bins) ** 2 / np.sum(window) ** 2
    power_db = 10 * np.log10(np.maximum(power, _POWER_FLOOR))

    # frequency of each column and start time of each row
    freqs = np.fft.fftshift(np.fft.fftfreq(fft_size, d=1 / sample_rate)) + center_freq
    times = np.arange(n_blocks) * fft_size / sample_rate

    return freqs, times, power_db