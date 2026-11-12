"""load iq recordings as complex64 sample arrays scaled to about -1..+1."""

from pathlib import Path

import numpy as np

# raw iq files have no header, so the extension tells us the layout
FORMATS = {
    ".iq": "cf32",
    ".cf32": "cf32",
    ".bin": "cu8",
    ".cu8": "cu8",
    ".npy": "npy",
}

# midpoint of the rtl-sdr's 0..255 byte range (zero signal)
CU8_CENTER = 127.5


def cu8_to_complex(raw: np.ndarray) -> np.ndarray:
    """convert interleaved uint8 i/q bytes to complex64."""
    # an odd byte count means a cut-off sample
    if raw.size % 2 != 0:
        raise ValueError(f"cu8 data has an odd number of bytes ({raw.size}); expected I/Q pairs")

    # center on zero and scale to -1..+1, staying in float32
    scaled = (raw.astype(np.float32) - CU8_CENTER) / CU8_CENTER

    # read each i, q float pair as one complex number (no copy)
    return scaled.view(np.complex64)


def load_cu8(path: str | Path) -> np.ndarray:
    """load an rtl-sdr raw recording (uint8 i/q)."""
    return cu8_to_complex(np.fromfile(path, dtype=np.uint8))


def load_cf32(path: str | Path) -> np.ndarray:
    """load a float32 complex recording."""
    path = Path(path)
    size = path.stat().st_size
    item = np.dtype(np.complex64).itemsize  # 8 bytes per sample
    if size % item != 0:
        raise ValueError(f"{path.name} is {size} bytes, not a multiple of {item}; is it really cf32?")
    return np.fromfile(path, dtype=np.complex64)


def save_npy(path: str | Path, samples: np.ndarray) -> None:
    """save samples as .npy (keeps dtype and shape)."""
    np.save(path, np.asarray(samples, dtype=np.complex64))


def load_npy(path: str | Path) -> np.ndarray:
    """load samples saved with save_npy."""
    samples = np.load(path)
    if samples.dtype != np.complex64 or samples.ndim != 1:
        raise ValueError(f"expected a 1-D complex64 array, got {samples.ndim}-D {samples.dtype}")
    return samples


def load_iq(path: str | Path, fmt: str | None = None) -> np.ndarray:
    """load any supported recording; fmt is cu8, cf32, or npy (default: from extension)."""
    path = Path(path)
    if fmt is None:
        fmt = FORMATS.get(path.suffix.lower())
        if fmt is None:
            raise ValueError(
                f"can't tell the format of {path.name} from its extension; "
                f"pass fmt= one of: cu8, cf32, npy"
            )

    loaders = {"cu8": load_cu8, "cf32": load_cf32, "npy": load_npy}
    if fmt not in loaders:
        raise ValueError(f"unknown format {fmt!r}; expected one of: {', '.join(loaders)}")
    return loaders[fmt](path)