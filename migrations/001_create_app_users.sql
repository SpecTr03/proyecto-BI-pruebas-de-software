CREATE SCHEMA IF NOT EXISTS app;

DO $$
BEGIN
    CREATE TYPE app.user_role AS ENUM (
        'Administrador',
        'Analista',
        'Investigador'
    );
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

CREATE TABLE IF NOT EXISTS app.users (
    id uuid PRIMARY KEY REFERENCES neon_auth."user"(id) ON DELETE CASCADE,
    email text NOT NULL UNIQUE,
    role app.user_role NOT NULL DEFAULT 'Analista',
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT users_email_format CHECK (position('@' IN email) > 1)
);

CREATE INDEX IF NOT EXISTS users_role_idx ON app.users (role);
CREATE INDEX IF NOT EXISTS users_active_idx ON app.users (is_active) WHERE is_active;
