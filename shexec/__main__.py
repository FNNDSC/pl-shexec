"""The ``shexec`` command: a ChRIS DS plugin that runs a command over every file of a tree.

This module is shexec's own call of ``plugin_build``: its name, its description for
ChRIS, no flag defaults, and its words on the manual page. A plugin built on shexec
has a module of the same shape with its own spec; see ``shexec.plugin`` and the
README's "Building a plugin on pl-shexec".

Key components:
    - SPEC: what shexec says about itself
    - PLUGIN: the built plugin
    - parser, main: the plugin's flags and the console script's target

Typical usage:
    shexec --fileFilter 'glob:*.jpg' --exec "convert %{inputWorkingDir}/%{inputWorkingFile}
        %{outputWorkingDir}/%{inputWorkingFile|rmext}.png" /incoming /outgoing

Dependencies:
    - shexec.plugin, shexec.models
"""

from __future__ import annotations

import argparse
from collections.abc import Callable

from pftree.manual import Manual

from shexec import __version__
from shexec.models import Plugin, PluginSpec
from shexec.plugin import plugin_build

TITLE: str = "Execute shell-type commands across input spaces"
CATEGORY: str = "Utility"
MIN_MEMORY: str = "2Gi"
MIN_CPU: str = "1000m"

BANNER_ART: str = r"""
       _            _
      | |          | |
 _ __ | |______ ___| |__   _____  _____  ___
| '_ \| |______/ __| '_ \ / _ \ \/ / _ \/ __|
| |_) | |      \__ \ | | |  __/>  <  __/ (__
| .__/|_|      |___/_| |_|\___/_/\_\___|\___|
| |
|_|
"""

BANNER_TITLE: str = "Run shell-type commands over an input tree"

BANNER_TEXT: str = """
                    Run shell-type commands over an input tree

                             -- version {version} --

        A ChRIS DS plugin that runs one command for every selected file of
        every directory in its input tree, the command written as a template
        whose %{{...}} tags name the file and directories in hand. The output
        tree mirrors the input tree; each command's record lands beside its
        results. The engine is pfdo_run.
"""

DESCRIPTION: str = """
    DESCRIPTION

        ``shexec`` is pfdo_run as a ChRIS plugin. ChRIS gives it an input and
        an output directory; every other flag is pfdo_run's. The input tree is
        walked, files are selected in each directory by the filters and
        --analyzeFileIndex, and the --exec template is run once per selected
        file with its tags resolved against that directory and file, without
        a shell. Each job's record, the command, its output, its exit status,
        the host and the timing, is one line of JSON in jobs.jsonl in its
        output directory unless --noJobLogging is given; --jobFiles adds the
        four files beside the result; at --verbosity 2 a job's output is also
        streamed to the console as it runs.

        The plugin's own run is timed: one line of JSON on standard error, when
        it began, when it ended, the seconds, and whether it succeeded. CUBE
        keeps that line with the rest of the plugin's output.

        The exit status is 0 when at least one directory's jobs all succeeded,
        1 when every directory failed or the run could not start, 2 when --exec
        is missing. The commands available are those of the container image:
        the coreutils, zip and unzip, bc, perl, tar, ImageMagick's convert,
        and the DCMTK tools.
"""

EXAMPLES: str = """

    EXAMPLES

    Convert every jpg in the input tree to png in the output tree:

        shexec                                                                  \\
            --fileFilter 'glob:*.jpg'                                           \\
            --exec "convert %{inputWorkingDir}/%{inputWorkingFile}
                            %{outputWorkingDir}/%{inputWorkingFile|rmext}.png"  \\
            --threads 4 /incoming /outgoing

    Each conversion's command, stdout, stderr, return code and timing are one
    line in the directory's jobs.jsonl; ``pflog read /outgoing/**/jobs.jsonl``
    lists them.

    Copy one file out of each directory whose path names a subject:

        shexec                                                                  \\
            --dirFilter 100307                                                  \\
            --exec "cp %{inputWorkingDir}/brain.mgz %{outputWorkingDir}/brain.mgz" \\
            --analyzeFileIndex f --noJobLogging /incoming /outgoing

    Zip each directory's files into one archive named after the directory:

        shexec                                                                  \\
            --analyzeFileIndex f                                                \\
            --exec "zip -j %{outputWorkingDir}/%{inputWorkingDir|basename}.zip
                           %{inputWorkingDir}/%{inputWorkingFile}"              \\
            /incoming /outgoing

    From the image, with the directories mounted:

        docker run --rm -v $PWD/in:/incoming:ro -v $PWD/out:/outgoing:rw        \\
            fnndsc/pl-shexec shexec --fileFilter txt                            \\
            --exec "wc -l %{inputWorkingDir}/%{inputWorkingFile}" /incoming /outgoing
"""


BRIEF_EXAMPLE: str = """

        shexec --fileFilter 'glob:*.jpg'                                        \\
            --exec "convert %{inputWorkingDir}/%{inputWorkingFile}
                            %{outputWorkingDir}/%{inputWorkingFile|rmext}.png"  \\
            /incoming /outgoing
"""

SPEC: PluginSpec = PluginSpec(
    name="shexec",
    version=__version__,
    title=TITLE,
    category=CATEGORY,
    minMemory=MIN_MEMORY,
    minCpu=MIN_CPU,
    bannerArt=BANNER_ART,
    bannerTitle=BANNER_TITLE,
    bannerText=BANNER_TEXT,
    briefExample=BRIEF_EXAMPLE,
    description=DESCRIPTION,
    examples=EXAMPLES,
)

PLUGIN: Plugin = plugin_build(SPEC)
parser: argparse.ArgumentParser = PLUGIN.parser
main: Callable[..., int] = PLUGIN.main


def manual_build() -> Manual:
    """The shexec manual page."""
    return PLUGIN.manual
