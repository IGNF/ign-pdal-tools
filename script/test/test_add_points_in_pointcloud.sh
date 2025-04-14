python -u -m pdaltools.add_points_in_pointcloud \
    --input_las test/data/decimated_laz/test_semis_2023_0292_6833_LA93_IGN69.laz \
    --output_las test/data/output/test_semis_2023_0292_6833_LA93_IGN69.laz \
    --input_geometry test/data/points_3d/Points_virtuels_0292_6833.geojson \
    --spatial_ref "EPSG:2154" \
    --tile_width 1000