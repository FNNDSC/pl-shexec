"""The records shexec works with: its options, and everything pfdo_run's records carry.

A program built on shexec imports every record from here, and reaches past it into
pfdo_run, pfdo, pftree, hostlib or pflog for nothing.

Key components:
    - ShExecOptions: pfdo_run's options, for the plugin
    - DirNode, FileJob, JobResult, JobSpec, HostFacts, RunResult, StageResult,
      ProcessResult, TreeOptions, PfdoOptions, PfdoRunOptions: re-exported
    - Span: pflog's record of the plugin's run, re-exported

Dependencies:
    - pfdo_run.models, pflog.models
"""

from __future__ import annotations

from dataclasses import dataclass

from pfdo_run.models import (
    DirNode,
    FileJob,
    HostFacts,
    JobResult,
    JobSpec,
    PfdoOptions,
    PfdoRunOptions,
    ProcessResult,
    RunResult,
    StageResult,
    TreeOptions,
)
from pflog.models import Span


@dataclass
class ShExecOptions(PfdoRunOptions):
    """What one run of the plugin is told.

    The same options as pfdo_run, built from the plugin's positional directories
    and its flags. The class exists so a plugin built on shexec has a place to add
    its own.

    Example:
        >>> ShExecOptions.fromDict({"inputDir": "/in", "outputDir": "/out", "exec": "ls"}).exec
        'ls'
    """


__all__: list[str] = [
    "DirNode",
    "FileJob",
    "HostFacts",
    "JobResult",
    "JobSpec",
    "PfdoOptions",
    "PfdoRunOptions",
    "ProcessResult",
    "RunResult",
    "ShExecOptions",
    "Span",
    "StageResult",
    "TreeOptions",
]
