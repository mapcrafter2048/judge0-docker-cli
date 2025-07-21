@echo off
REM Build all language images for Judge0

echo Building Judge0 language images...

REM List of languages to build
set languages=python3 python2 java cpp c node typescript

for %%L in (%languages%) do (
    echo Building %%L image...
    docker build -t "judge0/%%L:latest" "./docker_images/%%L/"
    echo ✓ Built judge0/%%L:latest
)

echo All language images built successfully!
echo.
echo Available images:
docker images | findstr judge0
