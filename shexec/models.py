"""The records shexec works with: its options, and everything pfdo_run's records carry.

A program built on shexec imports every record from here, and reaches past it into
pfdo_run, pfdo, pftree, hostlib or pflog for nothing.

Key components:
    - ShExecOptions: pfdo_run's options, for the plugin
    - PluginSpec: what a plugin built on shexec says about itself
    - Plugin: what ``plugin_build`` returns
    - ThreadsCap: how many jobs a run may hold at once, given the memory it has
    - DirNode, FileJob, JobResult, JobSpec, HostFacts, RunResult, StageResult,
      ProcessResult, TreeOptions, PfdoOptions, PfdoRunOptions: re-exported
    - Span: pflog's record of the plugin's run, re-exported
    - MemoryLimit: hostlib's figure for the memory the process may use, re-exported

Dependencies:
    - pfdo_run.models, pflog.models, hostlib.models
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from hostlib.models import MemoryLimit
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


DEFAULT_BANNER_ART: str = r"""
       _            _
      | |          | |
 _ __ | |______ ___| |__   _____  _____  ___
| '_ \| |______/ __| '_ \ / _ \ \/ / _ \/ __|
| |_) | |      \__ \ | | |  __/>  <  __/ (__
| .__/|_|      |___/_| |_|\___/_/\_\___|\___|
| |
|_|
"""


@dataclass
class PluginSpec:
    """What a plugin built on shexec says about itself.

    Everything a downstream plugin changes from shexec is here; the engine, the
    parser's flags, the records and the exit status are not, because they are the
    same for every plugin on the stack.

    Attributes:
        name: the command and the span, ``shexec``, ``freesurfer``.
        version: the plugin's version, for ``--version`` and the description.
        title: the plugin's title in ChRIS.
        category: the plugin's category in ChRIS.
        minMemory: the memory ChRIS reserves, as ``2Gi``.
        minCpu: the CPU ChRIS reserves, in millicores, as ``1000m``.
        minGpu: GPUs required; 0 for none.
        defaults: flag defaults, ``exec`` above all; a derived plugin's usual command.
        omit: engine flags this plugin does not offer, by destination name, as
            ``("threads", "threadsSplit")``. Each is removed from the parser, so
            neither ChRIS's description nor the manual shows it, and its value is
            pinned to the engine's default, or to ``defaults`` when that names it.
        chrisHidden: engine flags offered on the command line and in the manual
            but left out of the description ChRIS reads, by destination name. ChRIS
            passes only the parameters its description lists, so in ChRIS each
            keeps its default; run from a shell, the flag works.
        jobMemory: the most memory one job needs, as ``16Gi``; empty for no figure.
            When set, ``--threads`` is capped at the memory the process may use
            divided by it, so that the jobs held at once fit.
        bannerArt: the ASCII art on the manual's first page.
        bannerTitle: the one-line title under it.
        bannerText: the banner prose; ``{version}`` in it is replaced.
        briefExample: the manual's BRIEF EXAMPLE, an indented command.
        description: the manual's DESCRIPTION section, heading included.
        examples: the manual's EXAMPLES section, heading included.

    Example:
        >>> PluginSpec(name="freesurfer", version="1.0.0", defaults={"exec": "recon-all"}).defaults["exec"]
        'recon-all'
    """

    name: str
    version: str
    title: str = ""
    category: str = "Utility"
    minMemory: str = "2Gi"
    minCpu: str = "1000m"
    minGpu: int = 0
    defaults: dict[str, Any] = field(default_factory=dict)
    omit: tuple[str, ...] = ()
    chrisHidden: tuple[str, ...] = ()
    jobMemory: str = ""
    bannerArt: str = DEFAULT_BANNER_ART
    bannerTitle: str = ""
    bannerText: str = ""
    briefExample: str = ""
    description: str = ""
    examples: str = ""


@dataclass
class Plugin:
    """What ``plugin_build`` returns: a plugin ready to be a console script.

    Attributes:
        name: the plugin's name.
        spec: what it was built from.
        parser: its flags, defaults applied: what the command line parses.
        chrisParser: the parser ChRIS's description is made from, ``parser``
            without the spec's ``chrisHidden`` flags.
        main: the decorated main, the console script's target.
        manual: its manual page.

    Example:
        >>> Plugin.__dataclass_fields__["main"].name
        'main'
    """

    name: str
    spec: PluginSpec
    parser: argparse.ArgumentParser
    chrisParser: argparse.ArgumentParser
    main: Callable[..., int]
    manual: Any


@dataclass
class ThreadsCap:
    """How many jobs a run may hold at once, and why.

    Attributes:
        requested: the ``--threads`` asked for; 0 is sequential.
        allowed: what the run will use: ``requested``, or fewer when memory caps it.
        jobBytes: the memory one job needs, in bytes; 0 when no figure was given.
        limit: the memory the process may use, or ``None`` when it cannot be read.

    Example:
        >>> ThreadsCap(8, 3, 16 * 2**30, MemoryLimit(50 * 2**30, "cgroup")).capped()
        True
    """

    requested: int
    allowed: int
    jobBytes: int
    limit: MemoryLimit | None

    def capped(self) -> bool:
        """Whether memory lowered the request."""
        return self.allowed < self.requested

    def note(self) -> str:
        """One line for standard error saying what was decided; empty when nothing needs saying."""
        if self.requested <= 1 or self.jobBytes == 0:
            return ""
        jobGib: float = self.jobBytes / 2**30
        if self.limit is None:
            return f"--threads {self.requested}: memory limit unknown, not capped ({jobGib:g} GiB per job)"
        have: str = f"{self.limit.gibibytes():.1f} GiB ({self.limit.source}) / {jobGib:g} GiB per job"
        if self.capped():
            fewer: str = "one at a time" if self.allowed == 0 else f"{self.allowed} at once"
            return f"--threads {self.requested} capped to {fewer}: {have}"
        return ""


__all__: list[str] = [
    "DEFAULT_BANNER_ART",
    "DirNode",
    "FileJob",
    "HostFacts",
    "JobResult",
    "JobSpec",
    "MemoryLimit",
    "PfdoOptions",
    "PfdoRunOptions",
    "Plugin",
    "PluginSpec",
    "ProcessResult",
    "RunResult",
    "ShExecOptions",
    "Span",
    "StageResult",
    "ThreadsCap",
    "TreeOptions",
]
