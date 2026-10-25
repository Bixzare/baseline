-- Application foundation only. Provider-managed roles/schemas are not changed.
DO $bootstrap$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'baseline_owner') THEN
    CREATE ROLE baseline_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'baseline_runtime') THEN
    CREATE ROLE baseline_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
  END IF;
  IF EXISTS (SELECT FROM pg_roles WHERE rolname IN ('baseline_owner','baseline_runtime')
             AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)) THEN
    RAISE EXCEPTION 'Unsafe preexisting application role';
  END IF;
  IF EXISTS (SELECT FROM pg_roles WHERE rolname='baseline_owner' AND rolcanlogin)
     OR pg_has_role('baseline_runtime','baseline_owner','MEMBER') THEN
    RAISE EXCEPTION 'Unsafe application ownership or role membership';
  END IF;
  EXECUTE format('GRANT baseline_owner TO %I', current_user);
END
$bootstrap$;
CREATE SCHEMA platform AUTHORIZATION baseline_owner;
CREATE SCHEMA nba AUTHORIZATION baseline_owner;
CREATE SCHEMA api AUTHORIZATION baseline_owner;
REVOKE ALL ON SCHEMA platform, nba, api FROM PUBLIC;
GRANT USAGE ON SCHEMA platform, nba, api TO baseline_runtime;
SET LOCAL ROLE baseline_owner;
-- PUBLIC has function EXECUTE by default. Revoke globally for this owner.
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
ALTER DEFAULT PRIVILEGES REVOKE USAGE ON TYPES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA platform, nba, api REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA platform, nba, api REVOKE ALL ON SEQUENCES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES IN SCHEMA platform, nba, api REVOKE ALL ON TYPES FROM PUBLIC;
CREATE TABLE platform.schema_migrations (
  migration_id text PRIMARY KEY CHECK (migration_id ~ '^[0-9]{4}$'),
  filename text NOT NULL UNIQUE,
  sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
REVOKE ALL ON platform.schema_migrations FROM PUBLIC, baseline_runtime;
