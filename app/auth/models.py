CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    github_id       VARCHAR(50) UNIQUE NOT NULL,
    username        VARCHAR(100) NOT NULL,
    email           VARCHAR(255),
    avatar_url      VARCHAR(500),
    role            VARCHAR(20) NOT NULL DEFAULT 'analyst',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login      TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id              SERIAL PRIMARY KEY,
    user_id         INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token           VARCHAR(500) UNIQUE NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS request_logs (
    id              SERIAL PRIMARY KEY,
    user_id         INT REFERENCES users(id) ON DELETE SET NULL,
    method          VARCHAR(10) NOT NULL,
    path            VARCHAR(500) NOT NULL,
    status_code     INT,
    duration_ms     FLOAT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token ON refresh_tokens(token);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_request_logs_user ON request_logs(user_id);
"""