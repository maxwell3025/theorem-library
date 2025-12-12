#!/usr/bin/env python3
"""
Generate a docker-compose.yml file from common/config.py.

This script reads the DockerComposeConfig from common/config.py and generates
a properly formatted docker-compose.yml file using compose-pydantic.

Usage:
    python generate_compose.py [--output docker-compose.yml]
"""

import argparse
import sys
from pathlib import Path
import yaml

from common.compose import compose_specification
from compose_pydantic import Condition  # type: ignore[import-untyped]


def main():
    parser = argparse.ArgumentParser(
        description="Generate docker-compose.yml from common/config.py"
    )

    parser.add_argument(
        "--output",
        "-o",
        default="docker-compose.yml",
        help="Output file path (default: docker-compose.yml)",
    )

    args = parser.parse_args()
    output_path = Path(args.output)

    content = compose_specification.model_dump(exclude_none=True, by_alias=True)

    def represent_enum_as_string(dumper: yaml.SafeDumper, data: Condition):
        return dumper.represent_str(data.value)

    yaml.SafeDumper.add_representer(Condition, represent_enum_as_string)

    # Source - https://stackoverflow.com/a/41786451
    # Posted by Jace Browning, modified by community. See post 'Timeline' for change history
    # Retrieved 2025-12-12, License - CC BY-SA 4.0

    def represent_none(dumper: yaml.SafeDumper, _):
        return dumper.represent_scalar("tag:yaml.org,2002:null", "")

    yaml.add_representer(type(None), represent_none)

    yaml.SafeDumper.ignore_aliases = lambda self, data: True

    output_path.write_text(yaml.safe_dump(content))

    print(f"Successfully generated {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
