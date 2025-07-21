#!/bin/bash

# Build all language images for Judge0

set -e

echo "Building Judge0 language images..."

# List of languages to build
languages=("python3" "python2" "java" "cpp" "c" "node" "typescript")

for lang in "${languages[@]}"; do
    echo "Building $lang image..."
    docker build -t "judge0/$lang:latest" "./docker_images/$lang/"
    echo "✓ Built judge0/$lang:latest"
done

echo "All language images built successfully!"
echo ""
echo "Available images:"
docker images | grep judge0
