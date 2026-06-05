"""Run an arbitrary PDAL pipeline on a LAS/LAZ file with explicit input and output paths."""

from __future__ import annotations

import argparse
import json
import logging
import os
from typing import Any, Dict, List, Sequence

import pdal

from pdaltools.unlock_file import copy_and_hack_decorator

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a PDAL pipeline on a LAS/LAZ file. "
        "The pipeline is a JSON array of PDAL stage objects."
    )
    parser.add_argument("--input_file", required=True, type=str, help="Input LAS/LAZ path.")
    parser.add_argument("--output_file", required=True, type=str, help="Output LAS/LAZ path.")
    parser.add_argument(
        "--pipeline",
        required=True,
        metavar="JSON",
        help="PDAL pipeline as a JSON array, or path to a .json file containing that array.",
    )
    return parser.parse_args()


def _validate_pipeline_stages(stages: Sequence[Any]) -> List[Dict[str, Any]]:
    validated: List[Dict[str, Any]] = []
    for i, stage in enumerate(stages):
        if not isinstance(stage, dict) or "type" not in stage:
            raise ValueError(
                f"pipeline[{i}] must be an object with a 'type' key (PDAL stage), got {stage!r}."
            )
        validated.append(dict(stage))
    return validated


def load_pipeline_json(raw: str) -> List[Dict[str, Any]]:
    """Load a PDAL pipeline from a JSON string or from a path to a JSON file."""
    stripped = raw.strip()
    if not stripped:
        raise ValueError("--pipeline must not be empty")
    if os.path.isfile(stripped):
        with open(stripped, encoding="utf-8") as f:
            parsed = json.load(f)
    else:
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid JSON for --pipeline: {e}") from e
    if not isinstance(parsed, list):
        raise ValueError("--pipeline must be a JSON array of PDAL stage objects")
    return _validate_pipeline_stages(parsed)


def bind_input_output(
    stages: Sequence[Dict[str, Any]],
    input_file: str,
    output_file: str,
) -> List[Dict[str, Any]]:
    """Wire ``input_file`` / ``output_file`` to the first reader and last writer stage.

    If the pipeline has no ``readers.las`` stage at the start, one is prepended.
    If it has no ``writers.las`` stage at the end, one is appended (with ``forward: all``).
    """
    bound = [dict(stage) for stage in stages]

    if bound and bound[0].get("type").startswith("readers."):
        if bound[0].get("type") != "readers.las":
            raise ValueError(f"if pipeline start with a reader, it must be a readers.las stage, got {bound[0].get('type')}")

    if not bound or bound[0].get("type") != "readers.las":
        bound.insert(0, {"type": "readers.las", "filename": input_file})
    else:
        print(f"Binding input file: {input_file}")
        bound[0]["filename"] = input_file

    if bound and bound[-1].get("type").startswith("writers."):
        if bound[-1].get("type") != "writers.las":
            raise ValueError(f"if pipeline end with a writer, it must be a writers.las stage, got {bound[-1].get('type')}")

    if bound[-1].get("type") != "writers.las":
        bound.append({"type": "writers.las", "filename": output_file, "extra_dims": "all", "forward": "all"})
    else:
        print(f"Binding output file: {output_file}")
        bound[-1]["filename"] = output_file
    return bound


@copy_and_hack_decorator
def run_pdal_pipeline(
    input_file: str,
    output_file: str,
    pipeline_stages: Sequence[Dict[str, Any]],
) -> None:
    """Execute ``pipeline_stages`` on ``input_file`` and write ``output_file``."""
    stages = bind_input_output(pipeline_stages, input_file, output_file)
    pipeline_json = json.dumps(stages)
    logger.debug("PDAL pipeline: %s", pipeline_json)
    pdal.Pipeline(pipeline_json).execute()


def main() -> None:
    args = parse_args()
    pipeline_stages = load_pipeline_json(args.pipeline)
    run_pdal_pipeline(args.input_file, args.output_file, pipeline_stages)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
