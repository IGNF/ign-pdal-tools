rm -rf tmp/*
mkdir tmp/gpao_output_colored

INPUT_DIR=/media/data/Bug_ouverture_laz/one
OUPUT_DIR=`pwd`/tmp/gpao_output_colored

docker run -e http_proxy=$http_proxy -e https_proxy=$https_proxy --rm --network host \
-v $INPUT_DIR:/input \
-v $OUPUT_DIR:/output \
lidar_hd/lidar_express \
python -m tools.color decomp_and_color_str \
/input/436000_6469000.laz \
/output/436000_6469000.las 0.1
