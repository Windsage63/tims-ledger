PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE company_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    company_name TEXT NOT NULL,
    street_address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    zip TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

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
) VALUES (
    1,
    'Your Company Name',
    'Your Street Address',
    'Your City',
    'YS',
    'Your ZIP Code',
    'you@example.com',
    'Your Phone Number',
    datetime('now'),
    datetime('now')
);

COMMIT;
