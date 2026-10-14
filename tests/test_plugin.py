"""plugin_build: a plugin built on shexec with its own name, defaults and words, and no engine code."""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path

import pytest
from chris_plugin.parameters import serialize

from shexec import Plugin, PluginSpec, plugin_build
from shexec.plugin import PLUGIN_SIGNATURE

COUNT_LINES: str = "wc -l %{inputWorkingDir}/%{inputWorkingFile}"


def tree_make(root: Path) -> tuple[Path, Path]:
    inputDir: Path = root / "incoming"
    outputDir: Path = root / "outgoing"
    (inputDir / "sub-01").mkdir(parents=True)
    (inputDir / "sub-01" / "t1.nii.gz").write_text("1\n2\n3\n")
    (inputDir / "sub-01" / "notes.txt").write_text("x\n")
    outputDir.mkdir()
    return inputDir, outputDir


def spec_make(**extra: object) -> PluginSpec:
    values: dict[str, object] = {
        "name": "linecount",
        "version": "9.9.9",
        "title": "Count lines",
        "minMemory": "8Gi",
        "defaults": {"exec": COUNT_LINES, "analyzeFileIndex": "f", "fileFilter": "glob:*.nii.gz"},
        "bannerTitle": "Count the lines of every first file",
        "bannerText": "Count lines, version {version}.",
        "briefExample": "\n        linecount /incoming /outgoing\n",
        "description": "\n    DESCRIPTION\n\n        Counts lines.\n",
        "examples": "\n    EXAMPLES\n\n        linecount /incoming /outgoing\n",
    }
    values.update(extra)
    return PluginSpec(**values)  # type: ignore[arg-type]  # the test builds the spec from a loose mapping


def test_derivedPlugin_runsWithItsDefaults_noExecGiven(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    plugin: Plugin = plugin_build(spec_make(), singleton=False)
    options: argparse.Namespace = plugin.parser.parse_args(["--verbosity", "0"])
    assert options.exec == COUNT_LINES and options.analyzeFileIndex == "f"
    assert plugin.main(options, inputDir, outputDir) == 0
    record = json.loads((outputDir / "sub-01" / "jobs.jsonl").read_text())
    assert record["argv"][:2] == ["wc", "-l"] and record["argv"][-1].endswith("t1.nii.gz")
    assert "notes.txt" not in record["argv"][-1]
    span = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert span["name"] == "linecount" and span["status"] is True


def test_derivedPlugin_flagsOverrideDefaults(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    plugin: Plugin = plugin_build(spec_make(), singleton=False)
    options = plugin.parser.parse_args(["--verbosity", "0", "--fileFilter", "txt", "--analyzeFileIndex", "a"])
    assert plugin.main(options, inputDir, outputDir) == 0
    assert "notes.txt" in json.loads((outputDir / "sub-01" / "jobs.jsonl").read_text())["argv"][-1]


def test_derivedPlugin_describesItself_forChris() -> None:
    plugin: Plugin = plugin_build(spec_make(), singleton=False)
    byName = {spec["name"]: spec for spec in serialize(plugin.parser)}
    assert byName["exec"]["default"] == COUNT_LINES and byName["analyzeFileIndex"]["default"] == "f"
    assert inspect.signature(plugin.main) == PLUGIN_SIGNATURE
    assert plugin.main.__name__ == "linecount"


def test_derivedPlugin_manualAndVersion_areItsOwn(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    plugin: Plugin = plugin_build(spec_make(), singleton=False)
    assert plugin.main(plugin.parser.parse_args(["--man"]), tmp_path, tmp_path) == 0
    out: str = capsys.readouterr().out
    assert "linecount" in out and "Counts lines." in out and "9.9.9" in out and "TAGS" in out
    with pytest.raises(SystemExit):
        plugin.parser.parse_args(["--version"])
    assert capsys.readouterr().out.strip() == "linecount 9.9.9"


def test_shexecItself_isBuiltByTheFactory() -> None:
    from shexec.__main__ import PLUGIN, SPEC

    assert (
        SPEC.name == "shexec" and PLUGIN.parser.get_default("exec") == "" and PLUGIN.main.__name__ == "shexec"
    )
