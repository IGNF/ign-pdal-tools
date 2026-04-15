"""Re-write las file with expected format:
- laz version
- [TODO] nomenclature ???
- record format
- global encoding
- projection
- precision
- no extra-dims
"""

import argparse
import json
import os
import tempfile
from typing import Any, Dict, List, Sequence

import pdal

from pdaltools.las_rename_dimension import rename_dimension
from pdaltools.unlock_file import copy_and_hack_decorator

# Standard parameters to pass to the pdal writer
STANDARD_PARAMETERS = dict(
    major_version="1",
    minor_version="4",  # Laz format version (pdal always write in 1.x format)
    global_encoding=17,  # store WKT projection in file
    compression="true",  # Save to compressed laz format
    extra_dims=[],  # Save no extra_dims
    scale_x=0.01,  # Precision of the stored data
    scale_y=0.01,
    scale_z=0.01,
    offset_x=0,  # No offset
    offset_y=0,
    offset_z=0,
    dataformat_id=6,  # No color by default
    a_srs="EPSG:2154",
)


def parse_args():
    parser = argparse.ArgumentParser("Rewrite laz file with standard format.")
    parser.add_argument("--input_file", type=str, help="Laz input file.")
    parser.add_argument("--output_file", type=str, help="Laz output file")
    parser.add_argument(
        "--record_format", choices=[6, 8], type=int, help="Record format: 6 (no color) or 8 (4 color channels)"
    )
    parser.add_argument("--projection", default="EPSG:2154", type=str, help="Projection, eg. EPSG:2154")
    parser.add_argument(
        "--extra_dims",
        default=[],
        nargs="*",
        type=str,
        help="List of extra dims to keep in the output (default=[], use 'all' to keep all extra dims), "
        "extra_dims must be specified with their type (see pdal.writers.las documentation, eg 'dim1=double')",
    )
    parser.add_argument(
        "--rename_dims",
        default=[],
        nargs="*",
        type=str,
        help="Rename dimensions in pairs: --rename_dims old_name1 new_name1 old_name2 new_name2 ...",
    )
    parser.add_argument(
        "--extra_filters",
        default=None,
        metavar="JSON",
        help='Optional JSON array of PDAL filter stages (each object must have a "type" key), '
        "inserted in order after readers.las and before writers.las.",
    )
    return parser.parse_args()


def parse_optional_extra_filters_json(raw: str | None) -> Sequence[Dict[str, Any]] | None:
    """Parse CLI ``--extra_filters``: a JSON array of PDAL stage dicts, or ``None`` if unset/blank."""
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON for --extra_filters: {e}") from e
    if not isinstance(parsed, list):
        raise ValueError("--extra_filters must be a JSON array of objects")
    for i, stage in enumerate(parsed):
        if not isinstance(stage, dict) or "type" not in stage:
            raise ValueError(
                f"--extra_filters[{i}] must be an object with a 'type' key (PDAL stage), got {stage!r}."
            )
    return parsed


def get_writer_parameters(new_parameters: Dict) -> Dict:
    """
    Get writer parameters from a set of standard parameters + a new set of parameters that can
    override the standard ones
    """
    params = STANDARD_PARAMETERS | new_parameters
    return params


def build_standardize_pipeline_json(
    input_path: str,
    output_path: str,
    writer_parameter_overrides: Dict,
    extra_filters: Sequence[Dict[str, Any]] | None = None,
) -> str:
    """
    Build a PDAL pipeline as a JSON string:

    ``readers.las`` → optional ``extra_filters`` → ``writers.las`` with :data:`STANDARD_PARAMETERS`
    merged with ``writer_parameter_overrides``.

    ``extra_filters`` is a sequence of PDAL stage dicts (each must include a ``type`` key), inserted
    in order before the writer. Do not put a final ``writers.las`` there; the closing writer stage
    is always appended by this function.

    Example — remove classes 64 and 65 before the writer::
        standardize(
            "in.laz",
            "out.laz",
            {"dataformat_id": 6, "a_srs": "EPSG:2154", "extra_dims": []},
            extra_filters=[{"type": "filters.expression", "expression": "Classification != 64&&Classification != 65"}],
        )
    """
    writer_opts = get_writer_parameters(writer_parameter_overrides)
    stages: List[Dict] = [{"type": "readers.las", "filename": input_path}]
    if extra_filters:
        for i, stage in enumerate(extra_filters):
            if not isinstance(stage, dict) or "type" not in stage:
                raise ValueError(
                    f"extra_filters[{i}] must be a dict with a 'type' key (PDAL stage), got {stage!r}."
                )
            stages.append(dict(stage))
    stages.append({"type": "writers.las", "filename": output_path, "forward": "all", **writer_opts})
    return json.dumps(stages)


@copy_and_hack_decorator
def standardize(
    input_file: str,
    output_file: str,
    writer_parameter_overrides: Dict,
    rename_dims: List | None = None,
    extra_filters: Sequence[Dict[str, Any]] | None = None,
) -> None:
    """
    Build the standardization pipeline via :func:`build_standardize_pipeline_json` and run it.

    ``input_file`` must remain the first argument for :func:`pdaltools.unlock_file.copy_and_hack_decorator`.

    Args:
        input_file: Input LAS/LAZ path.
        output_file: Output LAS/LAZ path.
        writer_parameter_overrides: Writer options merged with :data:`STANDARD_PARAMETERS` (e.g. ``dataformat_id``, ``a_srs``, ``extra_dims``).
        rename_dims: Optional flat list ``[old0, new0, ...]``; a temp copy is renamed before PDAL reads it.
        extra_filters: Optional PDAL stages before the writer (see :func:`build_standardize_pipeline_json`).
    """
    rename_dims = rename_dims or []
    tmp_file_name = None
    try:
        if rename_dims:
            with tempfile.NamedTemporaryFile(suffix=".laz", delete=False) as tmp_file:
                tmp_file_name = tmp_file.name
            old_dims = rename_dims[::2]
            new_dims = rename_dims[1::2]
            rename_dimension(input_file, tmp_file_name, old_dims, new_dims)
            reader_path = tmp_file_name
        else:
            reader_path = input_file

        pipeline_json = build_standardize_pipeline_json(
            reader_path,
            output_file,
            writer_parameter_overrides,
            extra_filters=extra_filters,
        )
        pdal.Pipeline(pipeline_json).execute()
    finally:
        if tmp_file_name and os.path.exists(tmp_file_name):
            os.remove(tmp_file_name)


def main():
    args = parse_args()
    try:
        extra_filters = parse_optional_extra_filters_json(args.extra_filters)
    except ValueError as e:
        raise SystemExit(f"standardize_format: {e}") from e
    params_from_parser = dict(
        dataformat_id=args.record_format,
        a_srs=args.projection,
        extra_dims=args.extra_dims,
    )
    standardize(
        args.input_file,
        args.output_file,
        params_from_parser,
        args.rename_dims,
        extra_filters,
    )


if __name__ == "__main__":
    main()
