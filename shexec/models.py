"""The records shexec works with: its options, and everything pfdo_run's records carry.

A program built on shexec imports every record from here, and reaches past it into
pfdo_run, pfdo, pftree, hostlib or pflog for nothing.

Key components:
    - ShExecOptions: pfdo_run's options, for the plugin
    - PluginSpec: what a plugin built on shexec says about itself
    - Plugin: what ``plugin_build`` returns
    - DirNode, FileJob, JobResult, JobSpec, HostFacts, RunResult, StageResult,
      ProcessResult, TreeOptions, PfdoOptions, PfdoRunOptions: re-exported
    - Span: pflog's record of the plugin's run, re-exported

Dependencies:
    - pfdo_run.models, pflog.models
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

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
        parser: its flags, defaults applied; for ``chris_plugin`` and for tests.
        main: the decorated main, the console script's target.
        manual: its manual page.

    Example:
        >>> Plugin.__dataclass_fields__["main"].name
        'main'
    """

    name: str
    spec: PluginSpec
    parser: argparse.ArgumentParser
    main: Callable[..., int]
    manual: Any


__all__: list[str] = [
    "DEFAULT_BANNER_ART",
    "DirNode",
    "FileJob",
    "HostFacts",
    "JobResult",
    "JobSpec",
    "PfdoOptions",
    "PfdoRunOptions",
    "Plugin",
    "PluginSpec",
    "ProcessResult",
    "RunResult",
    "ShExecOptions",
    "Span",
    "StageResult",
    "TreeOptions",
]
