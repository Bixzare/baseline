CREATE TABLE platform.evaluation_reports (
 report_id uuid PRIMARY KEY,
 domain text NOT NULL,
 report_kind text NOT NULL CHECK(report_kind IN('live','rehearsal','replay')),
 policy_version text NOT NULL,
 period_start timestamptz NOT NULL CHECK(isfinite(period_start)),
 period_end timestamptz NOT NULL CHECK(isfinite(period_end) AND period_end>period_start),
 report_cutoff timestamptz NOT NULL CHECK(isfinite(report_cutoff) AND report_cutoff>=period_end),
 predictions_manifest_id uuid NOT NULL REFERENCES platform.artifacts,
 outcomes_manifest_id uuid NOT NULL REFERENCES platform.artifacts,
 report_artifact_id uuid NOT NULL REFERENCES platform.artifacts,
 input_hash text NOT NULL CHECK(input_hash ~ '^[0-9a-f]{64}$'),
 summary jsonb NOT NULL CHECK(platform.safe_summary(summary)),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(report_cutoff<=created_at),
 UNIQUE(domain,report_kind,input_hash)
);
CREATE FUNCTION platform.check_evaluation_artifacts() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 IF (SELECT count(*) FROM platform.artifacts a WHERE a.artifact_id IN
 (NEW.predictions_manifest_id,NEW.outcomes_manifest_id,NEW.report_artifact_id)
 AND a.kind='reports' AND a.format='json' AND a.schema_version=1)<>
 (SELECT count(DISTINCT x) FROM unnest(ARRAY[NEW.predictions_manifest_id,
 NEW.outcomes_manifest_id,NEW.report_artifact_id])x) THEN
   RAISE EXCEPTION 'Evaluation artifact contract'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER evaluation_artifacts BEFORE INSERT ON platform.evaluation_reports
 FOR EACH ROW EXECUTE FUNCTION platform.check_evaluation_artifacts();
GRANT SELECT ON platform.evaluation_reports TO baseline_runtime;
GRANT INSERT(report_id,domain,report_kind,policy_version,period_start,period_end,report_cutoff,
 predictions_manifest_id,outcomes_manifest_id,report_artifact_id,input_hash,summary)
 ON platform.evaluation_reports TO baseline_runtime;
