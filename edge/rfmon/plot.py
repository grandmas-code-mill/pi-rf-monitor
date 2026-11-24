# turn dsp output into pictures.

from pathlib import Path

import numpy as np

# brightness range: anything quieter than this percentile is drawn as black,
# so the noise floor stays dark and signals stand out
_FLOOR_PERCENTILE = 5


def save_waterfall(
    freqs: np.ndarray,
    times: np.ndarray,
    power_db: np.ndarray,
    path: str | Path,
    title: str | None = None,
) -> Path:
    """save a spectrogram as a png: frequency in mhz across, time going up."""
    # imported here so `rfmon --help` stays fast and needs no display
    import matplotlib

    matplotlib.use("Agg")  # draw to a file, no window (the pi runs headless)
    import matplotlib.pyplot as plt

    path = Path(path)

    # the last row starts at times[-1] and lasts one block, so the image ends one step later
    step = times[1] - times[0] if times.size > 1 else 0.0
    extent = (freqs[0] / 1e6, freqs[-1] / 1e6, times[0], times[-1] + step)

    fig, ax = plt.subplots(figsize=(10, 6))
    image = ax.imshow(
        power_db,
        aspect="auto",  # stretch to fill the plot instead of square pixels
        origin="lower",  # row 0 (oldest) at the bottom
        extent=extent,
        cmap="viridis",
        vmin=np.percentile(power_db, _FLOOR_PERCENTILE),
        vmax=power_db.max(),
    )
    ax.set_xlabel("frequency (MHz)")
    ax.set_ylabel("time (s)")
    if title:
        ax.set_title(title)
    fig.colorbar(image, ax=ax, label="power (dB)")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)  # free the memory; matters when making many images
    return path