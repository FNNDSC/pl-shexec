"""The command line: manual, version, parser shape, and the ChRIS plugin description."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from chris_plugin.parameters import serialize
from hostlib import JobSpec, job_run

from shexec import __version__
from shexec.__main__ import main, manual_build, parser, synopsis


def test_manual_andSynopsis(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(parser.parse_args(["--man"]), tmp_path, tmp_path) == 0
    out: str = capsys.readouterr().out
    body: str = out.split("DESCRIPTION", 1)[1]
    assert "`" not in body and "TAGS" in body and "<inputDir>" in body and "shexec" in body
    assert main(parser.parse_args(["--synopsis"]), tmp_path, tmp_path) == 0
    assert "TAGS" not in capsys.readouterr().out


def test_manual_build_namesShexec() -> None:
    manual = manual_build()
    assert manual.command == "shexec" and __version__ in manual.text_render()
    assert "--inputDir" not in synopsis(shortOnly=True)


def test_version_isShexecs(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        parser.parse_args(["--version"])
    assert capsys.readouterr().out.strip() == f"shexec {__version__}"


def test_parser_hasNoPositionals_andSerialises() -> None:
    assert all(action.option_strings for action in parser._actions)
    names: set[str] = {spec["name"] for spec in serialize(parser)}
    assert {"exec", "fileFilter", "threads", "noJobLogging", "analyzeFileIndex"} <= names


def test_chris_plugin_info_describesThePlugin() -> None:
    binDir: Path = Path(sys.executable).parent
    spec = JobSpec(
        argv=[
            str(binDir / "chris_plugin_info"),
            "--dock-image",
            "docker.io/fnndsc/pl-shexec:2.0.3",
            "shexec",
        ],
        env={"PATH": f"{binDir}{os.pathsep}{os.environ.get('PATH', '')}"},
    )
    result = job_run(spec)
    assert result.status, [*result.errors, result.stderr]
    description = json.loads(result.stdout)
    assert description["type"] == "ds" and description["selfexec"] == "shexec"
    assert description["version"] == __version__
    assert description["documentation"] == "https://github.com/FNNDSC/pl-shexec"
    assert description["authors"] == "FNNDSC <dev@babyMRI.org>"
    assert any(p["name"] == "exec" for p in description["parameters"])
