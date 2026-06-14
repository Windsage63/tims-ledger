from __future__ import annotations

import sqlite3

from pydantic import BaseModel, ConfigDict, field_validator

from .date_utils import utc_now


DEFAULT_COMPANY_PROFILE = {
    "id": 1,
    "company_name": "Your Company Name",
    "street_address": "Your Street Address",
    "city": "Your City",
    "state": "Your State",
    "zip": "Your ZIP Code",
    "email": "you@example.com",
    "phone": "Your Phone Number",
    "created_at": "",
    "updated_at": "",
}


class CompanyProfileWrite(BaseModel):
    company_name: str
    street_address: str
    city: str
    state: str
    zip: str
    email: str
    phone: str

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator(
        "company_name",
        "street_address",
        "city",
        "state",
        "zip",
        "email",
        "phone",
    )
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value:
            raise ValueError("This field is required.")
        return value

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str) -> str:
        normalized = value.upper()
        if len(normalized) > 2:
            normalized = normalized[:2]
        return normalized

    def to_record(self) -> dict[str, str]:
        return self.model_dump()


def row_to_company_profile(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "company_name": row["company_name"],
        "street_address": row["street_address"],
        "city": row["city"],
        "state": row["state"],
        "zip": row["zip"],
        "email": row["email"],
        "phone": row["phone"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def default_company_profile() -> dict[str, object]:
    return dict(DEFAULT_COMPANY_PROFILE)


def fetch_company_profile(connection: sqlite3.Connection) -> dict[str, object]:
    try:
        row = connection.execute(
            """
            SELECT
                id,
                company_name,
                street_address,
                city,
                state,
                zip,
                email,
                phone,
                created_at,
                updated_at
            FROM company_profile
            WHERE id = 1
            """
        ).fetchone()
    except sqlite3.OperationalError:
        return default_company_profile()

    if row is None:
        return default_company_profile()
    return row_to_company_profile(row)


def upsert_company_profile(
    connection: sqlite3.Connection,
    payload: CompanyProfileWrite,
) -> dict[str, object]:
    record = payload.to_record()
    existing = fetch_company_profile(connection)
    timestamp = utc_now()
    created_at = str(existing.get("created_at") or timestamp)

    connection.execute(
        """
        INSERT INTO company_profile (
            id,
            company_name,
            street_address,
            city,
            state,
            zip,
            email,
            phone,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            company_name = excluded.company_name,
            street_address = excluded.street_address,
            city = excluded.city,
            state = excluded.state,
            zip = excluded.zip,
            email = excluded.email,
            phone = excluded.phone,
            updated_at = excluded.updated_at
        """,
        (
            1,
            record["company_name"],
            record["street_address"],
            record["city"],
            record["state"],
            record["zip"],
            record["email"],
            record["phone"],
            created_at,
            timestamp,
        ),
    )
    connection.commit()
    return fetch_company_profile(connection)
