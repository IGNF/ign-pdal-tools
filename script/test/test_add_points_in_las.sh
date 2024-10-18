python -u -m pdaltools.add_points_in_las \
    --input_file test/data/test_data_77055_627760_LA93_IGN69.LAZ \
    --output_file test/tmp/addded_cmdline.laz \
    --input_geo_file test/data/add_points/add_points.geojson \
    --dimensions "Classification"=64 "Intensity"=1.1