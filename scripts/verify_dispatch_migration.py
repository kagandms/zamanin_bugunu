"""Verify additive migrations twice on a disposable DB; source is read-only and hash checked."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import sqlite3
import tempfile
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine
from src.data.database import migrate_db


def digest(path: Path) -> str:
    """Return the byte SHA-256 of a supplied path without writing it."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(path: Path) -> dict[str, dict[str, object]]:
    """Capture every original table's columns, row count and deterministic values hash."""
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True) as connection:
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {table: table_fingerprint(connection, table) for table in tables}


def table_fingerprint(connection: sqlite3.Connection, table: str) -> dict[str, object]:
    """Fingerprint values using original columns, including tables with newly added fields."""
    columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
    return project_fingerprint(connection, table, columns)


def project_fingerprint(connection: sqlite3.Connection, table: str, columns: list[str]) -> dict[str, object]:
    """Hash sorted row values; identifiers come exclusively from SQLite schema introspection."""
    projection = ','.join('"' + column.replace('"', '""') + '"' for column in columns)
    quoted_table = table.replace('"', '""')
    rows = connection.execute(f'SELECT {projection} FROM "{quoted_table}"').fetchall()
    encoded = sorted(json.dumps(row, ensure_ascii=False, default=str) for row in rows)
    return {'columns': columns, 'rows': len(rows), 'values_sha256': hashlib.sha256('\n'.join(encoded).encode()).hexdigest()}


async def verify(source: Path) -> dict[str, object]:
    """Migrate a temporary copy twice, asserting every original value and source hash unchanged."""
    original_hash, original = digest(source), capture(source)
    passes = []
    with tempfile.TemporaryDirectory(prefix='task04-migration-') as directory:
        target = Path(directory) / 'copy.db'
        shutil.copyfile(source, target)
        engine = create_async_engine(f'sqlite+aiosqlite:///{target}')
        try:
            for pass_number in (1, 2):
                await migrate_db(engine)
                with sqlite3.connect(target.as_uri() + '?mode=ro&immutable=1', uri=True) as connection:
                    projected = {table: project_fingerprint(connection, table, record['columns'])
                        for table, record in original.items()}
                assert projected == original, 'Original values changed during migration'
                passes.append({'pass': pass_number, 'all_original_values_preserved': True, 'tables': projected})
        finally:
            await engine.dispose()
    assert digest(source) == original_hash, 'Source DB was changed'
    return {'source_sha256': original_hash, 'source_unchanged': True, 'passes': passes}


def run_cli() -> None:
    """Write a local migration evidence JSON. Raises on any failed invariant."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(asyncio.run(verify(args.source)), indent=2) + '\n')


if __name__ == '__main__':
    run_cli()
