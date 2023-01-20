rm -rf tmp/*
mkdir tmp/gpao_output_colored

INPUT_DIR=`pwd`/data/one_micro_laz
OUPUT_DIR=`pwd`/tmp/gpao_output_colored

docker run -e http_proxy=$http_proxy -e https_proxy=$https_proxy --rm --network host \
-v $INPUT_DIR:/input \
-v $OUPUT_DIR:/output \
lidarhd/lidarexpress \
python -m tools.color decomp_and_color_str \
/input/Semis_2021_0785_6378_LA93_IGN69_light.laz \
/output/Semis_2021_0785_6378_LA93_IGN69_light.las 0.1
