#!/usr/bin/env python

from pathlib import Path
from argparse import ArgumentParser, Namespace, ArgumentDefaultsHelpFormatter, RawTextHelpFormatter
from importlib.metadata import Distribution

from chris_plugin import chris_plugin, PathMapper

__pkg       = Distribution.from_name(__package__)
__version__ = '1.2.17'

import  os, sys
os.environ['XDG_CONFIG_HOME'] = '/tmp'

import  pudb

import  pfmisc
from    pfmisc._colors              import Colors
from    pfmisc                      import other

from    pftag                       import pftag
from    pflog                       import pflog

from    argparse                    import Namespace
from    datetime                    import datetime

from    pfdo_run                    import  pfdo_run
from    pfdo_run.__main__           import  package_CLIDS,              \
                                            package_argsSynopsisDS,     \
                                            package_CLItagHelp,         \
                                            package_specialFunctionHelp
from    pfdo_run.__main__           import  parserDS


DISPLAY_TITLE = r"""
       _            _
      | |          | |
 _ __ | |______ ___| |__   _____  _____  ___
| '_ \| |______/ __| '_ \ / _ \ \/ / _ \/ __|
| |_) | |      \__ \ | | |  __/>  <  __/ (__
| .__/|_|      |___/_| |_|\___/_/\_\___|\___|
| |
|_|
"""

str_desc    = '''

                Run "shell" commands on input

                    -- version ''' + \
            Colors.YELLOW + __version__ + Colors.CYAN + ''' --

    This ChRIS DS plugin provides the ability to run shell-type jobs
    on input spaces. Typical use cases entail zipping, copying, re-
    naming.


''' + Colors.NO_COLOUR

def synopsis(ab_shortOnly = False):
    scriptName = os.path.basename(sys.argv[0])
    shortSynopsis =  '''
    NAME

        shexec

    SYNOPSIS

        shexec                                                                  \\
        [--pftelDB <DBURL>]                                                     \\''' \
        + package_CLIDS

    description = '''

    DESCRIPTION

        This plugin is a thin wrapper about ``pfdo_run``.

    ARGS

        [--pftelDB <DBURLpath>]
        If specified, send telemetry logging to the pftel server and the
        specfied DBpath:

            --pftelDB   <URLpath>/<logObject>/<logCollection>/<logEvent>

        for example

            --pftelDB http://localhost:22223/api/v1/weather/massachusetts/boston

        Indirect parsing of each of the object, collection, event strings is
        available through `pftag` so any embedded pftag SGML is supported. So

            http://localhost:22223/api/vi/%platform/%timestamp_strmsk|**********_/%name

        would be parsed to, for example:

            http://localhost:22223/api/vi/Linux/2023-03-11/posix''' +\
    package_argsSynopsisDS + '''

    NOTE: ''' + package_CLItagHelp + package_specialFunctionHelp + '''

    EXAMPLES

    Perform a `shexec` down some input directory and convert all input
    ``jpg`` files to ``png`` in the output tree:

        shexec                                                      \\
            /var/www/html/data --fileFilter jpg                     \\
            /var/www/html/png                                       \\
            --exec "convert %inputWorkingDir/%inputWorkingFile
            %outputWorkingDir/%_rmext_inputWorkingFile.png"         \\
            --threads 0 --printElapsedTime

    The above will find all files in the tree structure rooted at
    /var/www/html/data that also contain the string "jpg" anywhere
    in the filename. For each file found, a `convert` conversion
    will be called, storing a converted file in the same tree location
    in the output directory as the original input.

    Note the special construct, %_rmext_inputWorkingFile.png -- the
    %_<func>_ designates a built in funtion to apply to the
    tag value. In this case, to "remove the extension" from the
    %inputWorkingFile string.

    Consider an example where only one file in a branched inputdir
    space is to be preserved:

        shexec                                                      \\
            $PWD/raw $PWD/out                                       \\
            --dirFilter 100307                                      \\
            --exec "cp %inputWorkingDir/brain.mgz
            %outputWorkingDir/brain.mgz"                            \\
            --threads 0 --verbosity 3 --noJobLogging

    Here, the input directory space is pruned for a directory leaf
    node that contains the string 100307. The exec command essentially
    copies the file `brain.mgz` in that target directory to the
    corresponding location in the output tree.

    Finally the elapsed time and a JSON output are printed.

'''
    if ab_shortOnly:
        return shortSynopsis
    else:
        return shortSynopsis + description

def earlyExit_check(args) -> int:
    """Perform some preliminary checks
    """
    if args.man or args.synopsis:
        print(str_desc)
        if args.man:
            str_help     = synopsis(False)
        else:
            str_help     = synopsis(True)
        print(str_help)
        return 1
    if args.b_version:
        print("Name:    %s\nVersion: %s" % (__name__, __version__))
        return 1
    return 0

parserDS.add_argument(
            "--pftelDB",
            help    = "an optional pftel telemetry logger, of form '<pftelURL>/api/v1/<object>/<collection>/<event>'",
            default = ''
)

@chris_plugin(
    parser              = parserDS,
    title               = 'Execute shell-type commands across input spaces',
    category            = 'utility',    # ref. https://chrisstore.co/plugins
    min_memory_limit    = '2Gi',        # supported units: Mi, Gi
    min_cpu_limit       = '1000m',      # millicores, e.g. "1000m" = 1 CPU core
    min_gpu_limit       = 0             # set min_gpu_limit=1 to enable GPU
)
@pflog.tel_logTime(
    event               = 'shexec',
    log                 = 'filter a specific upstream inputfile into outputdir'
)
def main(options: Namespace, inputdir: Path, outputdir: Path):
    """
    Simple call to pfdo_run
    """

    d_run:dict              = {}

    if int(options.verbosity)   : print(DISPLAY_TITLE)
    if earlyExit_check(options): return 1

    options.str_version     = __version__
    options.str_desc        = synopsis(True)
    options.inputDir        = options.inputdir      # Camel case "annoyances"
    options.outputDir       = options.outputdir

    pf_shexec:pfdo_run.pfdo_run = pfdo_run.pfdo_run(vars(options))
    d_run                       = pf_shexec.run(timerStart = True)

    if options.printElapsedTime:
        pf_shexec.dp.qprint(
            "Elapsed time = %f seconds" % d_run['runTime']
        )

    return 0

if __name__ == '__main__':
    sys.exit(main())
