"""The plugin over a tree: records, tags, failure, exit status, the span."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shexec.__main__ import main, parser
from shexec.models import ShExecOptions
from shexec.shexec import ShExec, options_build, plugin_run


def tree_make(root: Path) -> tuple[Path, Path]:
    inputDir: Path = root / "incoming"
    outputDir: Path = root / "outgoing"
    (inputDir / "a").mkdir(parents=True)
    (inputDir / "b").mkdir(parents=True)
    (inputDir / "a" / "one.txt").write_text("1\n2\n")
    (inputDir / "a" / "skip.md").write_text("x\n")
    (inputDir / "b" / "two.txt").write_text("1\n")
    outputDir.mkdir()
    return inputDir, outputDir


def test_run_everyTxt_withRecords(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    template: str = "wc -l %{inputWorkingDir}/%{inputWorkingFile}"
    options = parser.parse_args(["--fileFilter", "txt", "--exec", template])
    assert main(options, inputDir, outputDir) == 0
    jobA = json.loads((outputDir / "a" / "jobs.jsonl").read_text())
    assert jobA["stdout"].startswith("2 ") and jobA["returncode"] == 0
    assert json.loads((outputDir / "b" / "jobs.jsonl").read_text())["returncode"] == 0
    assert not (outputDir / "a" / "one.txt-cmd").exists()
    assert "skip.md" not in jobA["argv"][-1]
    span = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert span["name"] == "shexec" and span["status"] is True and span["returncode"] == 0


def test_tagsResolve_toOutputTree(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    template: str = (
        "cp %{inputWorkingDir}/%{inputWorkingFile} %{outputWorkingDir}/%{inputWorkingFile|rmext}.copy"
    )
    options = parser.parse_args(["--fileFilter", "txt", "--exec", template])
    assert plugin_run(options, inputDir, outputDir) == 0
    assert (outputDir / "a" / "one.copy").read_text() == "1\n2\n"


def test_failingCommand_exits1_andSpanFails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    options = parser.parse_args(["--fileFilter", "txt", "--exec", "false %{inputWorkingFile}"])
    assert main(options, inputDir, outputDir) == 1
    assert json.loads((outputDir / "a" / "jobs.jsonl").read_text())["returncode"] == 1
    span = json.loads(capsys.readouterr().err.strip().splitlines()[-1])
    assert span["status"] is False and span["returncode"] == 1


def test_missingExec_exits2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    assert main(parser.parse_args([]), inputDir, outputDir) == 2
    assert "--exec is required" in capsys.readouterr().err


def test_json_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    options = parser.parse_args(["--fileFilter", "txt", "--json", "--noJobLogging", "--exec", "true"])
    assert plugin_run(options, inputDir, outputDir) == 0
    out: str = capsys.readouterr().out
    record = json.loads(out)
    assert record["status"] is True and any(key.endswith("/a") for key in record["tree"])
    assert not (outputDir / "a" / "jobs.jsonl").exists()


def test_jobFiles_writesTheFourFilesToo(tmp_path: Path) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    options = parser.parse_args(["--fileFilter", "txt", "--jobFiles", "--exec", "wc -l %{inputWorkingDir}/%{inputWorkingFile}"])
    assert plugin_run(options, inputDir, outputDir) == 0
    assert (outputDir / "a" / "one.txt-returncode").read_text() == "0\n"
    assert (outputDir / "a" / "jobs.jsonl").exists()


def test_options_build_setsDirectories(tmp_path: Path) -> None:
    options = parser.parse_args(["--exec", "true", "--threads", "2"])
    built: ShExecOptions = options_build(options, tmp_path / "in", tmp_path / "out")
    assert built.inputDir == tmp_path / "in" and built.outputDir == tmp_path / "out"
    assert built.exec == "true" and built.threads == 2
    assert ShExec.fromPlugin(options, tmp_path / "in", tmp_path / "out").argvTemplate == ["true"]


def test_badFlagValue_exits2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    inputDir, outputDir = tree_make(tmp_path)
    options = parser.parse_args(["--exec", "true", "--analyzeFileIndex", "notAnIndex"])
    assert plugin_run(options, inputDir, outputDir) == 2
    assert "shexec:" in capsys.readouterr().err
