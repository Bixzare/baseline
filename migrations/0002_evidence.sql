CREATE FUNCTION platform.safe_summary(value jsonb) RETURNS boolean
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog AS $$
 SELECT jsonb_typeof(value)='object' AND octet_length(value::text)<=16384
   AND value::text !~* '"(password|secret|token|access_token|refresh_token|authorization|cookie|set-cookie|api_key|apikey|dsn|credentials)"\s*:'
   AND value::text !~* '(Bearer[ ]|postgres(ql)?://|sb_secret_|[?&](token|key|signature|access_token)=|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.)'
$$;
GRANT EXECUTE ON FUNCTION platform.safe_summary(jsonb) TO baseline_runtime;

CREATE TABLE platform.runs (
 run_id uuid PRIMARY KEY,
 operation text NOT NULL CHECK (operation ~ '^[a-z][a-z0-9_-]{0,63}$'),
 domain text NOT NULL CHECK (domain ~ '^[a-z][a-z0-9_-]{0,63}$'),
 environment text NOT NULL CHECK (environment IN ('rehearsal','production')),
 code_version text NOT NULL CHECK (length(code_version) BETWEEN 1 AND 128),
 config_hash text NOT NULL CHECK (config_hash ~ '^[0-9a-f]{64}$'),
 started_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE platform.run_events (
 run_event_id uuid PRIMARY KEY,
 run_id uuid NOT NULL REFERENCES platform.runs,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 state text NOT NULL CHECK (state IN ('started','succeeded','failed','incomplete')),
 reason_code text CHECK (reason_code ~ '^[a-z][a-z0-9_-]{0,127}$'),
 details jsonb NOT NULL CHECK (platform.safe_summary(details)),
 CHECK (state='started' OR (details ? 'counts' AND details ? 'duration_ms')),
 CHECK (state='started' OR (jsonb_typeof(details->'counts')='object'
     AND jsonb_typeof(details->'duration_ms')='number' AND (details->>'duration_ms')::numeric>=0)),
 CHECK (state NOT IN ('failed','incomplete') OR reason_code IS NOT NULL)
);
CREATE INDEX run_events_run_id ON platform.run_events(run_id);
CREATE TABLE platform.artifacts (
 artifact_id uuid PRIMARY KEY,
 sha256 text NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
 kind text NOT NULL CHECK (kind IN ('raw','history','features','models','reports')),
 format text NOT NULL CHECK (format ~ '^[a-z0-9_-]{1,32}$'),
 schema_version integer NOT NULL CHECK (schema_version>0),
 byte_count bigint NOT NULL CHECK (byte_count>=0),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 storage_uri text NOT NULL UNIQUE CHECK (
   storage_uri ~ '^supabase://[a-z0-9-]+/[a-z0-9-]+/(raw|history|features|models|reports)/[0-9a-f]{2}/[0-9a-f]{64}$'
   AND split_part(storage_uri,'/',5)=kind
   AND right(storage_uri,64)=sha256
   AND split_part(storage_uri,'/',6)=left(sha256,2)
 ),
 manifest jsonb NOT NULL CHECK (platform.safe_summary(manifest)),
 UNIQUE(artifact_id,kind)
);
CREATE TABLE platform.source_checks (
 check_id uuid PRIMARY KEY,
 run_id uuid NOT NULL REFERENCES platform.runs,
 source_id text NOT NULL CHECK (length(source_id) BETWEEN 1 AND 256 AND source_id !~ '[?@]'),
 adapter_version text NOT NULL CHECK (length(adapter_version) BETWEEN 1 AND 128),
 requested_at timestamptz NOT NULL,
 received_at timestamptz,
 validated_at timestamptz,
 source_published_at timestamptz,
 raw_artifact_id uuid,
 raw_kind text GENERATED ALWAYS AS ('raw'::text) STORED,
 http_status integer CHECK (http_status BETWEEN 100 AND 599),
 record_count bigint CHECK (record_count>=0),
 state text NOT NULL CHECK (state IN ('accepted','invalid','transport_failure','storage_failure','unverified')),
 validation_summary jsonb NOT NULL CHECK (platform.safe_summary(validation_summary)),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(raw_artifact_id,raw_kind) REFERENCES platform.artifacts(artifact_id,kind),
 CHECK (isfinite(requested_at) AND requested_at<=recorded_at),
 CHECK (received_at IS NULL OR (isfinite(received_at) AND requested_at<=received_at AND received_at<=recorded_at)),
 CHECK (validated_at IS NULL OR (isfinite(validated_at) AND received_at IS NOT NULL AND received_at<=validated_at AND validated_at<=recorded_at)),
 CHECK (source_published_at IS NULL OR isfinite(source_published_at)),
 CHECK (received_at IS NOT NULL OR (http_status IS NULL AND raw_artifact_id IS NULL AND record_count IS NULL)),
 CHECK (state!='accepted' OR (received_at IS NOT NULL AND validated_at IS NOT NULL
     AND raw_artifact_id IS NOT NULL AND record_count IS NOT NULL AND (http_status IS NULL OR http_status BETWEEN 200 AND 299))),
 CHECK (state='accepted' OR validated_at IS NULL),
 CHECK (state!='transport_failure' OR received_at IS NULL)
);
CREATE INDEX source_checks_run_id ON platform.source_checks(run_id);
CREATE INDEX source_checks_raw_artifact_id ON platform.source_checks(raw_artifact_id);

REVOKE ALL ON platform.runs,platform.run_events,platform.artifacts,platform.source_checks FROM PUBLIC;
GRANT SELECT ON platform.runs,platform.run_events,platform.artifacts,platform.source_checks TO baseline_runtime;
-- Database times cannot be supplied by the runtime writer.
GRANT INSERT(run_id,operation,domain,environment,code_version,config_hash) ON platform.runs TO baseline_runtime;
GRANT INSERT(run_event_id,run_id,state,reason_code,details) ON platform.run_events TO baseline_runtime;
GRANT INSERT(artifact_id,sha256,kind,format,schema_version,byte_count,storage_uri,manifest) ON platform.artifacts TO baseline_runtime;
GRANT INSERT(check_id,run_id,source_id,adapter_version,requested_at,received_at,validated_at,source_published_at,raw_artifact_id,http_status,record_count,state,validation_summary) ON platform.source_checks TO baseline_runtime;
