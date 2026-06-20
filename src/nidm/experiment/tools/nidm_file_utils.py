"""Shared helpers for expanding the ``-nl`` NIDM file list.

Both ``pynidm query`` and ``pynidm queryai`` accept a ``-nl`` value that is a
comma-separated list.  Historically every entry had to be a literal NIDM file
path, which is painful for studies with many per-subject files.  These helpers
let each comma-separated entry be any of:

  * a NIDM file path (``.ttl`` / ``.jsonld`` / ``.n3`` / ``.rdf`` / ``.owl``)
  * an ``http(s)://`` URL (rdflib fetches it)
  * a **directory** -> recursed for ``**/nidm.ttl`` (the canonical per-subject /
    per-site output name)
  * a **manifest** text file (``.txt`` / ``.list`` / ``.lst``) -> each non-blank,
    non-``#`` line is expanded recursively (so a manifest may list files,
    directories, globs, or URLs)
  * a shell **glob** (contains ``*``, ``?`` or ``[``) -> expanded

Optionally the bundled FreeSurfer / FSL / ANTS CDE files can be appended so the
common brain-volume questions resolve without the user listing them by hand.
"""

from __future__ import annotations
import glob as _glob
from os import environ, path
from nidm.core import Constants

# Suffixes treated as RDF/NIDM graph files (used as-is).
_GRAPH_SUFFIXES = (".ttl", ".jsonld", ".json", ".n3", ".rdf", ".owl", ".nt")
# Suffixes treated as a manifest (one entry per line).
_MANIFEST_SUFFIXES = (".txt", ".list", ".lst")
# What a directory is recursed for.
_DIR_RECURSE_GLOB = "**/nidm.ttl"
# The bundled CDE filenames (order matches Constants.CDE_FILE_LOCATIONS intent).
_CDE_FILENAMES = ("ants_cde.ttl", "fs_cde.ttl", "fsl_cde.ttl")


def _is_url(token: str) -> bool:
    return token.startswith("http://") or token.startswith("https://")


def _has_glob_magic(token: str) -> bool:
    return any(ch in token for ch in "*?[")


def bundled_cde_files() -> list[str]:
    """Return file paths (or URLs) for the ANTS/FS/FSL CDE files, local-first.

    Resolution order: ``CDE_DIR`` env var, the installed ``nidm/core/cde_dir``
    package directory, the ``/opt/project`` Docker location, then -- only if no
    local copy is found -- the canonical GitHub raw URLs from
    :data:`nidm.core.Constants.CDE_FILE_LOCATIONS`.
    """
    candidate_dirs = []
    if environ.get("CDE_DIR"):
        candidate_dirs.append(environ["CDE_DIR"])
    try:  # the copy shipped inside the installed package
        from nidm import core as _core

        candidate_dirs.append(path.join(path.dirname(_core.__file__), "cde_dir"))
    except Exception:  # pragma: no cover - import should always succeed
        pass
    candidate_dirs.append("/opt/project/nidm/core/cde_dir")

    for cde_dir in candidate_dirs:
        if cde_dir and all(
            path.isfile(path.join(cde_dir, name)) for name in _CDE_FILENAMES
        ):
            return [path.join(cde_dir, name) for name in _CDE_FILENAMES]

    # No local copy anywhere -> fall back to the canonical online locations.
    return list(Constants.CDE_FILE_LOCATIONS)


def expand_nidm_file_list(
    spec,
    include_cdes: bool = False,
    dir_recurse_glob: str = _DIR_RECURSE_GLOB,
    _seen=None,
) -> list[str]:
    """Expand a ``-nl`` *spec* into a concrete, de-duplicated file list.

    *spec* may be a comma-separated string or an iterable of tokens.  Order is
    preserved and duplicates are dropped.  Local paths have ``~`` expanded;
    URLs are passed through untouched.  When *include_cdes* is true the bundled
    CDE files are appended once, after the user's entries.
    """
    if _seen is None:
        _seen = set()
    out: list[str] = []

    def _add(item: str) -> None:
        if item not in _seen:
            _seen.add(item)
            out.append(item)

    tokens = spec if isinstance(spec, (list, tuple)) else str(spec).split(",")
    for raw in tokens:
        token = raw.strip()
        if not token:
            continue

        if _is_url(token):
            _add(token)
            continue

        expanded = path.expanduser(token)

        if path.isdir(expanded):
            for found in sorted(
                _glob.glob(path.join(expanded, dir_recurse_glob), recursive=True)
            ):
                _add(found)
        elif expanded.lower().endswith(_MANIFEST_SUFFIXES) and path.isfile(expanded):
            with open(expanded, encoding="utf-8") as handle:
                lines = [line.strip() for line in handle]
            for line in lines:
                if line and not line.startswith("#"):
                    # recurse so a manifest entry may itself be a dir/glob/URL
                    out.extend(
                        expand_nidm_file_list(
                            line,
                            include_cdes=False,
                            dir_recurse_glob=dir_recurse_glob,
                            _seen=_seen,
                        )
                    )
        elif _has_glob_magic(expanded):
            for found in sorted(_glob.glob(expanded, recursive=True)):
                _add(found)
        else:
            _add(expanded)

    if include_cdes:
        for cde in bundled_cde_files():
            _add(cde)

    return out
