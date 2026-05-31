from __future__ import annotations

import sqlite3

from .payments_db import load_payments_db


def load_full_ledger_db(connection: sqlite3.Connection) -> int:
    return load_payments_db(connection)
