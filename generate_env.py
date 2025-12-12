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

# Add the common module to the path
sys.path.insert(0, str(Path(__file__).parent))

from common.config import (
    AppConfig,
    PostgresConfig,
    DockerConfig,
    ServiceConfig,
    BaseHealthCheckConfig,
    PostgresHealthCheckConfig,
    DependencyServiceHealthCheckConfig,
    VerificationServiceHealthCheckConfig,
    VerificationWorkerHealthCheckConfig,
    RabbitMQHealthCheckConfig,
    PdfServiceHealthCheckConfig,
    LatexServiceHealthCheckConfig,
)

# Markers for the managed section
MANAGED_SECTION_START = "# >>>>>> AUTO-GENERATED SECTION - DO NOT EDIT MANUALLY <<<<<<"
MANAGED_SECTION_END = "# >>>>>> END AUTO-GENERATED SECTION <<<<<<"


def generate_healthcheck_section(name: str, config: BaseHealthCheckConfig) -> list[str]:
    """Generate healthcheck configuration lines for a service."""
    prefix = name.upper().replace(" ", "_").replace("-", "_")
    return [
        "# ============================================",
        f"# Healthcheck Configuration ({name})",
        "# ============================================",
        f"{prefix}_HEALTHCHECK_INTERVAL={config.interval}",
        f"{prefix}_HEALTHCHECK_TIMEOUT={config.timeout}",
        f"{prefix}_HEALTHCHECK_RETRIES={config.retries}",
        f"{prefix}_HEALTHCHECK_START_PERIOD={config.start_period}",
        "",
    ]


def generate_managed_section() -> str:
    """Generate the content for the managed section of the .env file."""
    config = AppConfig()

    lines = [
        MANAGED_SECTION_START,
        "# This section is automatically managed by generate_env.py",
        "# Edit common/config.py to change defaults, then run: python generate_env.py",
        "",
        "# ============================================",
        "# PostgreSQL Configuration (non-sensitive)",
        "# ============================================",
        f"POSTGRES_HOST={config.postgres.host}",
        f"POSTGRES_PORT={config.postgres.port}",
        f"POSTGRES_DB={config.postgres.database}",
        "",
        "# ============================================",
        "# Docker Configuration",
        "# ============================================",
        f"VERIFICATION_TASK_NAME={config.docker.verification_task_name}",
        f"PROJECT_NAME={config.docker.project_name}",
        "",
        "# ============================================",
        "# Service Configuration",
        "# ============================================",
        f"PDF_SERVICE_BASE={config.services.pdf_service_base}",
        "",
    ]

    # Add healthcheck configurations for all services
    healthcheck_configs = [
        ("PostgreSQL", config.postgres_healthcheck),
        ("Dependency Service", config.dependency_service_healthcheck),
        ("Verification Service", config.verification_service_healthcheck),
        ("Verification Worker", config.verification_worker_healthcheck),
        ("RabbitMQ", config.rabbitmq_healthcheck),
        ("PDF Service", config.pdf_service_healthcheck),
        ("LaTeX Service", config.latex_service_healthcheck),
    ]

    for name, healthcheck_config in healthcheck_configs:
        lines.extend(generate_healthcheck_section(name, healthcheck_config))

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

    # Parse existing content
    lines = existing_content.splitlines()

    # Find the managed section markers
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
