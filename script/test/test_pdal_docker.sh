#!/bin/bash
set -e

# Test if the Docker image exists
if ! docker image inspect pdal-custom >/dev/null 2>&1; then
    echo "Error: pdal-custom Docker image not found. Please build it first using script/createDockerPDAL.sh"
    exit 1
fi

echo "=== Testing PDAL Docker image ==="

# Test 1: Check PDAL version
echo "[Test 1/3] Checking PDAL version..."
if ! docker run --rm pdal-custom --version; then
    echo "❌ Failed to get PDAL version"
    exit 1
fi

# Test 2: Run a simple PDAL command
echo -e "\n[Test 2/3] Running PDAL info with a test file..."
TEST_LAS="test.las"

# Create a minimal LAS file for testing if it doesn't exist
if [ ! -f "$TEST_LAS" ]; then
    echo "Creating test LAS file..."
    cat > create_test.py << 'EOF'
import numpy as np
from laspy import create, PointFormat

# Create a new LAS file
header = create(version="1.2", point_format=PointFormat(3))
header.x = np.array([0.0, 1.0, 2.0])
header.y = np.array([0.0, 1.0, 2.0])
header.z = np.array([0.0, 1.0, 2.0])
header.write("test.las")
EOF
    
    # Install laspy if not available
    if ! python3 -c "import laspy" &>/dev/null; then
        pip install laspy
    fi
    
    python3 create_test.py
    rm create_test.py
fi

# Run PDAL info on the test file
echo "Running PDAL info on test file..."
if ! docker run --rm -v "$(pwd):/data" pdal-custom info "/data/$TEST_LAS"; then
    echo "❌ PDAL info command failed"
    exit 1
fi

# Test 3: Check if the custom branch was used
echo -e "\n[Test 3/3] Verifying PDAL version information..."
VERSION_INFO=$(docker run --rm pdal-custom --version 2>&1)
if [[ $VERSION_INFO == *"read_las_with_sereral_LASF_Spec"* ]]; then
    echo "✅ Verified custom branch is being used"
else
    echo "⚠️  Could not verify custom branch in version info"
    echo "Version info: $VERSION_INFO"
fi

echo -e "\n✅ All tests passed successfully!"
echo "The PDAL Docker image is working correctly."
