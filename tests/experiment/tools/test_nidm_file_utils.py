"""Tests for the shared -nl file-list resolver used by query / queryai."""

from __future__ import annotations
from pathlib import Path
from nidm.experiment.tools.nidm_file_utils import (
    bundled_cde_files,
    expand_nidm_file_list,
)


def _make_study(root: Path) -> None:
    """Two subjects, each with a canonical nidm.ttl plus a stray .ttl, and a
    top-level .ttl that should NOT be picked up by directory recursion."""
    for sub in ("sub-01", "sub-02"):
        (root / sub).mkdir(parents=True)
        (root / sub / "nidm.ttl").write_text("")
        (root / sub / "other.ttl").write_text("")  # must be ignored
    (root / "top.ttl").write_text("")


def test_directory_recurses_for_nidm_ttl_only(tmp_path: Path) -> None:
    _make_study(tmp_path)
    out = expand_nidm_file_list(str(tmp_path))
    assert out == [
        str(tmp_path / "sub-01" / "nidm.ttl"),
        str(tmp_path / "sub-02" / "nidm.ttl"),
    ]


def test_manifest_expands_lines_and_skips_comments(tmp_path: Path) -> None:
    _make_study(tmp_path)
    manifest = tmp_path / "list.txt"
    manifest.write_text(
        "# my study files\n"
        f"{tmp_path / 'sub-01'}\n"  # a directory entry
        "\n"  # blank line ignored
        f"{tmp_path / 'top.ttl'}\n"  # a literal file
        "https://example.org/remote.ttl\n"  # a URL
    )
    out = expand_nidm_file_list(str(manifest))
    assert out == [
        str(tmp_path / "sub-01" / "nidm.ttl"),
        str(tmp_path / "top.ttl"),
        "https://example.org/remote.ttl",
    ]


def test_glob_and_literal_and_url(tmp_path: Path) -> None:
    _make_study(tmp_path)
    out = expand_nidm_file_list(
        f"{tmp_path}/*/nidm.ttl,{tmp_path}/top.ttl,https://example.org/a.ttl"
    )
    assert out == [
        str(tmp_path / "sub-01" / "nidm.ttl"),
        str(tmp_path / "sub-02" / "nidm.ttl"),
        str(tmp_path / "top.ttl"),
        "https://example.org/a.ttl",
    ]


def test_dedupes_preserving_order(tmp_path: Path) -> None:
    _make_study(tmp_path)
    # the same directory listed twice yields each nidm.ttl once
    out = expand_nidm_file_list(f"{tmp_path},{tmp_path}")
    assert out == [
        str(tmp_path / "sub-01" / "nidm.ttl"),
        str(tmp_path / "sub-02" / "nidm.ttl"),
    ]


def test_include_cdes_appends_three_after_user_entries(tmp_path: Path) -> None:
    _make_study(tmp_path)
    out = expand_nidm_file_list(str(tmp_path / "top.ttl"), include_cdes=True)
    assert out[0] == str(tmp_path / "top.ttl")
    cdes = out[1:]
    assert len(cdes) == 3
    assert all(c.endswith(("ants_cde.ttl", "fs_cde.ttl", "fsl_cde.ttl")) for c in cdes)


def test_bundled_cde_files_prefers_cde_dir_env(tmp_path: Path, monkeypatch) -> None:
    cde_dir = tmp_path / "cdes"
    cde_dir.mkdir()
    for name in ("ants_cde.ttl", "fs_cde.ttl", "fsl_cde.ttl"):
        (cde_dir / name).write_text("")
    monkeypatch.setenv("CDE_DIR", str(cde_dir))
    out = bundled_cde_files()
    assert out == [
        str(cde_dir / "ants_cde.ttl"),
        str(cde_dir / "fs_cde.ttl"),
        str(cde_dir / "fsl_cde.ttl"),
    ]


def test_bundled_cde_files_returns_three(monkeypatch) -> None:
    """With no CDE_DIR, resolution still yields exactly three entries (the
    installed package copies, or the GitHub URLs as a last resort)."""
    monkeypatch.delenv("CDE_DIR", raising=False)
    out = bundled_cde_files()
    assert len(out) == 3
    assert all(
        str(c).endswith(("ants_cde.ttl", "fs_cde.ttl", "fsl_cde.ttl")) for c in out
    )
