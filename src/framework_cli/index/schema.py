SCHEMA_VERSION = 1
SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, root_path TEXT NOT NULL, profile TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS applications (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, path TEXT NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS adapters (id TEXT PRIMARY KEY, version TEXT NOT NULL, capabilities TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY, category TEXT NOT NULL, path TEXT, line INTEGER, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS generated_artifacts (path TEXT PRIMARY KEY, source TEXT NOT NULL, version TEXT NOT NULL, checksum TEXT NOT NULL, state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS learn_sessions (id TEXT PRIMARY KEY, parent_session_id TEXT, status TEXT NOT NULL, local_date TEXT NOT NULL, started_at TEXT, ended_at TEXT, agent TEXT, host TEXT, branch TEXT, worktree TEXT, commit_base TEXT, coverage TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS learn_events (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, type TEXT NOT NULL, observed_at TEXT NOT NULL, fingerprint TEXT NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS learn_lessons (id TEXT NOT NULL, revision INTEGER NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL, fingerprint TEXT NOT NULL DEFAULT '', PRIMARY KEY (id, revision));
CREATE TABLE IF NOT EXISTS handoffs (id TEXT PRIMARY KEY, source_session_id TEXT NOT NULL, target TEXT NOT NULL, checksum TEXT NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS quiz_questions (id TEXT NOT NULL, revision INTEGER NOT NULL, status TEXT NOT NULL, fingerprint TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY (id, revision));
CREATE TABLE IF NOT EXISTS quiz_jobs (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, command TEXT NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS quiz_attempts (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, question_revision TEXT NOT NULL, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS symbols (id TEXT PRIMARY KEY, path TEXT NOT NULL, name TEXT NOT NULL, kind TEXT NOT NULL, line INTEGER, end_line INTEGER, signature TEXT NOT NULL, fingerprint TEXT NOT NULL, data TEXT NOT NULL);
"""
