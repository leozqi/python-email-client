SCHEMA = '''DROP TABLE IF EXISTS emails;
DROP TABLE IF EXISTS files;

CREATE TABLE emails (
    id INTEGER PRIMARY KEY,
    subject TEXT NOT NULL,
    loaded TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created TIMESTAMP NOT NULL,
    to_address TEXT NOT NULL,
    from_address TEXT NOT NULL,
    read INTEGER NOT NULL,
    tags TEXT
);

CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    email_lk INTEGER NOT NULL,
    FOREIGN KEY (email_lk) REFERENCES emails (id)
);

CREATE TABLE profiles (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    password TEXT NOT NULL,
    imap TEXT NOT NULL,
    port INTEGER NOT NULL DEFAULT 993
);
'''

VERSION='0.0.7'