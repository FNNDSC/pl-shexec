"""shexec: a ChRIS DS plugin that runs a shell-type command over every file of a tree.

Key components:
    - plugin_build, PluginSpec, Plugin: make a ChRIS plugin from a spec; what a
      downstream plugin calls
    - ShExec: pfdo_run's engine, built from the plugin's arguments
    - ShExecOptions: the options
    - plugin_run: the body of the plugin's main
    - the records of pfdo_run and pflog, re-exported through shexec.models

Dependencies:
    - chris_plugin, pfdo_run, pflog
"""

from __future__ import annotations

__version__: str = "2.3.0"

from shexec.models import (
    DirNode,
    FileJob,
    HostFacts,
    JobResult,
    JobSpec,
    Plugin,
    PluginSpec,
    RunResult,
    ShExecOptions,
    Span,
    StageResult,
)
from shexec.plugin import plugin_build
from shexec.shexec import ShExec, options_build, plugin_run

__all__: list[str] = [
    "DirNode",
    "FileJob",
    "HostFacts",
    "JobResult",
    "JobSpec",
    "Plugin",
    "PluginSpec",
    "RunResult",
    "ShExec",
    "ShExecOptions",
    "Span",
    "StageResult",
    "__version__",
    "options_build",
    "plugin_build",
    "plugin_run",
]
