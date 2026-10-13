from __future__ import annotations

import argparse
import asyncio

from src.core.logger import logger
from src.git_database import save_database


def run_cli() -> int:
    """Save workflow results even after an operational failure; return explicit status."""
    parser = argparse.ArgumentParser(description="Persist the runtime DB without publishing")
    parser.add_argument("--phase", choices=("result", "analytics"), required=True)
    arguments = parser.parse_args()
    try:
        asyncio.run(save_database(arguments.phase))
        return 0
    except Exception as error:
        logger.error("DB checkpoint failed ({})", type(error).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(run_cli())
