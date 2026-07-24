#!/bin/bash

export PIP_CACHE_DIR=/goinfre/$USER/.cache/pip
export UV_CACHE_DIR=/goinfre/$USER/.cache/uv
VENV=/goinfre/$USER/.venv


mkdir -p "$PIP_CACHE_DIR" "$UV_CACHE_DIR"

echo "Creating virtual environment..."
python3 -m venv "$VENV"
source $VENV/bin/activate

echo "Installing uv..."
"$VENV/bin/python" -m pip install uv

echo "Installing dependencies"
"$VENV/bin/uv" sync --active

echo "Pulling Docker image for MBPP Tests"
docker pull python:3.11-slim

echo "To use the program, don't forget to activate the virtual environment by entering this command:"
echo "source $VENV/bin/activate && uv sync && cd moulinette && uv sync"
