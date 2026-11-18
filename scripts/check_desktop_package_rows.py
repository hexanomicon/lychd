"""Prove committed rows survive repair and removal of one native program edition."""

from __future__ import annotations

import argparse

import psycopg

from lychd.config.settings import Settings
from lychd.system.desktop.credentials import load_credentials


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("seed", "repair", "recover"))
    phase = parser.parse_args().phase
    load_credentials(administrative=True, required=True)
    db = Settings().server.database
    if not db.password:
        msg = "Expected the installation's database credential"
        raise RuntimeError(msg)
    with psycopg.connect(
        host="127.0.0.1",
        hostaddr="127.0.0.1",
        port=db.port,
        user=db.user,
        dbname=db.database,
        password=db.password.get_secret_value(),
    ) as conn:
        if conn.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone() is None:
            msg = "Expected the provisioned application database with pgvector"
            raise RuntimeError(msg)
        if phase == "seed":
            conn.execute("CREATE SCHEMA edition_trial")
            conn.execute("CREATE TABLE edition_trial.proof (generation integer PRIMARY KEY)")
            conn.execute("INSERT INTO edition_trial.proof VALUES (1)")
            return
        expected = [(1,)] if phase == "repair" else [(1,), (2,)]
        if conn.execute("SELECT generation FROM edition_trial.proof ORDER BY generation").fetchall() != expected:
            msg = f"The {phase} trial lost a committed application-database row"
            raise RuntimeError(msg)
        if phase == "repair":
            conn.execute("INSERT INTO edition_trial.proof VALUES (2)")


if __name__ == "__main__":
    main()
