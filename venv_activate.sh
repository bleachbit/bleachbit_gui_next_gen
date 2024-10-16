#!/bin/bash

VENV_DIR="/tmp/venv/bleachbit_next_gen_gui"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists in $VENV_DIR."
fi

source "$VENV_DIR/bin/activate"

echo "Installing packages from requirements.txt..."
pip install -r requirements.txt

echo "Virtual environment activated."

