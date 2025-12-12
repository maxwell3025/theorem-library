#!/bin/bash
cd $(dirname "$0")

if [ -z "$VIRTUAL_ENV" ]; then
    echo "Please activate a virtual environment before running this script."
    exit 1
fi

pip install -r requirements-dev.txt

python generate_env.py

python generate_compose.py

docker compose down --rmi all --volumes --remove-orphans
