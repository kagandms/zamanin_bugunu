from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Protocol

from src.core.logger import logger
from src.core.config import settings


class PersistenceError(RuntimeError):
    """A remote database checkpoint was not verified; publication must stop."""


class DatabaseCheckpoint(Protocol):
    """Persistence edge, replaceable by a deterministic test double."""
    async def save(self, phase: str) -> str: ...


class GitDatabaseCheckpoint:
    """Commit only the runtime DB and reject divergence without binary merge."""

    def __init__(self, root: Path) -> None:
        self.root = root

    async def _git(self, *arguments: str) -> str:
        process = await asyncio.create_subprocess_exec(
            "git", *arguments, cwd=self.root, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, _ = await process.communicate()
        if process.returncode:
            logger.error("DB persistence failed: git {} exit={}", arguments[0], process.returncode)
            raise PersistenceError(f"git {arguments[0]} failed; no automatic conflict resolution")
        return stdout.decode().strip()

    async def save(self, phase: str) -> str:
        """Verify a non-force remote checkpoint; raise before publication on failure."""
        self._require_runtime()
        if phase not in ("reservation", "result", "analytics"):
            raise ValueError("Unknown database checkpoint phase")
        await self._stage_database()
        if await self._git("diff", "--cached", "--name-only"):
            await self._git("-c", "user.name=github-actions[bot]", "-c",
                "user.email=github-actions[bot]@users.noreply.github.com", "commit", "-m",
                f"chore: database {phase} checkpoint")
        await self._git("push", "origin", "HEAD:refs/heads/main")
        head = await self._git("rev-parse", "HEAD")
        remote = await self._git("ls-remote", "origin", "refs/heads/main")
        if not remote or remote.split()[0] != head:
            raise PersistenceError("Remote main checkpoint does not match local HEAD")
        logger.info("DB checkpoint verified phase={} commit={}", phase, head)
        return head

    def _require_runtime(self) -> None:
        if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("ZAMANIN_DB_PERSISTENCE") != "git":
            raise PersistenceError("Remote persistence is enabled only by the production workflow")
        if settings.DATABASE_URL != "sqlite+aiosqlite:///bot_data.db":
            raise PersistenceError("Git checkpoints require the tracked bot_data.db database")

    async def _stage_database(self) -> None:
        staged = await self._git("diff", "--cached", "--name-only")
        if staged and set(staged.splitlines()) != {"bot_data.db"}:
            raise PersistenceError("Unrelated staged files prevent a DB checkpoint")
        changed = await self._git("diff", "--name-only")
        if set(changed.splitlines()) - {"bot_data.db"}:
            raise PersistenceError("Uncommitted tracked code prevents source SHA verification")
        await self._git("add", "--", "bot_data.db")


async def save_database(phase: str) -> str:
    """Persist DB from the workflow cwd, preserving Git's non-force conflict gate."""
    return await GitDatabaseCheckpoint(Path.cwd()).save(phase)
