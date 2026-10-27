CREATE TABLE platform.alert_events (
 alert_event_id uuid PRIMARY KEY,
 alert_key text NOT NULL CHECK(length(alert_key) BETWEEN 1 AND 256 AND alert_key ~ '^[a-z0-9:_-]+$'),
 severity text NOT NULL CHECK(severity IN('info','warning','critical')),
 state text NOT NULL CHECK(state IN('open','acknowledged','resolved')),
 reason_code text NOT NULL CHECK(reason_code ~ '^[a-z][a-z0-9_-]{0,127}$'),
 observed_at timestamptz NOT NULL CHECK(isfinite(observed_at)),
 run_id uuid REFERENCES platform.runs,
 report_id uuid REFERENCES platform.evaluation_reports,
 details jsonb NOT NULL CHECK(platform.safe_summary(details)),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(observed_at<=recorded_at)
);
CREATE INDEX alert_key_time ON platform.alert_events(alert_key,recorded_at);
GRANT SELECT ON platform.alert_events TO baseline_runtime;
GRANT INSERT(alert_event_id,alert_key,severity,state,reason_code,observed_at,run_id,report_id,details)
 ON platform.alert_events TO baseline_runtime;
