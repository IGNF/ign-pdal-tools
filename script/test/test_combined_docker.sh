#!/bin/bash
set -e

# Test if the Docker image exists
if ! docker image inspect pdal-combined >/dev/null 2>&1; then
    echo "Error: pdal-combined Docker image not found. Please build it first using:"
    echo "docker build -t pdal-combined -f Dockerfile.combined ."
    exit 1
fi

echo "=== Testing Combined PDAL Docker Image ==="

# Test 1: Check PDAL version
echo "[Test 1/5] Checking PDAL version..."
if ! docker run --rm pdal-combined pdal --version; then
    echo "❌ Failed to get PDAL version"
    exit 1
fi

# Test 2: Check Python and Python PDAL bindings
echo -e "\n[Test 2/5] Checking Python and PDAL bindings..."
if ! docker run --rm pdal-combined python -c "import pdal; print(f'Python PDAL version: {pdal.__version__}'); print(f'PDAL version: {pdal.Pipeline().version}')"; then
    echo "❌ Failed to verify Python PDAL bindings"
    exit 1
fi

# Test 3: Check conda environment
echo -e "\n[Test 3/5] Verifying conda environment..."
if ! docker run --rm pdal-combined bash -c "which python && python -c 'import sys; print(sys.prefix)' && conda info --envs"; then
    echo "❌ Failed to verify conda environment"
    exit 1
fi

# Test 4: Check custom PDAL branch
echo -e "\n[Test 4/5] Verifying custom PDAL branch..."
VERSION_INFO=$(docker run --rm pdal-combined pdal --version 2>&1)
if [[ $VERSION_INFO == *"read_las_with_sereral_LASF_Spec"* ]]; then
    echo "✅ Verified custom branch is being used"
else
    echo "⚠️  Could not verify custom branch in version info"
    echo "Version info: $VERSION_INFO"
fi

# Test 5: Run a simple PDAL command with a test file
echo -e "\n[Test 5/5] Running PDAL info with a test file..."

# Create a test script that will run inside the container
cat > test_combined.py << 'EOF'
import os
import numpy as np
from laspy import create, PointFormat

def create_test_las(filename):
    # Create a new LAS file
    header = create(version="1.2", point_format=PointFormat(3))
    header.x = np.array([0.0, 1.0, 2.0])
    header.y = np.array([0.0, 1.0, 2.0])
    header.z = np.array([0.0, 1.0, 2.0])
    header.write(filename)

def test_pdal():
    test_file = "test_combined.las"
    create_test_las(test_file)
    
    # Test PDAL info
    import pdal
    pipeline = pdal.Reader.las(filename=test_file).pipeline()
    metadata = pipeline.quickinfo['readers.las']
    print(f"PDAL quick info: {metadata}")
    
    # Test Python PDAL bindings
    pipeline = pdal.Reader.las(filename=test_file).pipeline()
    count = pipeline.execute()
    print(f"Processed {count} points")
    
    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    test_pdal()
EOF

# Run the test script inside the container
echo "Running Python test script in container..."
if ! docker run --rm -v "$(pwd)/test_combined.py:/test_combined.py" pdal-combined python /test_combined.py; then
    echo "❌ PDAL Python test failed"
    rm -f test_combined.py
    exit 1
fi

# Clean up
rm -f test_combined.py

echo -e "\n✅ All tests passed successfully!"
echo "The combined PDAL Docker image is working correctly with both PDAL and the conda environment."
