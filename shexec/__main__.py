"""The ``shexec`` command: a ChRIS DS plugin that runs a command over every file of a tree.

The parser is pfdo_run's, without ``--inputDir`` and ``--outputDir``; ChRIS supplies
those as positional arguments. ``main`` wears ``@chris_plugin``, which registers the
plugin and parses the command line, and inside it ``@timed``, which clocks the body
alone and writes the span on standard error where CUBE keeps the plugin's output.
``--man`` prints the full manual, ``--synopsis`` its first page.

Key components:
    - BANNER_*, DESCRIPTION, EXAMPLES: the manual's own text; the rest is pfdo_run's
    - synopsis, manual_build: the manual
    - parser: the plugin's flags, for chris_plugin and for tests
    - main: the plugin

Typical usage:
    shexec --fileFilter 'glob:*.jpg' --exec "convert %{inputWorkingDir}/%{inputWorkingFile}
        %{outputWorkingDir}/%{inputWorkingFile|rmext}.png" /incoming /outgoing

Dependencies:
    - chris_plugin, pfdo_run.__main__, pftree.manual, pflog, shexec.shexec
"""

# No ``from __future__ import annotations`` here: chris_plugin reads main's annotations
# as objects to tell a DS plugin from an FS plugin, and stringified ones fail that check.

import argparse
from pathlib import Path

from chris_plugin import chris_plugin
from pfdo_run.__main__ import ARGS_SYNOPSIS_DS, CLI_DS, TAG_HELP, parser_build
from pflog import timed
from pftree.manual import Manual, manual_print

from shexec import __version__
from shexec.shexec import plugin_run

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


def synopsis(shortOnly: bool = False) -> str:
    """Assemble the manual text.

    Args:
        shortOnly: NAME, SYNOPSIS and a brief example only.

    Returns:
        The manual text, without the banner.
    """
    shortSynopsis: str = (
        """
    NAME

        shexec

    SYNOPSIS

        shexec \\"""
        + CLI_DS
        + """

    BRIEF EXAMPLE

        shexec --fileFilter 'glob:*.jpg'                                        \\
            --exec "convert %{inputWorkingDir}/%{inputWorkingFile}
                            %{outputWorkingDir}/%{inputWorkingFile|rmext}.png"  \\
            /incoming /outgoing
    """
    )
    if shortOnly:
        return shortSynopsis
    return shortSynopsis + DESCRIPTION + "\n    ARGS " + ARGS_SYNOPSIS_DS + TAG_HELP + EXAMPLES


def manual_build() -> Manual:
    """The shexec manual page."""
    return Manual(
        command="shexec",
        art=BANNER_ART,
        title=BANNER_TITLE,
        text=BANNER_TEXT,
        version=__version__,
        synopsisShort=synopsis(shortOnly=True),
        synopsisFull=synopsis(shortOnly=False),
    )


parser: argparse.ArgumentParser = parser_build(standalone=False, command="shexec", version=__version__)


@chris_plugin(
    parser=parser,
    title=TITLE,
    category=CATEGORY,
    min_memory_limit=MIN_MEMORY,
    min_cpu_limit=MIN_CPU,
)
@timed("shexec")
def main(options: argparse.Namespace, inputdir: Path, outputdir: Path) -> int:
    """The plugin.

    Args:
        options: the parsed flags.
        inputdir: the input tree, from ChRIS.
        outputdir: the output tree, from ChRIS.

    Returns:
        The exit status; see the manual.
    """
    if options.man or options.synopsis:
        manual_print(manual_build(), shortOnly=not options.man)
        return 0
    return plugin_run(options, inputdir, outputdir)
