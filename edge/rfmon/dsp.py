# signal processing for rfmon.

import numpy as np

# lowest power allowed before the log, so empty bins don't become -inf
_POWER_FLOOR = 1e-20


def spectrum(
    samples: np.ndarray,
    sample_rate: float,
    center_freq: float = 0.0,
    fft_size: int = 2048,
) -> tuple[np.ndarray, np.ndarray]:
    """return (frequencies in hz, power in db) for the first fft_size samples."""
    samples = np.asarray(samples)
    if samples.ndim != 1:
        raise ValueError(f"expected a 1-D array of samples, got {samples.ndim}-D")
    if fft_size < 1:
        raise ValueError(f"fft_size must be at least 1, got {fft_size}")
    if sample_rate <= 0:
        raise ValueError(f"sample_rate must be positive, got {sample_rate}")
    if samples.size < fft_size:
        raise ValueError(f"need at least {fft_size} samples, got {samples.size}")

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