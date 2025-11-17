-- pre-registry--
CREATE TABLE IF NOT EXISTS registry (
    voter_id TEXT PRIMARY KEY,
    full_name TEXT
);

-- votes
CREATE TABLE IF NOT EXISTS votes (
    voter_id TEXT PRIMARY KEY,
    candidate_id INTEGER,
    timestamp TEXT,
    FOREIGN KEY(candidate_id) REFERENCES candidates(id)

);

-- candidates
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voter_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL
);
