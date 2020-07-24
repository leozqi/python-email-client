DROP TABLE IF EXISTS emails;

CREATE TABLE emails (
    id INTEGER PRIMARY KEY,
    subject TEXT NOT NULL,
    loaded TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created TIMESTAMP NOT NULL,
    to_address TEXT NOT NULL,
    from_address TEXT NOT NULL,
    tags TEXT
);