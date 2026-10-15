"""What the plugin does: pfdo_run over the directories ChRIS hands it.

A ChRIS DS plugin receives its input and output directories as positional arguments
and everything else as flags. ``ShExec`` is pfdo_run's engine with its options built
from those three things, and ``plugin_run`` is the body of the plugin's ``main``:
configure logging, run, report, and return an exit status.

Key components:
    - ShExec: pfdo_run's engine, built from the plugin's arguments
    - options_build: the plugin's arguments as ShExecOptions
    - threads_cap: ``--threads`` against the memory the process may use
    - plugin_run: run and report, returning the exit status

Typical usage:
    return plugin_run(options, inputdir, outputdir)

Dependencies:
    - pfdo_run, pftree.__main__ (logging), hostlib.facts, shexec.models
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hostlib.facts import memory_limit, memorySize_parse
from pfdo_run.pfdo_run import PfdoRun
from pftree.__main__ import logging_configure

from shexec.models import MemoryLimit, RunResult, ShExecOptions, ThreadsCap

EXIT_OK: int = 0
EXIT_FAILED: int = 1
EXIT_USAGE: int = 2


def options_build(options: argparse.Namespace, inputdir: Path, outputdir: Path) -> ShExecOptions:
    """The plugin's arguments as options.

    Args:
        options: the parsed flags.
        inputdir: the positional input directory.
        outputdir: the positional output directory.

    Returns:
        pfdo_run's options with the two directories set.

    Raises:
        ValueError: a flag's value cannot be coerced to its option's type.
    """
    values: dict[str, object] = dict(vars(options))
    values["inputDir"] = inputdir
    values["outputDir"] = outputdir
    return ShExecOptions.fromDict(values)


class ShExec(PfdoRun):
    """pfdo_run as a ChRIS plugin runs it.

    Example:
        >>> ShExec(ShExecOptions(inputDir=Path("."), outputDir=Path("/tmp/o"), exec="true")).argvTemplate
        ['true']
    """

    @classmethod
    def fromPlugin(cls, options: argparse.Namespace, inputdir: Path, outputdir: Path) -> ShExec:
        """The engine, built from what the plugin was given."""
        return cls(options_build(options, inputdir, outputdir))


def result_report(options: argparse.Namespace, result: RunResult) -> None:
    """Print what the flags asked for: the record as JSON, the elapsed time."""
    if options.json:
        print(json.dumps(result.toDict(), indent=4, sort_keys=True))
    if options.printElapsedTime:
        print(f"Elapsed time = {result.runTime:.6f} seconds")


def threads_cap(requested: int, jobBytes: int, limit: MemoryLimit | None) -> ThreadsCap:
    """How many jobs may run at once when each needs ``jobBytes`` and the process has ``limit``.

    No figure for a job, or no readable limit, leaves the request as it is. Otherwise
    the run holds at most ``limit // jobBytes`` jobs; one or none fitting is 0, the
    engine's sequential run, which is what one job at a time means.

    Example:
        >>> threads_cap(8, 16 * 2**30, MemoryLimit(50 * 2**30, "meminfo")).allowed
        3
        >>> threads_cap(4, 16 * 2**30, MemoryLimit(32 * 2**30, "cgroup")).allowed
        2
        >>> threads_cap(4, 16 * 2**30, MemoryLimit(20 * 2**30, "cgroup")).allowed
        0
    """
    if requested <= 1 or jobBytes <= 0 or limit is None:
        return ThreadsCap(requested=requested, allowed=requested, jobBytes=max(jobBytes, 0), limit=limit)
    fitting: int = limit.bytes // jobBytes
    allowed: int = requested if fitting >= requested else (fitting if fitting > 1 else 0)
    return ThreadsCap(requested=requested, allowed=allowed, jobBytes=jobBytes, limit=limit)


def plugin_run(
    options: argparse.Namespace, inputdir: Path, outputdir: Path, jobMemory: str = "", name: str = "shexec"
) -> int:
    """The body of the plugin's main.

    Args:
        options: the parsed flags; ``exec`` must be set.
        inputdir: the input tree.
        outputdir: the output tree.
        jobMemory: the most memory one job needs, as ``16Gi``; when given,
            ``--threads`` is capped so that the jobs held at once fit in the memory
            the process may use, and the cap is said on standard error.
        name: the command's name, which begins its messages on standard error.

    Returns:
        0 when at least one directory's jobs all succeeded (pftree's stage rule);
        1 when the run failed everywhere or could not start; 2 when ``--exec`` is
        empty or a flag's value is unusable.
    """
    if not options.exec:
        print(f"{name}: --exec is required; see {name} --man", file=sys.stderr)
        return EXIT_USAGE
    if jobMemory and getattr(options, "threads", 0) > 1:
        cap: ThreadsCap = threads_cap(options.threads, memorySize_parse(jobMemory), memory_limit())
        if cap.note():
            print(f"{name}: {cap.note()}", file=sys.stderr)
        options = argparse.Namespace(**{**vars(options), "threads": cap.allowed})
    try:
        engine: ShExec = ShExec.fromPlugin(options, inputdir, outputdir)
    except ValueError as err:
        print(f"{name}: {err}", file=sys.stderr)
        return EXIT_USAGE
    logging_configure(engine.options.verbosity)
    result: RunResult = engine.run()
    result_report(options, result)
    if result.error:
        print(result.error, file=sys.stderr)
    return EXIT_OK if result.status else EXIT_FAILED
