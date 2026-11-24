# record live iq samples from the rtl-sdr by running the rtl_sdr program.

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

# rates the rtl2832u can actually run at (anything between them drops samples)
RATE_RANGES = ((225_001, 300_000), (900_001, 3_200_000))
DEFAULT_RATE = 2_048_000


def check_settings(center_freq: float, sample_rate: float, seconds: float) -> None:
    # raise ValueError for settings the dongle can't handle.
    if not 24e6 <= center_freq <= 1.766e9:  # r820t tuner range
        raise ValueError(f"center_freq {center_freq:.0f} hz is outside the r820t's 24 mhz-1.766 ghz")
    if not any(low <= sample_rate <= high for low, high in RATE_RANGES):
        raise ValueError(
            f"sample_rate {sample_rate:.0f} is not supported; use 225001-300000 or 900001-3200000"
        )
    if seconds <= 0:
        raise ValueError(f"seconds must be positive, got {seconds}")


def rtl_sdr_command(
    path: Path, center_freq: float, sample_rate: float, n_samples: int, gain: float | None
) -> list[str]:
    # build the rtl_sdr command line. gain None means automatic gain."""
    command = ["rtl_sdr", "-f", str(int(center_freq)), "-s", str(int(sample_rate))]
    command += ["-n", str(n_samples)]
    if gain is not None:
        command += ["-g", str(gain)]
    command.append(str(path))
    return command


def default_path(center_freq: float, folder: Path = Path("data/captures")) -> Path:
    # name like data/captures/101.100MHz_20261124T183000Z.cu8
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return folder / f"{center_freq / 1e6:.3f}MHz_{stamp}.cu8"


def sidecar_path(path: Path) -> Path:
    # the json file that sits next to a capture and describes it.
    return Path(path).with_suffix(".json")


def capture(
    path: str | Path,
    center_freq: float,
    sample_rate: float = DEFAULT_RATE,
    seconds: float = 5.0,
    gain: float | None = None,
    run=None,
) -> dict:
    """
    record seconds of samples to path (.cu8) and write a json sidecar.

    returns the sidecar contents. `run` is swapped out in tests so no radio is needed.
    """
    check_settings(center_freq, sample_rate, seconds)
    if run is None:
        # the real radio: make sure the program is installed before trying
        if shutil.which("rtl_sdr") is None:
            raise RuntimeError("rtl_sdr not found; run scripts/install_rtlsdr.sh first")
        run = subprocess.run

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n_samples = int(sample_rate * seconds)
    started = datetime.now(UTC)

    # rtl_sdr prints its status to stderr; keep it to show if something goes wrong
    command = rtl_sdr_command(path, center_freq, sample_rate, n_samples, gain)
    result = run(command, capture_output=True, text=True, check=False)

    # each sample is 2 bytes (i and q), so a full capture has an exact size
    expected = 2 * n_samples
    got = path.stat().st_size if path.exists() else 0
    if result.returncode != 0 or got != expected:
        detail = (result.stderr or "").strip().splitlines()[-3:]
        raise RuntimeError(
            f"capture failed (exit {result.returncode}, {got} of {expected} bytes). "
            f"rtl_sdr said: {' | '.join(detail) or 'nothing'}"
        )

    info = {
        "format": "cu8",
        "center_freq": center_freq,
        "sample_rate": sample_rate,
        "gain": "auto" if gain is None else gain,
        "n_samples": n_samples,
        "seconds": n_samples / sample_rate,
        "started_utc": started.isoformat(timespec="seconds"),
        "tool": "rtl_sdr",
    }
    sidecar_path(path).write_text(json.dumps(info, indent=2) + "\n")
    return info


def read_sidecar(path: str | Path) -> dict | None:
    # load a capture's json sidecar, or None if it doesn't have one.
    sidecar = sidecar_path(path)
    if not sidecar.exists():
        return None
    return json.loads(sidecar.read_text())