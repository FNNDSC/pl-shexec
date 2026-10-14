pl-shexec
=========

**Run a shell-type command over every file of a tree, as a ChRIS plugin.**

``pl-shexec`` is a `ChRIS <https://chrisproject.org/>`_ DS plugin for the jobs that are too small to deserve a plugin of their own: convert every image, zip every directory, rename, copy one file out of each subject, count lines. It takes a command template, runs it once per selected file of every directory in its input tree, and writes the results, and a record of each run, into an output tree that mirrors the input.

.. code-block:: bash

    shexec --fileFilter 'glob:*.jpg'                                            \
        --exec "convert %{inputWorkingDir}/%{inputWorkingFile}
                        %{outputWorkingDir}/%{inputWorkingFile|rmext}.png"      \
        /incoming /outgoing

The engine is `pfdo_run <https://github.com/FNNDSC/pfdo_run>`_; the plugin is pfdo_run with its directories supplied by ChRIS and its own run timed.

The template
------------

``--exec`` is not a shell command. It is a template whose ``%{...}`` tags name the file and directories in hand, resolved once per file, and run directly without a shell, so a path with a space in it stays one argument and nothing is interpreted that was not written. Three tags describe the job:

==========================  ==============================================
``%{inputWorkingDir}``      the input directory being processed
``%{outputWorkingDir}``     its counterpart in the output tree
``%{inputWorkingFile}``     the file being processed
==========================  ==============================================

Functions derive one name from another: ``%{inputWorkingFile|rmext}.png`` turns ``scan.jpg`` into ``scan.png``; ``%{inputWorkingDir|basename}`` is the directory's own name. Every flag of the plugin is a tag too, and so are ``%{timestamp}``, ``%{hostname}`` and ``%{user}``. The grammar is `pftag <https://github.com/FNNDSC/pftag>`_'s; ``shexec --man`` lists it under TAGS. A template with no tag draws a warning, since the same command would then run for every file.

What each run leaves behind
---------------------------

Beside each file's results in the output tree, four small files record what ran:

.. code-block:: text

    scan.png
    scan.jpg-cmd            the command, as executed
    scan.jpg-stdout         everything it printed
    scan.jpg-stderr         everything it complained
    scan.jpg-returncode     its exit status

The stream files are written while the command runs and, when it ends, rendered as a terminal would have shown them, so a progress bar redrawn a hundred times is one line. ``--noJobLogging`` turns the records off. ``--json`` prints the whole run's record on standard output.

The plugin's own run is timed by `pflog <https://github.com/FNNDSC/pflog>`_: one line of JSON on standard error, when it began, when it ended, the seconds, and whether it succeeded. CUBE keeps that line with the rest of the plugin's output, and any log collector indexes it.

Selecting files and directories
-------------------------------

The filters are pftree's. ``--fileFilter`` and ``--dirFilter`` take substrings, or ``glob:`` and ``re:`` patterns, joined by ``--fileFilterLogic`` and ``--dirFilterLogic``; ``--maxDepth`` bounds the descent. ``--analyzeFileIndex`` chooses which of a directory's selected files get the command: ``a`` for all, ``f`` for the first, ``l`` for the last, ``m`` for the middle, or an index. ``f`` is how one command runs per directory, started on the first file, as for a DICOM series.

Directories run in parallel under ``--threads``. At ``--verbosity 2`` each command's output streams to the console as it runs.

Exit status
-----------

0 when at least one directory's jobs all succeeded; 1 when every directory failed or the run could not start; 2 when ``--exec`` is missing or a flag's value is unusable. A failed template, a command that cannot be found, or a non-zero exit fails its directory and the run continues; the record says why.

Running it
----------

From ChRIS, add the plugin to a pipeline and give it ``--exec`` and filters as parameters.

From the command line, with the image:

.. code-block:: bash

    docker run --rm -v $PWD/in:/incoming:ro -v $PWD/out:/outgoing:rw            \
        fnndsc/pl-shexec shexec --fileFilter txt                                \
        --exec "wc -l %{inputWorkingDir}/%{inputWorkingFile}" /incoming /outgoing

    docker run --rm fnndsc/pl-shexec shexec --man /tmp /tmp

With Apptainer, ``apptainer exec docker://fnndsc/pl-shexec shexec ...``. The image carries the coreutils, zip and unzip, bc, perl, tar, ImageMagick and the DCMTK tools.

As a Python package, ``pip install .`` in this repository gives the ``shexec`` command and the ``shexec`` module, whose ``plugin_run(options, inputdir, outputdir)`` is the body of the plugin and whose ``shexec.models`` re-exports every record pfdo_run, pfdo, pftree, hostlib and pflog produce.

Development
-----------

.. code-block:: bash

    uv venv --python /usr/bin/python3.14 .venv
    uv pip install --python .venv/bin/python -e ".[dev]"
    .venv/bin/ruff check . && .venv/bin/pytest -q
    PATH=$PWD/.venv/bin:$PATH chris_plugin_info --dock-image docker.io/fnndsc/pl-shexec:2.0.1 shexec

The CI workflow lints and tests on Python 3.11 to 3.14, builds the image on every push to ``main``, pushes it to Docker Hub and ghcr.io, and on a ``v*`` tag uploads the plugin's description to cube.chrisproject.org. The tag must match ``__version__`` in ``shexec/__init__.py``.

Layout
------

.. code-block:: text

    shexec/
    ├── __main__.py   the plugin: parser, manual, @chris_plugin @timed main
    ├── shexec.py     ShExec, options_build, plugin_run
    └── models.py     ShExecOptions, and every record below re-exported

``docs/purpose.adoc`` says why the plugin exists, ``docs/architecture.adoc`` how it is built, ``docs/history.adoc`` where it came from.
