# command-line interface for pi-rf-monitor

import argparse
from importlib.metadata import PackageNotFoundError, version


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
    parser.add_subparsers(dest="command", metavar="<command>")

    return parser


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