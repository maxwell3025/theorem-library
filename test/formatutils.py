"""
Utilities for formatting HTTP responses in tests.
"""

import json
import httpx
import logging


def pretty_print_response(response: httpx.Response, logger: logging.Logger) -> None:
    """
    Pretty-print an HTTP response including status, headers, and body.
    
    Args:
        response: The httpx.Response object to print.
        logger: The logger instance to use for output.
    """
    logger.info(f"HTTP {response.status_code} {response.reason_phrase}")
    
    # Print headers
    logger.info("Headers:")
    for key, value in response.headers.items():
        logger.info(f"  {key}: {value}")
    
    # Print body
    logger.info("Body:")
    try:
        # Try to parse and pretty-print JSON
        body_json = response.json()
        logger.info(json.dumps(body_json, indent=2))
    except (json.JSONDecodeError, ValueError):
        # Fall back to raw text if not JSON
        logger.info(response.text)
