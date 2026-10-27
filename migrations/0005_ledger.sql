CREATE TABLE platform.models (
 model_id uuid PRIMARY KEY,
 domain text NOT NULL CHECK(length(domain) BETWEEN 1 AND 64),
 family text NOT NULL CHECK(length(family) BETWEEN 1 AND 128),
 target text NOT NULL CHECK(length(target) BETWEEN 1 AND 64),
 version text NOT NULL CHECK(length(version) BETWEEN 1 AND 64),
 code_version text NOT NULL CHECK(length(code_version) BETWEEN 1 AND 128),
 config_hash text NOT NULL CHECK(config_hash ~ '^[0-9a-f]{64}$'),
 artifact_id uuid REFERENCES platform.artifacts,
 training_cutoff timestamptz CHECK(isfinite(training_cutoff)),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(domain,family,target,version)
);
CREATE TABLE platform.model_bundles (
 bundle_id uuid PRIMARY KEY,
 domain text NOT NULL,
 components jsonb NOT NULL CHECK(platform.safe_summary(components) AND components<>'{}'::jsonb),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 config_hash text NOT NULL CHECK(config_hash ~ '^[0-9a-f]{64}$')
);
CREATE FUNCTION platform.check_bundle() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ DECLARE item record; BEGIN
 FOR item IN SELECT * FROM jsonb_each_text(NEW.components) LOOP
   IF item.key='' OR NOT EXISTS (SELECT FROM platform.models m
     WHERE m.model_id=item.value::uuid AND m.domain=NEW.domain AND m.target=item.key) THEN
     RAISE EXCEPTION 'Bundle component domain or target mismatch' USING ERRCODE='23514';
   END IF;
 END LOOP;
 RETURN NEW;
END $$;
CREATE TRIGGER bundle_contract BEFORE INSERT ON platform.model_bundles FOR EACH ROW EXECUTE FUNCTION platform.check_bundle();
CREATE TABLE platform.active_bundles (
 domain text NOT NULL,
 family text NOT NULL,
 bundle_id uuid NOT NULL REFERENCES platform.model_bundles,
 generation bigint NOT NULL CHECK(generation>0),
 PRIMARY KEY(domain,family)
);
CREATE FUNCTION platform.check_active_bundle() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 IF NOT EXISTS (SELECT FROM platform.model_bundles b WHERE b.bundle_id=NEW.bundle_id AND b.domain=NEW.domain)
 OR EXISTS (SELECT FROM platform.model_bundles b CROSS JOIN LATERAL jsonb_each_text(b.components) c
   JOIN platform.models m ON m.model_id=c.value::uuid WHERE b.bundle_id=NEW.bundle_id AND m.family<>NEW.family) THEN
   RAISE EXCEPTION 'Active bundle family/domain mismatch' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER active_bundle_contract BEFORE INSERT OR UPDATE ON platform.active_bundles FOR EACH ROW EXECUTE FUNCTION platform.check_active_bundle();
CREATE TABLE platform.forecast_batches (
 batch_id uuid PRIMARY KEY,
 run_id uuid NOT NULL REFERENCES platform.runs,
 event_id uuid NOT NULL REFERENCES platform.events,
 bundle_id uuid NOT NULL REFERENCES platform.model_bundles,
 feature_artifact_id uuid NOT NULL REFERENCES platform.artifacts,
 cohort_artifact_id uuid NOT NULL REFERENCES platform.artifacts,
 schedule_observation_id uuid NOT NULL,
 generated_at timestamptz NOT NULL CHECK(isfinite(generated_at)),
 feature_cutoff timestamptz NOT NULL CHECK(isfinite(feature_cutoff)),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 scheduled_start timestamptz NOT NULL CHECK(isfinite(scheduled_start)),
 publication_policy_version text NOT NULL CHECK(length(publication_policy_version) BETWEEN 1 AND 64),
 content_hash text NOT NULL CHECK(content_hash ~ '^[0-9a-f]{64}$'),
 insertion_transaction_id text NOT NULL DEFAULT pg_current_xact_id()::text,
 CHECK(feature_cutoff<=generated_at AND generated_at<=recorded_at),
 FOREIGN KEY(schedule_observation_id,event_id) REFERENCES platform.event_observations(observation_id,event_id),
 UNIQUE(batch_id,event_id)
);
CREATE FUNCTION platform.check_batch() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 IF NOT EXISTS (SELECT FROM platform.events e JOIN platform.model_bundles b
   ON b.domain=e.domain WHERE e.event_id=NEW.event_id AND b.bundle_id=NEW.bundle_id)
 OR (SELECT count(*) FROM platform.artifacts a WHERE a.artifact_id IN
   (NEW.feature_artifact_id,NEW.cohort_artifact_id) AND a.kind='features') <
   (CASE WHEN NEW.feature_artifact_id=NEW.cohort_artifact_id THEN 1 ELSE 2 END) THEN
   RAISE EXCEPTION 'Batch domain or feature artifact mismatch' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER batch_contract BEFORE INSERT ON platform.forecast_batches FOR EACH ROW EXECUTE FUNCTION platform.check_batch();
CREATE TABLE platform.official_slots (
 event_id uuid NOT NULL,
 subject_type text NOT NULL CHECK(length(subject_type) BETWEEN 1 AND 64),
 subject_id text NOT NULL CHECK(length(subject_id) BETWEEN 1 AND 256),
 target text NOT NULL CHECK(length(target) BETWEEN 1 AND 64),
 batch_id uuid NOT NULL,
 decision_kind text NOT NULL CHECK(decision_kind IN ('prediction','abstention')),
 role text GENERATED ALWAYS AS ('official'::text) STORED,
 prediction_batch_id uuid GENERATED ALWAYS AS (CASE WHEN decision_kind='prediction' THEN batch_id END) STORED,
 abstention_batch_id uuid GENERATED ALWAYS AS (CASE WHEN decision_kind='abstention' THEN batch_id END) STORED,
 PRIMARY KEY(event_id,subject_type,subject_id,target),
 UNIQUE(batch_id,subject_type,subject_id,target,decision_kind),
 FOREIGN KEY(batch_id,event_id) REFERENCES platform.forecast_batches(batch_id,event_id)
);
CREATE TABLE platform.predictions (
 prediction_id uuid PRIMARY KEY,
 batch_id uuid NOT NULL REFERENCES platform.forecast_batches,
 subject_type text NOT NULL CHECK(length(subject_type) BETWEEN 1 AND 64),
 subject_id text NOT NULL CHECK(length(subject_id) BETWEEN 1 AND 256),
 target text NOT NULL CHECK(length(target) BETWEEN 1 AND 64),
 role text NOT NULL CHECK(role='official'),
 model_id uuid NOT NULL REFERENCES platform.models,
 value double precision NOT NULL CHECK(value>'-Infinity'::float8 AND value<'Infinity'::float8),
 unit text NOT NULL CHECK(length(unit) BETWEEN 1 AND 64),
 decision_kind text GENERATED ALWAYS AS ('prediction'::text) STORED,
 UNIQUE(batch_id,subject_type,subject_id,target,role),
 UNIQUE(prediction_id,batch_id),
 FOREIGN KEY(batch_id,subject_type,subject_id,target,decision_kind)
   REFERENCES platform.official_slots(batch_id,subject_type,subject_id,target,decision_kind)
   DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE platform.abstentions (
 abstention_id uuid PRIMARY KEY,
 batch_id uuid NOT NULL REFERENCES platform.forecast_batches,
 subject_type text NOT NULL CHECK(length(subject_type) BETWEEN 1 AND 64),
 subject_id text NOT NULL CHECK(length(subject_id) BETWEEN 1 AND 256),
 target text NOT NULL CHECK(length(target) BETWEEN 1 AND 64),
 role text NOT NULL CHECK(role='official'),
 reason_code text NOT NULL CHECK(reason_code ~ '^[a-z][a-z0-9_-]{0,127}$'),
 details jsonb NOT NULL CHECK(platform.safe_summary(details)),
 decision_kind text GENERATED ALWAYS AS ('abstention'::text) STORED,
 UNIQUE(batch_id,subject_type,subject_id,target,role),
 FOREIGN KEY(batch_id,subject_type,subject_id,target,decision_kind)
   REFERENCES platform.official_slots(batch_id,subject_type,subject_id,target,decision_kind)
   DEFERRABLE INITIALLY DEFERRED
);
-- Circular deferred foreign keys enforce a matching child without snapshot-
-- sensitive COUNT triggers. Either insertion order works inside one transaction.
ALTER TABLE platform.official_slots ADD CONSTRAINT official_prediction_child
 FOREIGN KEY(prediction_batch_id,subject_type,subject_id,target,role)
 REFERENCES platform.predictions(batch_id,subject_type,subject_id,target,role)
 DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE platform.official_slots ADD CONSTRAINT official_abstention_child
 FOREIGN KEY(abstention_batch_id,subject_type,subject_id,target,role)
 REFERENCES platform.abstentions(batch_id,subject_type,subject_id,target,role)
 DEFERRABLE INITIALLY DEFERRED;
CREATE FUNCTION platform.check_prediction_model() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 IF NOT EXISTS (SELECT FROM platform.forecast_batches f JOIN platform.model_bundles b USING(bundle_id)
   WHERE f.batch_id=NEW.batch_id AND b.components->>NEW.target=NEW.model_id::text) THEN
   RAISE EXCEPTION 'Prediction model must match bundle target' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER prediction_model_contract BEFORE INSERT ON platform.predictions FOR EACH ROW EXECUTE FUNCTION platform.check_prediction_model();
CREATE FUNCTION platform.check_abstention_target() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 IF NOT EXISTS (SELECT FROM platform.forecast_batches f JOIN platform.model_bundles b USING(bundle_id)
    WHERE f.batch_id=NEW.batch_id AND b.components ? NEW.target) THEN
   RAISE EXCEPTION 'Abstention target must belong to bundle' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER abstention_target_contract BEFORE INSERT ON platform.abstentions FOR EACH ROW EXECUTE FUNCTION platform.check_abstention_target();
CREATE TABLE platform.publication_receipts (
 receipt_id uuid PRIMARY KEY,
 batch_id uuid NOT NULL UNIQUE REFERENCES platform.forecast_batches,
 observed_committed_at timestamptz NOT NULL DEFAULT clock_timestamp() CHECK(isfinite(observed_committed_at)),
 confirming_transaction_id text NOT NULL DEFAULT pg_current_xact_id()::text,
 policy_version text NOT NULL
);
CREATE FUNCTION platform.check_receipt() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 IF NOT EXISTS (SELECT FROM platform.forecast_batches b WHERE b.batch_id=NEW.batch_id
    AND b.insertion_transaction_id<>NEW.confirming_transaction_id
    AND b.recorded_at<=NEW.observed_committed_at AND b.publication_policy_version=NEW.policy_version) THEN
   RAISE EXCEPTION 'Receipt identity, time or policy mismatch' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER receipt_contract BEFORE INSERT ON platform.publication_receipts FOR EACH ROW EXECUTE FUNCTION platform.check_receipt();
CREATE TABLE platform.prediction_events (
 prediction_event_id uuid PRIMARY KEY,
 batch_id uuid NOT NULL REFERENCES platform.forecast_batches,
 prediction_id uuid,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 kind text NOT NULL CHECK(kind ~ '^[a-z][a-z0-9_-]{0,63}$'),
 reason_code text NOT NULL CHECK(reason_code ~ '^[a-z][a-z0-9_-]{0,127}$'),
 source_check_id uuid REFERENCES platform.source_checks,
 FOREIGN KEY(prediction_id,batch_id) REFERENCES platform.predictions(prediction_id,batch_id)
);
GRANT SELECT ON platform.models,platform.model_bundles,platform.active_bundles,
 platform.forecast_batches,platform.predictions,platform.abstentions,platform.official_slots,
 platform.publication_receipts,platform.prediction_events TO baseline_runtime;

RESET ROLE;
DO $$ BEGIN
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='baseline_publisher') THEN
   CREATE ROLE baseline_publisher NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
 END IF;
 IF EXISTS (SELECT FROM pg_roles WHERE rolname='baseline_publisher' AND
   (rolcanlogin OR rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
 OR pg_has_role('baseline_publisher','baseline_owner','MEMBER')
 OR pg_has_role('baseline_runtime','baseline_publisher','MEMBER') THEN
   RAISE EXCEPTION 'Unsafe publication-function owner';
 END IF;
END $$;
SET LOCAL ROLE baseline_owner;
GRANT USAGE ON SCHEMA platform,nba TO baseline_publisher;
GRANT SELECT ON platform.runs,platform.events,platform.event_observations,platform.artifacts,
 platform.source_checks,platform.models,platform.model_bundles,platform.active_bundles,
 platform.forecast_batches,platform.predictions,platform.abstentions,platform.official_slots,
 platform.publication_receipts,platform.prediction_events TO baseline_publisher;
GRANT INSERT ON platform.forecast_batches,platform.predictions,platform.abstentions,
 platform.official_slots,platform.publication_receipts,platform.prediction_events TO baseline_publisher;
GRANT EXECUTE ON FUNCTION platform.safe_summary(jsonb) TO baseline_publisher;
-- No publication functions or runtime execute grants exist in this migration.
