# tests for the rfmon command-line interface

import pytest

from rfmon.cli import get_version, main


def test_version_flag_prints_package_version(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"rfmon {get_version()}"


def test_no_command_prints_help_and_succeeds(capsys):
    assert main([]) == 0
    assert "usage: rfmon" in capsys.readouterr().out


def test_unknown_command_fails(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["not-a-command"])
    assert exit_info.value.code != 0