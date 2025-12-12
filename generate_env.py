#!/usr/bin/env python3
"""
Generate a .env file from common/config.py default values.

This script reads the configuration classes in common/config.py and updates
a managed section in the .env file. Content outside the managed section is
preserved. If the managed section doesn't exist, it's appended to the file.

Usage:
    python generate_env.py [--output .env]
"""

import argparse
import sys
from pathlib import Path

from common.config import AppConfig

MANAGED_SECTION_START = "# >>>>>> AUTO-GENERATED SECTION - DO NOT EDIT MANUALLY <<<<<<"
MANAGED_SECTION_END = "# >>>>>> END AUTO-GENERATED SECTION <<<<<<"


def path_to_env_var(path: list[str]) -> str:
    """Convert a list of keys to an environment variable name."""
    return "_".join(part.upper() for part in path)


def get_env_entries(data, prefix: list[str] = []) -> list[str]:
    """Recursively traverse dict structure and generate env var lines."""
    env_lines = []

    for key, value in data.items():
        if isinstance(value, dict):
            env_lines.extend(get_env_entries(value, prefix + [key]))
        elif isinstance(value, list):
            env_lines.extend(
                get_env_entries(
                    {
                        list_index: list_entry
                        for list_index, list_entry in enumerate(value)
                    },
                    prefix + [key],
                )
            )
        else:
            env_lines.append(f"{path_to_env_var(prefix + [key])}={value}")

    return env_lines


def generate_managed_section() -> str:
    """Generate the content for the managed section of the .env file."""
    config = AppConfig()

    lines = [
        MANAGED_SECTION_START,
        "# This section is automatically managed by generate_env.py",
        "# Edit common/config.py to change defaults, then run: python generate_env.py",
        "",
    ]

    # Get the raw dict representation from pydantic
    config_dict = config.model_dump()

    # Dump the entire config structure
    lines.extend(get_env_entries(config_dict))

    # Remove trailing empty line and add end marker
    if lines and lines[-1] == "":
        lines.pop()
    lines.append(MANAGED_SECTION_END)

    return "\n".join(lines)


def update_env_file(existing_content: str) -> str:
    """
    Update the managed section in the .env file content.

    Args:
        existing_content: The existing .env file content

    Returns:
        The updated .env file content with the managed section.
    """
    managed_content = generate_managed_section()

    lines = existing_content.splitlines()

    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        if line == MANAGED_SECTION_START:
            if start_idx is not None:
                raise ValueError("Multiple managed section start markers found.")
            start_idx = i
        if line == MANAGED_SECTION_END:
            if end_idx is not None:
                raise ValueError("Multiple managed section end markers found.")
            end_idx = i

    if start_idx is not None and end_idx is not None and start_idx < end_idx:
        new_lines = (
            lines[:start_idx] + managed_content.splitlines() + lines[end_idx + 1 :]
        )
        return "\n".join(new_lines)
    else:
        return existing_content + "\n\n" + managed_content


def main():
    parser = argparse.ArgumentParser(
        description="Generate/update the managed section in .env from common/config.py"
    )

    parser.add_argument(
        "--output",
        "-o",
        default=".env",
        help="Output file path (default: .env)",
    )

    parser.add_argument(
        "--input",
        "-i",
        default=".env",
        help="Input file path (default: .env)",
    )

    args = parser.parse_args()
    output_path = Path(args.output)
    input_path = Path(args.input)

    existing_content = input_path.read_text() if input_path.exists() else ""

    new_content = update_env_file(existing_content)
    output_path.write_text(new_content)

    return 0


if __name__ == "__main__":
    sys.exit(main())
