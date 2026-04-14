"""Append extra dimensions from a donor LAS/LAZ into a base file (same point count).

Also supports directory inputs: process every LAS/LAZ whose **basename** exists in both
``base_dir`` and ``source_dir`` (top level only), writing ``output_dir / basename``.
"""

from __future__ import annotations

import argparse
import io
import logging
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence

import laspy
import numpy as np

_LAS_SUFFIXES = frozenset({".las", ".laz"})
logger = logging.getLogger(__name__)


def _clone_lasdata(las: laspy.LasData) -> laspy.LasData:
    # laspy LasData is not copy.deepcopy-safe; round-trip through memory is a faithful copy.
    buf = io.BytesIO()
    las.write(buf)
    buf.seek(0)
    return laspy.read(buf)


def _require_gps_time(base: laspy.LasData, source: laspy.LasData) -> None:
    if "gps_time" not in base.point_format.dimension_names:
        raise ValueError("Base LAS must contain dimension 'gps_time' (required for row matching).")
    if "gps_time" not in source.point_format.dimension_names:
        raise ValueError("Source LAS must contain dimension 'gps_time' (required for row matching).")


def _alignment_sort_columns(las: laspy.LasData) -> tuple[np.ndarray, ...]:
    """Column arrays for ``np.lexsort``: (gps_time, z, y, x); last key (x) is primary."""
    return (
        np.asarray(las.gps_time),
        np.asarray(las.z),
        np.asarray(las.y),
        np.asarray(las.x),
    )


def _source_row_for_each_base_row(
    base: laspy.LasData,
    source: laspy.LasData,
    *,
    xyz_atol: float,
    gps_atol: float,
    gps_rtol: float,
) -> np.ndarray:
    """Sort by (gps_time, z, y, x), check sorted keys match between files, map base row → source row."""

    kb, ks = _alignment_sort_columns(base), _alignment_sort_columns(source)
    idx_b, idx_s = np.lexsort(kb), np.lexsort(ks)
    n = len(base)

    for k, (bcol, scol) in enumerate(zip(kb, ks)):
        vb = np.asarray(bcol[idx_b], dtype=np.float64)
        vs = np.asarray(scol[idx_s], dtype=np.float64)
        if k == 0:
            if not np.allclose(vb, vs, atol=gps_atol, rtol=gps_rtol):
                raise ValueError("gps_time sequences differ between base and source after sorting.")
        elif not np.allclose(vb, vs, atol=xyz_atol, rtol=0):
            raise ValueError("Coordinate sequences differ between base and source after sorting.")

    out = np.empty(n, dtype=np.int64)
    out[idx_b] = idx_s.astype(np.int64)
    return out


def _dims_to_copy(base: laspy.LasData, source: laspy.LasData, dimensions: Optional[Sequence[str]]) -> list[str]:
    """Return dimension names to copy from source (all missing from base, or the requested subset)."""
    base_names = set(base.point_format.dimension_names)
    missing = [n for n in source.point_format.dimension_names if n not in base_names]
    if dimensions is None:
        return missing
    requested = list(dimensions)
    unknown = [d for d in requested if d not in source.point_format.dimension_names]
    if unknown:
        raise ValueError(f"Unknown dimension(s) in source file: {unknown}")
    not_missing = [d for d in requested if d in base_names]
    if not_missing:
        raise ValueError(
            f"Dimension(s) already present in base file (not copied): {not_missing}. "
            "Remove them from --dimensions or use a base file without these fields."
        )
    return [d for d in requested if d in missing]


def _las_point_attr(dimension_name: str) -> str:
    return {"X": "x", "Y": "y", "Z": "z"}.get(dimension_name, dimension_name)


def _verify_merge_output(
    base_path: Path,
    source_path: Path,
    output_path: Path,
    dim_list: Sequence[str],
    *,
    xyz_atol: float,
    gps_atol: float,
    gps_rtol: float,
) -> None:
    """Re-read files and assert base dimensions are preserved and copied dims match the source mapping."""
    base = laspy.read(base_path)
    source = laspy.read(source_path)
    output = laspy.read(output_path)
    if not (len(base) == len(output) == len(source)):
        raise AssertionError(
            f"point count mismatch after merge: base={len(base)} output={len(output)} source={len(source)}"
        )
    row_map = _source_row_for_each_base_row(
        base, source, xyz_atol=xyz_atol, gps_atol=gps_atol, gps_rtol=gps_rtol
    )
    for name in base.point_format.dimension_names:
        attr = _las_point_attr(name)
        b = np.asarray(getattr(base, attr))
        o = np.asarray(getattr(output, attr))
        if np.issubdtype(b.dtype, np.floating):
            if not np.allclose(b, o, rtol=0, atol=1e-3):
                raise AssertionError(f"dimension {name!r} differs between base and output")
        elif not np.array_equal(b, o):
            raise AssertionError(f"dimension {name!r} differs between base and output")
    for name in dim_list:
        src_arr = np.asarray(getattr(source, name))[row_map]
        out_arr = np.asarray(getattr(output, name))
        if np.issubdtype(src_arr.dtype, np.floating):
            if not np.allclose(src_arr, out_arr, rtol=0, atol=1e-5):
                raise AssertionError(f"copied dimension {name!r} does not match source after alignment")
        elif not np.array_equal(src_arr, out_arr):
            raise AssertionError(f"copied dimension {name!r} does not match source after alignment")


def add_extra_dims_from_las(
    base_las: Path | str,
    source_las: Path | str,
    output_las: Path | str,
    dimensions: Optional[Iterable[str]] = None,
    *,
    xyz_atol: float = 1e-4,
    tiebreak_atol: float = 1e-6,
    tiebreak_rtol: float = 1e-12,
    test_output: bool = False,
) -> None:
    """
    Copy into ``base_las`` every dimension that exists in ``source_las`` but not in the base
    (or only those listed in ``dimensions``). Same point count required.

    Both files must include **gps_time**. Rows are paired by lexicographic sort on
    **gps_time, z, y, x** (same multiset of keys in base and source at the given tolerances).
    """
    base_path = Path(base_las)
    source_path = Path(source_las)
    output_path = Path(output_las)
    base = laspy.read(base_path)
    source = laspy.read(source_path)
    logger.info("Base: %s, source: %s", base_path, source_path)

    if len(base) != len(source):
        raise ValueError(f"Point count mismatch: base has {len(base)} points, source has {len(source)}.")

    _require_gps_time(base, source)

    dim_list = _dims_to_copy(base, source, list(dimensions) if dimensions is not None else None)
    if not dim_list:
        raise ValueError("No dimension to copy: source has no extra field missing from the base file.")

    logger.info("Dimensions to copy: %s", dim_list)
    row_map = _source_row_for_each_base_row(
        base, source, xyz_atol=xyz_atol, gps_atol=tiebreak_atol, gps_rtol=tiebreak_rtol
    )

    out = _clone_lasdata(base)
    for name in dim_list:
        src_arr = np.asarray(getattr(source, name))[row_map]
        out.add_extra_dim(laspy.ExtraBytesParams(name=name, type=np.dtype(src_arr.dtype).type))
        getattr(out, name)[:] = src_arr

    out.header.version = base.header.version
    out.write(output_path)
    logger.info("Written: %s", output_path)

    if test_output:
        _verify_merge_output(
            base_path,
            source_path,
            output_path,
            dim_list,
            xyz_atol=xyz_atol,
            gps_atol=tiebreak_atol,
            gps_rtol=tiebreak_rtol,
        )
        logger.info("Output file verified: %s", output_path)


def _is_las_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in _LAS_SUFFIXES


def _las_files_directly_in_dir(directory: Path) -> dict[str, Path]:
    """Map basename -> path for LAS/LAZ files directly under ``directory`` (non-recursive)."""
    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    found: dict[str, Path] = {}
    for p in directory.iterdir():
        if _is_las_file(p):
            if p.name in found:
                raise ValueError(f"Duplicate LAS/LAZ basename in {directory}: {p.name}")
            found[p.name] = p
    return found


def _log_unpaired_basenames(names: set[str], reason: str) -> None:
    for name in sorted(names):
        print(f"[las_add_extra_dims] skip ({reason}): {name}", file=sys.stderr)


def add_extra_dims_from_las_dirs(
    base_dir: Path | str,
    source_dir: Path | str,
    output_dir: Path | str,
    dimensions: Optional[Iterable[str]] = None,
    *,
    xyz_atol: float = 1e-4,
    tiebreak_atol: float = 1e-6,
    tiebreak_rtol: float = 1e-12,
    test_output: bool = False,
) -> list[str]:
    """
    For each LAS/LAZ **basename** present in both ``base_dir`` and ``source_dir`` (top level only),
    run :func:`add_extra_dims_from_las` and write ``output_dir / basename``.

    Basenames present in only one directory are always reported on stderr (unpaired files).

    Returns basenames processed successfully.
    """
    base_dir = Path(base_dir)
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_map = _las_files_directly_in_dir(base_dir)
    source_map = _las_files_directly_in_dir(source_dir)
    common = sorted(set(base_map) & set(source_map))
    if not common:
        raise ValueError(
            f"No common LAS/LAZ filenames between {base_dir} and {source_dir} "
            f"(extensions: {', '.join(sorted(_LAS_SUFFIXES))})."
        )

    _log_unpaired_basenames(set(base_map) - set(source_map), "not in source")
    _log_unpaired_basenames(set(source_map) - set(base_map), "not in base")

    common_args = dict(
        dimensions=dimensions,
        xyz_atol=xyz_atol,
        tiebreak_atol=tiebreak_atol,
        tiebreak_rtol=tiebreak_rtol,
        test_output=test_output,
    )
    done: list[str] = []
    for name in common:
        try:
            add_extra_dims_from_las(base_map[name], source_map[name], output_dir / name, **common_args)
            done.append(name)
        except ValueError as e:
            raise ValueError(f"{name}: {e}") from e

    return done


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Copy extra LAS columns from a donor file into a base file. "
        "Same points; both files must have gps_time; rows matched by sorted (gps_time, z, y, x). "
        "If --base and --source are directories, every common LAS/LAZ basename is processed and "
        "written under --output (directory, created if missing)."
    )
    p.add_argument(
        "--base",
        "-b",
        type=str,
        required=True,
        help="Base LAS/LAZ file, or directory of LAS/LAZ (pairs by matching filename with --source).",
    )
    p.add_argument(
        "--source",
        "-s",
        type=str,
        required=True,
        help="Donor LAS/LAZ file, or directory of LAS/LAZ (same basenames as in --base).",
    )
    p.add_argument(
        "--output",
        "-o",
        type=str,
        required=True,
        help="Output LAS/LAZ path, or output directory when --base/--source are directories.",
    )
    p.add_argument(
        "-d",
        "--dimensions",
        type=str,
        nargs="+",
        default=None,
        help="Dimensions to copy (default: all missing from base).",
    )
    p.add_argument("--xyz-atol", type=float, default=1e-4, help="Tolerance on x,y,z (default: 1e-4).")
    p.add_argument("--tiebreak-atol", type=float, default=1e-6, help="Absolute tolerance on gps_time (default: 1e-6).")
    p.add_argument(
        "--tiebreak-rtol", type=float, default=1e-12, help="Relative tolerance on gps_time (default: 1e-12)."
    )
    p.add_argument("--test-output", action="store_true", help="Test the output file after processing.")
    return p.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    base_p = Path(args.base)
    source_p = Path(args.source)
    output_p = Path(args.output)
    common_args = dict(
        dimensions=args.dimensions,
        xyz_atol=args.xyz_atol,
        tiebreak_atol=args.tiebreak_atol,
        tiebreak_rtol=args.tiebreak_rtol,
        test_output=args.test_output,
    )

    if base_p.is_dir() and source_p.is_dir():
        if output_p.exists() and not output_p.is_dir():
            raise SystemExit("--output must be a directory when --base and --source are directories.")
        output_p.mkdir(parents=True, exist_ok=True)
        add_extra_dims_from_las_dirs(base_p, source_p, output_p, **common_args)
    elif base_p.is_dir() or source_p.is_dir():
        raise SystemExit("--base and --source must both be files or both be directories.")
    else:
        add_extra_dims_from_las(base_p, source_p, output_p, **common_args)


if __name__ == "__main__":
    main()
