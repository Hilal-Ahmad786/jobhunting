#!/bin/bash

echo "Starting Job Hunter Bot..."
echo

cd "$(dirname "$0")"

if [ ! -d "job_hunter_env" ]; then
    echo "Virtual environment not found!"
    echo "Please run: python3 setup_job_hunter.py"
    exit 1
fi

source job_hunter_env/bin/activate

if ! python main.py; then
    echo
    echo "Job Hunter Bot encountered an error."
    echo "Check the log files in data/logs/ for details."
    read -p "Press Enter to continue..."
fi
