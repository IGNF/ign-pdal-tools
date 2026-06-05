#!/usr/bin/env bash
# Run a custom PDAL pipeline (JSON) on a LAS/LAZ file.
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p test/tmp

python -m pdaltools.run_pdal_pipeline \
    --input_file test/data/classified_laz/test_data_77050_627755_LA93_IGN69.laz \
    --output_file test/tmp/run_pdal_pipeline_out.laz \
    --pipeline test/data/example_pdal_pipeline.json
