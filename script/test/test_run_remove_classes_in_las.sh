#!/usr/bin/env bash
# Retrait des points de classification 2 via --extra_filters (JSON).
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p test/tmp

python -m pdaltools.standardize_format \
    --input_file test/data/classified_laz/test_data_77050_627755_LA93_IGN69.laz \
    --output_file test/tmp/replaced_cmdline.laz \
    --record_format 6 \
    --projection EPSG:2154 \
    --extra_dims \
    --rename_dims \
    --extra_filters '[{"type":"filters.expression","expression":"Classification != 2"}]'
