#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the test script
python -m tests.test_api

# Deactivate virtual environment if it was activated
if [ -d "venv" ]; then
    deactivate
fi 