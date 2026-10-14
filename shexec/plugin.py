"""Making a ChRIS plugin out of shexec: the factory a downstream plugin calls.

A plugin that wraps a command-line program is shexec with four things changed: its
name and version, its description for ChRIS, the defaults of its flags, above all the
``--exec`` template, and the words on its manual page. ``plugin_build`` takes those as
a ``PluginSpec`` and returns a ``Plugin``: the parser with the defaults applied, the
manual composed from the plugin's own banner over pfdo_run's shared sections, and
``main`` already wrapped in pflog's ``timed`` and ``chris_plugin``. pl-shexec itself is
the first call of it; pl-freesurfer is the second, with FreeSurfer in the image and
``recon-all`` as the default template, and no engine code of its own.

Key components:
    - plugin_build: the factory
    - synopsis_build: the manual text for a spec
    - PLUGIN_SIGNATURE: the signature chris_plugin inspects

Typical usage:
    PLUGIN: Plugin = plugin_build(PluginSpec(
        name="freesurfer", version=__version__, title="FreeSurfer recon-all",
        defaults={"exec": RECON_ALL, "analyzeFileIndex": "f", "fileFilter": "glob:*.nii.gz"},
        minMemory="8Gi", minCpu="4000m",
    ))
    main = PLUGIN.main

Dependencies:
    - chris_plugin, pflog, pfdo_run.__main__, pftree.manual, shexec.shexec, shexec.models
"""

from __future__ import annotations

import argparse
import inspect
from collections.abc import Callable
from pathlib import Path

from chris_plugin import chris_plugin
from pfdo_run.__main__ import ARGS_SYNOPSIS_DS, CLI_DS, TAG_HELP, parser_build
from pflog import timed
from pftree.manual import Manual, manual_print

from shexec.models import Plugin, PluginSpec
from shexec.shexec import plugin_run

PLUGIN_SIGNATURE: inspect.Signature = inspect.Signature(
    [
        inspect.Parameter("options", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=argparse.Namespace),
        inspect.Parameter("inputdir", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Path),
        inspect.Parameter("outputdir", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Path),
    ],
    return_annotation=int,
)


def synopsis_build(spec: PluginSpec, shortOnly: bool = False) -> str:
    """The manual text for a plugin: its NAME, SYNOPSIS and brief example, then the shared sections.

    Args:
        spec: the plugin.
        shortOnly: NAME, SYNOPSIS and the brief example only.

    Returns:
        The text, without the banner.
    """
    shortSynopsis: str = (
        f"""
    NAME

        {spec.name}

    SYNOPSIS

        {spec.name} \\"""
        + CLI_DS
        + "\n\n    BRIEF EXAMPLE\n"
        + spec.briefExample
    )
    if shortOnly:
        return shortSynopsis
    return shortSynopsis + spec.description + "\n    ARGS " + ARGS_SYNOPSIS_DS + TAG_HELP + spec.examples


def manual_build(spec: PluginSpec) -> Manual:
    """The manual page for a plugin."""
    return Manual(
        command=spec.name,
        art=spec.bannerArt,
        title=spec.bannerTitle,
        text=spec.bannerText,
        version=spec.version,
        synopsisShort=synopsis_build(spec, shortOnly=True),
        synopsisFull=synopsis_build(spec, shortOnly=False),
    )


def parser_forSpec(spec: PluginSpec) -> argparse.ArgumentParser:
    """pfdo_run's parser named for the plugin, its defaults set from the spec.

    The defaults are set on the parser rather than applied afterwards, so the
    description ``chris_plugin_info`` serialises carries them and ChRIS shows them.
    """
    parser: argparse.ArgumentParser = parser_build(standalone=False, command=spec.name, version=spec.version)
    parser.set_defaults(**spec.defaults)
    return parser


def plugin_build(spec: PluginSpec, singleton: bool = True) -> Plugin:
    """Make a ChRIS plugin from a spec.

    Args:
        spec: name, version, description for ChRIS, flag defaults, manual text.
        singleton: register with chris_plugin's registry, which ``chris_plugin_info``
            reads; a test building several plugins in one process passes False.

    Returns:
        The plugin: its parser, its ``main`` for the console script, and its manual.

    Example:
        >>> plugin = plugin_build(PluginSpec(name="x", version="0.1"), singleton=False)
        >>> plugin.name, plugin.parser.get_default("exec")
        ('x', '')
    """
    parser: argparse.ArgumentParser = parser_forSpec(spec)
    manual: Manual = manual_build(spec)

    def body(options: argparse.Namespace, inputdir: Path, outputdir: Path) -> int:
        if options.man or options.synopsis:
            manual_print(manual, shortOnly=not options.man)
            return 0
        return plugin_run(options, inputdir, outputdir)

    body.__name__ = spec.name
    body.__qualname__ = spec.name
    body.__signature__ = PLUGIN_SIGNATURE  # type: ignore[attr-defined]  # what chris_plugin inspects; this module stringifies annotations
    timedBody: Callable[[argparse.Namespace, Path, Path], int] = timed(spec.name)(body)
    main: Callable[..., int] = chris_plugin(
        parser=parser,
        title=spec.title,
        category=spec.category,
        min_memory_limit=spec.minMemory,
        min_cpu_limit=spec.minCpu,
        min_gpu_limit=spec.minGpu,
        singleton=singleton,
    )(timedBody)
    return Plugin(name=spec.name, spec=spec, parser=parser, main=main, manual=manual)
