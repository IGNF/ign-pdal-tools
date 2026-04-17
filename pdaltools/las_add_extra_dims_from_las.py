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
from typing import Any, Iterable, Optional, Sequence

import laspy
import numpy as np

_LAS_SUFFIXES = frozenset({".las", ".laz"})
logger = logging.getLogger(__name__)
# ANSI for terminal emphasis (ignored by non-TTY handlers in most setups).
_BOLD, _RESET = "\033[1m", "\033[0m"


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
    """
        Both point clouds have the same number of points, but row order in the file may differ (rewrite, filter, another tool).
        To copy dimensions from the source into the base, we need to know which source row matches which base row.
        The function returns a NumPy array of length len(base): for each base row index i,
        entry i is the source row index of the same physical point (in the sense of the alignment keys).
    """

    # get the columns to sort by (gps_time, z, y, x)
    base_sort_columns = _alignment_sort_columns(base)
    source_sort_columns = _alignment_sort_columns(source)

    # lexsort: last tuple element is primary key → order is (x, y, z, gps_time) as documented above.
    base_rows_in_sorted_key_order = np.lexsort(base_sort_columns)
    source_rows_in_sorted_key_order = np.lexsort(source_sort_columns)

    # Test duplicates in base on full key (x, y, z, gps_time), and log offending keys.
    key_dtype = np.dtype([("x", "f8"), ("y", "f8"), ("z", "f8"), ("gps_time", "f8")])
    base_keys = np.empty(len(base), dtype=key_dtype)
    base_keys["x"] = np.asarray(base.x, dtype=np.float64)
    base_keys["y"] = np.asarray(base.y, dtype=np.float64)
    base_keys["z"] = np.asarray(base.z, dtype=np.float64)
    base_keys["gps_time"] = np.asarray(base.gps_time, dtype=np.float64)
    uniq_keys, counts = np.unique(base_keys, return_counts=True)
    duplicate_mask = counts > 1
    if np.any(duplicate_mask):
        duplicate_count = int(np.sum(duplicate_mask))
        duplicate_examples = ", ".join(
            [
                f"(x={k['x']}, y={k['y']}, z={k['z']}, gps_time={k['gps_time']})"
                for k, c in zip(uniq_keys[duplicate_mask][:10], counts[duplicate_mask][:10])
            ]
        )
        logger.warning(
            f"{_BOLD}Base file contains {duplicate_count} duplicate key(s) on "
            f"(x,y,z,gps_time). This may cause unexpected behavior. "
            f"Examples: {duplicate_examples}{_RESET}"
        )

    # test that the sorted keys match between files
    #sort_column_index: 0 is gps_time, 1 is z, 2 is y, 3 is x (cf. _alignment_sort_columns)
    # source and base columns are zipped together and then sorted by the sort_column_index
    # base_key_sorted and source_key_sorted are the sorted columns
    # if the sorted columns are not the same, raise an error
    for sort_column_index, (base_column, source_column) in enumerate(
        zip(base_sort_columns, source_sort_columns)
    ):
        base_key_sorted = np.asarray(base_column[base_rows_in_sorted_key_order], dtype=np.float64)
        source_key_sorted = np.asarray(source_column[source_rows_in_sorted_key_order], dtype=np.float64)
        if sort_column_index == 0: # gps_time is the first column
            if not np.allclose(base_key_sorted, source_key_sorted, atol=gps_atol, rtol=gps_rtol):
                raise ValueError("gps_time sequences differ between base and source after sorting.")
        elif not np.allclose(base_key_sorted, source_key_sorted, atol=xyz_atol, rtol=0):
            raise ValueError("Coordinate sequences differ between base and source after sorting.")

    # Same multiset of keys → i-th row in sorted base order pairs with i-th row in sorted source order.
    source_row_for_each_base_row = np.empty(len(base), dtype=np.int64)
    source_row_for_each_base_row[base_rows_in_sorted_key_order] = source_rows_in_sorted_key_order.astype(
        np.int64
    )
    return source_row_for_each_base_row


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


def add_extra_dims_from_las(
    base_las: Path | str,
    source_las: Path | str,
    output_las: Path | str,
    dimensions: Optional[Iterable[str]] = None,
    *,
    xyz_atol: float = 1e-4,
    tiebreak_atol: float = 1e-6,
    tiebreak_rtol: float = 1e-12,
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

    row_map = _source_row_for_each_base_row(
        base, source, xyz_atol=xyz_atol, gps_atol=tiebreak_atol, gps_rtol=tiebreak_rtol
    )

    logger.info("Dimensions to copy: %s", dim_list)
    out = _clone_lasdata(base)
    for name in dim_list:
        src_arr = np.asarray(getattr(source, name))[row_map]
        out.add_extra_dim(laspy.ExtraBytesParams(name=name, type=np.dtype(src_arr.dtype).type))
        getattr(out, name)[:] = src_arr

    out.header.version = base.header.version
    out.write(output_path)
    logger.info("Written: %s", output_path)


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
