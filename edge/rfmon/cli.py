# command-line interface for pi-rf-monitor

import argparse
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def get_version() -> str:
    # return the installed package version, set in pyproject.toml
    try:
        return version("pi-rf-monitor")
    except PackageNotFoundError:  # running from source without installing
        return "unknown"


def build_parser() -> argparse.ArgumentParser:
    # build the argument parser
    parser = argparse.ArgumentParser(
        prog="rfmon",
        description="Receive-only RF monitor for the Raspberry Pi: capture, "
        "visualize, and demodulate radio signals.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {get_version()}"
    )

    #  each feature adds a subcommand here, each one sets a handler with set_defaults(func=...).
    commands = parser.add_subparsers(dest="command", metavar="<command>")

    waterfall = commands.add_parser(
        "waterfall",
        help="save a waterfall (spectrogram) png from an iq recording",
        description="Save a waterfall (spectrogram) PNG from an IQ recording. "
        "Frequencies are in Hz; scientific notation works (250e3, 99.5e6).",
    )
    waterfall.add_argument("input", type=Path, help="recording (.cu8, .bin, .cf32, .iq, .npy)")
    waterfall.add_argument(
        "-r", "--sample-rate", type=float,
        help="samples per second, e.g. 2.048e6 (default: from the capture's .json)",
    )
    waterfall.add_argument(
        "-c", "--center-freq", type=float,
        help="tuned frequency in hz (default: from the capture's .json, else 0)",
    )
    waterfall.add_argument(
        "-n", "--fft-size", type=int, default=2048, help="samples per row (default 2048)"
    )
    waterfall.add_argument(
        "-f", "--format", choices=["cu8", "cf32", "npy"], help="override the file extension"
    )
    waterfall.add_argument(
        "-o", "--output", type=Path, help="png to write (default: input name with .png)"
    )
    waterfall.add_argument("-t", "--title", help="title on the image (default: file name)")
    waterfall.set_defaults(func=run_waterfall)

    capture = commands.add_parser(
        "capture",
        help="record live iq samples from the rtl-sdr",
        description="Record live IQ samples from the RTL-SDR to a .cu8 file, plus a .json "
        "file describing it. Frequencies are in Hz; scientific notation works (101.1e6).",
    )
    capture.add_argument(
        "-f", "--freq", type=float, required=True, help="center frequency in hz, e.g. 101.1e6"
    )
    capture.add_argument(
        "-r", "--sample-rate", type=float, default=2.048e6, help="samples per second (default 2.048e6)"
    )
    capture.add_argument(
        "-d", "--duration", type=float, default=5.0, help="seconds to record (default 5)"
    )
    capture.add_argument(
        "-g", "--gain", type=float, help="tuner gain in db, e.g. 20.7 (default: automatic)"
    )
    capture.add_argument(
        "-o", "--output", type=Path,
        help="file to write (default: data/captures/<freq>MHz_<utc time>.cu8)",
    )
    capture.set_defaults(func=run_capture)

    return parser


def run_waterfall(args: argparse.Namespace) -> int:
    # load a recording, build its spectrogram, and save it as a png.
    # imported here so `rfmon --version` doesn't load numpy and matplotlib
    from rfmon.capture import read_sidecar
    from rfmon.dsp import spectrogram
    from rfmon.iq import load_iq
    from rfmon.plot import save_waterfall

    # flags win; otherwise use the .json that rfmon capture wrote next to the file
    info = read_sidecar(args.input) or {}
    sample_rate = args.sample_rate or info.get("sample_rate")
    center_freq = args.center_freq if args.center_freq is not None else info.get("center_freq", 0.0)
    if sample_rate is None:
        print("rfmon waterfall: no --sample-rate given and no .json next to the file", file=sys.stderr)
        return 1

    output = args.output or args.input.with_suffix(".png")
    try:
        samples = load_iq(args.input, args.format)
        freqs, times, power_db = spectrogram(samples, sample_rate, center_freq, args.fft_size)
    except (OSError, ValueError) as err:
        # bad path or bad settings: one clear line instead of a traceback
        print(f"rfmon waterfall: {err}", file=sys.stderr)
        return 1

    save_waterfall(freqs, times, power_db, output, title=args.title or args.input.name)
    rows, cols = power_db.shape
    print(f"wrote {output} ({rows} rows x {cols} bins, {times[-1]:.2f} s)")
    return 0


def run_capture(args: argparse.Namespace) -> int:
    # record from the rtl-sdr and report where the file went.
    from rfmon.capture import capture, default_path

    output = args.output or default_path(args.freq)
    print(f"recording {args.duration:g} s at {args.freq / 1e6:.3f} MHz ...")
    try:
        info = capture(output, args.freq, args.sample_rate, args.duration, args.gain)
    except (ValueError, RuntimeError, OSError) as err:
        print(f"rfmon capture: {err}", file=sys.stderr)
        return 1

    print(f"wrote {output} ({info['n_samples']:,} samples, gain {info['gain']})")
    print(f"next: rfmon waterfall {output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """
    entry point for the `rfmon` command.
    argv defaults to the real command-line arguments; tests pass a list instead.
    returns an exit code; 0 for success, nonzero for failure.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())