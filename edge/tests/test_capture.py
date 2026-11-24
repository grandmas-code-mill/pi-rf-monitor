# tests for rfmon.capture and `rfmon capture`. a fake rtl_sdr stands in for the radio.

import json
import subprocess

import numpy as np
import pytest

from rfmon import capture as cap
from rfmon.cli import main


def fake_rtl_sdr(fill_bytes=None, returncode=0, stderr=""):
    """return a stand-in for subprocess.run that writes the file rtl_sdr would."""
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        n_samples = int(command[command.index("-n") + 1])
        size = 2 * n_samples if fill_bytes is None else fill_bytes
        # a gentle tone around the 127.5 midpoint, like a real cu8 capture
        data = (127.5 + 50 * np.sin(np.arange(size) / 3)).astype(np.uint8)
        with open(command[-1], "wb") as f:
            f.write(data.tobytes())
        return subprocess.CompletedProcess(command, returncode, "", stderr)

    run.calls = calls
    return run


def test_command_has_freq_rate_count_and_auto_gain(tmp_path):
    command = cap.rtl_sdr_command(tmp_path / "a.cu8", 101.1e6, 2.048e6, 1000, None)
    assert command == ["rtl_sdr", "-f", "101100000", "-s", "2048000", "-n", "1000", str(tmp_path / "a.cu8")]


def test_command_includes_gain_when_set(tmp_path):
    command = cap.rtl_sdr_command(tmp_path / "a.cu8", 101.1e6, 2.048e6, 1000, 20.7)
    assert command[-3:-1] == ["-g", "20.7"]


def test_capture_writes_file_and_sidecar(tmp_path):
    out = tmp_path / "sub" / "fm.cu8"  # folder doesn't exist yet
    run = fake_rtl_sdr()
    info = cap.capture(out, 101.1e6, 2.048e6, seconds=0.5, gain=20.7, run=run)
    assert out.stat().st_size == 2 * 1_024_000
    sidecar = json.loads((tmp_path / "sub" / "fm.json").read_text())
    assert sidecar == info
    assert sidecar["center_freq"] == 101.1e6 and sidecar["sample_rate"] == 2.048e6
    assert sidecar["gain"] == 20.7 and sidecar["n_samples"] == 1_024_000


def test_short_file_is_an_error(tmp_path):
    run = fake_rtl_sdr(fill_bytes=100, stderr="usb_claim_interface error -6")
    with pytest.raises(RuntimeError, match="100 of .* bytes.*usb_claim_interface"):
        cap.capture(tmp_path / "a.cu8", 101.1e6, seconds=0.1, run=run)
    assert not (tmp_path / "a.json").exists()


def test_nonzero_exit_is_an_error(tmp_path):
    with pytest.raises(RuntimeError, match="exit 1"):
        cap.capture(tmp_path / "a.cu8", 101.1e6, seconds=0.1, run=fake_rtl_sdr(returncode=1))


@pytest.mark.parametrize(
    "freq, rate, seconds",
    [(10e6, 2.048e6, 1), (2e9, 2.048e6, 1), (101.1e6, 500e3, 1), (101.1e6, 2.048e6, 0)],
)
def test_bad_settings_raise_before_recording(tmp_path, freq, rate, seconds):
    run = fake_rtl_sdr()
    with pytest.raises(ValueError):
        cap.capture(tmp_path / "a.cu8", freq, rate, seconds, run=run)
    assert run.calls == []  # never touched the radio


def test_default_path_names_the_frequency():
    path = cap.default_path(101.1e6)
    assert path.parent.as_posix() == "data/captures"
    assert path.name.startswith("101.100MHz_") and path.suffix == ".cu8"


def test_cli_capture_then_waterfall_uses_sidecar(tmp_path, monkeypatch, capsys):
    # hand the fake radio to capture() only; patching subprocess.run itself would also
    # catch other programs, like the fc-list call matplotlib makes on a fresh machine
    real_capture = cap.capture
    fake = fake_rtl_sdr()
    monkeypatch.setattr(cap, "capture", lambda *args, **kwargs: real_capture(*args, **kwargs, run=fake))
    out = tmp_path / "fm.cu8"
    assert main(["capture", "-f", "101.1e6", "-d", "0.1", "-o", str(out)]) == 0
    assert "rfmon waterfall" in capsys.readouterr().out

    # no -r or -c: both come from fm.json
    assert main(["waterfall", str(out)]) == 0
    assert (tmp_path / "fm.png").exists()


def test_cli_capture_without_rtl_sdr_fails_cleanly(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cap.shutil, "which", lambda name: None)
    assert main(["capture", "-f", "101.1e6", "-o", str(tmp_path / "a.cu8")]) == 1
    assert "install_rtlsdr.sh" in capsys.readouterr().err