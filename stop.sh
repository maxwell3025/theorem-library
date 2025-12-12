#!/bin/bash
cd $(dirname "$0")

if [ -z "$VIRTUAL_ENV" ]; then
    echo "Please activate a virtual environment before running this script."
    exit 1
fi

pip install -r requirements-dev.txt

python -m scripts.generate_env

python -m scripts.generate_compose

docker compose down --rmi all --volumes --remove-orphans
