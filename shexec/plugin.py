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
    - parser_omit, manualText_omit: take flags a plugin does not offer out of its parser and manual
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
import copy
import inspect
import re
from collections.abc import Callable, Sequence
from pathlib import Path

from chris_plugin import chris_plugin
from pfdo_run.__main__ import ARGS_SYNOPSIS_DS, CLI_DS, TAG_HELP, parser_build
from pflog import timed
from pftree.manual import Manual, manual_attach

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


ENTRY_LINE: re.Pattern[str] = re.compile(r"^ {8}(?:\[--(?P<flag>[A-Za-z][\w-]*)|[\[<])")


def manualText_omit(text: str, flags: Sequence[str]) -> str:
    r"""The shared manual text without the entries for the given flags.

    The shared sections write each flag in one of two forms, both indented eight
    spaces: a synopsis line, ``[--threads <numThreads>]`` ending in a continuation
    backslash, and an ARGS entry, that line followed by its prose up to the next
    entry, which opens with ``[`` or ``<``, or the next section heading. Both are
    removed. A synopsis line that loses its successor keeps no dangling backslash.

    Args:
        text: a block of the shared manual, ``CLI_DS`` or ``ARGS_SYNOPSIS_DS``.
        flags: flag names without dashes.

    Returns:
        The block without those flags.

    Example:
        >>> manualText_omit("        [--a] \\\n        [--b]\n", ["b"])
        '        [--a]\n'
    """
    if not flags:
        return text
    omitted: set[str] = set(flags)
    kept: list[str] = []
    skipping: bool = False
    for line in text.splitlines(keepends=True):
        match: re.Match[str] | None = ENTRY_LINE.match(line)
        if match:
            skipping = match.group("flag") in omitted
        elif skipping and line.strip() and not line.startswith(" " * 8):
            skipping = False
        if not skipping:
            kept.append(line)
    if kept and text.rstrip().endswith("]") and kept[-1].rstrip().endswith("\\"):
        kept[-1] = kept[-1].rstrip()[:-1].rstrip() + "\n"
    return "".join(kept)


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
        + manualText_omit(CLI_DS, spec.omit)
        + "\n\n    BRIEF EXAMPLE\n"
        + spec.briefExample
    )
    if shortOnly:
        return shortSynopsis
    return (
        shortSynopsis
        + spec.description
        + "\n    ARGS "
        + manualText_omit(ARGS_SYNOPSIS_DS, spec.omit)
        + TAG_HELP
        + spec.examples
    )


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


def parser_omit(parser: argparse.ArgumentParser, names: Sequence[str]) -> None:
    """Take flags out of a parser, keeping each one's default as a fixed value.

    argparse has no public way to remove an argument, and the parser is assembled
    from pftree's, pfdo's and pfdo_run's parents, so the flag is removed from the
    three places argparse keeps it: the parser's actions, which chris_plugin
    serialises; the group that lists it in ``--help``; and the option-string map
    the command line is parsed against. Its default stays in the namespace, set
    with ``set_defaults``, so the engine reads the value it always did.

    Args:
        parser: the assembled parser, changed in place.
        names: destination names, as ``threads``.

    Raises:
        ValueError: a name the parser does not have; a misspelt omission would
            otherwise leave the flag in place unnoticed.

    Example:
        >>> p = argparse.ArgumentParser(); _ = p.add_argument("--n", dest="n", default=3)
        >>> parser_omit(p, ["n"]); p.parse_args([]).n
        3
    """
    # argparse internals: _actions, _action_groups, _group_actions and
    # _option_string_actions are private but stable from 3.11 to 3.14, and
    # chris_plugin itself reads _actions; CI runs every one of those versions.
    actions: dict[str, argparse.Action] = {action.dest: action for action in parser._actions}
    unknown: list[str] = [name for name in names if name not in actions]
    if unknown:
        raise ValueError(f"cannot omit flags the parser does not have: {', '.join(unknown)}")
    for name in names:
        action: argparse.Action = actions[name]
        parser._remove_action(action)
        for group in parser._action_groups:
            if action in group._group_actions:
                group._group_actions.remove(action)
        for optionString in action.option_strings:
            parser._option_string_actions.pop(optionString, None)
        parser.set_defaults(**{name: action.default})


def parser_forSpec(spec: PluginSpec) -> argparse.ArgumentParser:
    """pfdo_run's parser named for the plugin, its omitted flags removed, its defaults set from the spec.

    The defaults are set on the parser rather than applied afterwards, so the
    description ``chris_plugin_info`` serialises carries them and ChRIS shows them.
    They are set after the omission, so a spec can pin an omitted flag to a value
    of its own. ``--man`` and ``--synopsis`` print the plugin's own manual and exit as
    they are read, so they need no ``inputdir outputdir``.
    """
    parser: argparse.ArgumentParser = parser_build(standalone=False, command=spec.name, version=spec.version)
    parser_omit(parser, spec.omit)
    parser.set_defaults(**spec.defaults)
    manual_attach(parser, manual_build(spec))
    return parser


def plugin_build(spec: PluginSpec, singleton: bool = True) -> Plugin:
    """Make a ChRIS plugin from a spec.

    The command line is parsed by the spec's full parser. The description ChRIS
    reads is made from a copy without the spec's ``chrisHidden`` flags: chris_plugin
    describes whatever parser was registered, so the plugin registers the copy and
    the console script parses with the original. ChRIS passes only the parameters
    it was told of, so in ChRIS a hidden flag keeps its default.

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
    chrisParser: argparse.ArgumentParser = copy.deepcopy(parser)
    parser_omit(chrisParser, spec.chrisHidden)
    manual: Manual = manual_build(spec)

    def body(options: argparse.Namespace, inputdir: Path, outputdir: Path) -> int:
        return plugin_run(options, inputdir, outputdir, jobMemory=spec.jobMemory)

    body.__name__ = spec.name
    body.__qualname__ = spec.name
    body.__signature__ = PLUGIN_SIGNATURE  # type: ignore[attr-defined]  # what chris_plugin inspects; this module stringifies annotations
    timedBody: Callable[[argparse.Namespace, Path, Path], int] = timed(spec.name)(body)

    def chris_wrap(using: argparse.ArgumentParser, register: bool) -> Callable[..., int]:
        return chris_plugin(
            parser=using,
            title=spec.title,
            category=spec.category,
            min_memory_limit=spec.minMemory,
            min_cpu_limit=spec.minCpu,
            min_gpu_limit=spec.minGpu,
            singleton=register,
        )(timedBody)

    main: Callable[..., int] = chris_wrap(parser, register=False)
    if singleton:
        # Registered for chris_plugin_info only; the console script is ``main``.
        chris_wrap(chrisParser, register=True)
    return Plugin(name=spec.name, spec=spec, parser=parser, chrisParser=chrisParser, main=main, manual=manual)
