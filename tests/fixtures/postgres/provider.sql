-- Disposable Postgres scaffolding only. NEVER apply to a hosted provider.
DO $$ BEGIN
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='anon') THEN CREATE ROLE anon NOLOGIN; END IF;
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='authenticated') THEN CREATE ROLE authenticated NOLOGIN; END IF;
END $$;
CREATE SCHEMA auth;
CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$
 SELECT nullif(current_setting('request.jwt.claim.sub',true),'')::uuid
$$;
GRANT USAGE ON SCHEMA auth TO PUBLIC;
CREATE SCHEMA storage;
CREATE TABLE storage.buckets(id text PRIMARY KEY, public boolean NOT NULL DEFAULT false);
CREATE TABLE storage.objects(id uuid PRIMARY KEY, bucket_id text REFERENCES storage.buckets, name text NOT NULL, UNIQUE(bucket_id,name));
ALTER TABLE storage.buckets ENABLE ROW LEVEL SECURITY;
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;
GRANT USAGE ON SCHEMA storage TO anon,authenticated;
GRANT SELECT,INSERT,UPDATE,DELETE ON storage.objects,storage.buckets TO anon,authenticated;
