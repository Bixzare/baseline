-- Parser/config revisions of the same raw observation need separate facts, with
-- new observation times, instead of replacing the originally normalized row.
ALTER TABLE nba.player_game_versions ADD COLUMN normalization_hash text NOT NULL DEFAULT 'legacy'
 CHECK(normalization_hash='legacy' OR normalization_hash ~ '^[0-9a-f]{64}$');
ALTER TABLE nba.team_game_versions ADD COLUMN normalization_hash text NOT NULL DEFAULT 'legacy'
 CHECK(normalization_hash='legacy' OR normalization_hash ~ '^[0-9a-f]{64}$');
ALTER TABLE nba.player_game_versions DROP CONSTRAINT player_game_versions_event_id_player_id_source_check_id_key;
ALTER TABLE nba.player_game_versions ADD UNIQUE(event_id,player_id,source_check_id,normalization_hash);
ALTER TABLE nba.team_game_versions DROP CONSTRAINT team_game_versions_event_id_team_id_source_check_id_key;
ALTER TABLE nba.team_game_versions ADD UNIQUE(event_id,team_id,source_check_id,normalization_hash);
GRANT INSERT(normalization_hash) ON nba.player_game_versions,nba.team_game_versions TO baseline_runtime;
CREATE TABLE platform.outcome_versions (
 outcome_version_id uuid PRIMARY KEY,
 event_id uuid NOT NULL REFERENCES platform.events,
 observed_at timestamptz NOT NULL CHECK(isfinite(observed_at)),
 source_check_id uuid NOT NULL REFERENCES platform.source_checks,
 outcome_artifact_id uuid NOT NULL REFERENCES platform.artifacts,
 state text NOT NULL CHECK(state IN('pending','partial','final')),
 semantic_hash text NOT NULL CHECK(semantic_hash ~ '^[0-9a-f]{64}$'),
 parser_version text NOT NULL,
 config_hash text NOT NULL CHECK(config_hash ~ '^[0-9a-f]{64}$'),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(event_id,semantic_hash),
 CHECK(observed_at<=recorded_at)
);
CREATE TRIGGER outcome_source BEFORE INSERT ON platform.outcome_versions
FOR EACH ROW EXECUTE FUNCTION platform.check_observed_source();
CREATE FUNCTION platform.check_outcome_artifact() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 IF NOT EXISTS(SELECT FROM platform.artifacts a JOIN platform.source_checks s
 ON s.check_id=NEW.source_check_id WHERE a.artifact_id=NEW.outcome_artifact_id
 AND a.kind='reports' AND a.format='json' AND a.schema_version=1
 AND a.manifest->>'event_id'=NEW.event_id::text
 AND a.manifest->>'semantic_hash'=NEW.semantic_hash
 AND s.validation_summary->>'capability'='final') THEN
   RAISE EXCEPTION 'Outcome artifact/source mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER outcome_artifact BEFORE INSERT ON platform.outcome_versions
FOR EACH ROW EXECUTE FUNCTION platform.check_outcome_artifact();
CREATE INDEX outcomes_event_time ON platform.outcome_versions(event_id,observed_at,recorded_at);
CREATE TABLE platform.outcome_observations (
 event_id uuid NOT NULL REFERENCES platform.events,
 source_check_id uuid NOT NULL REFERENCES platform.source_checks,
 parser_version text NOT NULL,
 config_hash text NOT NULL,
 outcome_version_id uuid NOT NULL REFERENCES platform.outcome_versions,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(event_id,source_check_id,parser_version,config_hash)
);
CREATE FUNCTION platform.check_outcome_observation() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 IF NOT EXISTS(SELECT FROM platform.outcome_versions v JOIN platform.source_checks s
 ON s.check_id=NEW.source_check_id WHERE v.outcome_version_id=NEW.outcome_version_id
 AND v.event_id=NEW.event_id AND v.parser_version=NEW.parser_version AND v.config_hash=NEW.config_hash
 AND s.state='accepted' AND s.validation_summary->>'capability'='final') THEN
   RAISE EXCEPTION 'Outcome observation mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER outcome_observation_contract BEFORE INSERT ON platform.outcome_observations
FOR EACH ROW EXECUTE FUNCTION platform.check_outcome_observation();
GRANT SELECT ON platform.outcome_versions,platform.outcome_observations TO baseline_runtime;
GRANT INSERT(outcome_version_id,event_id,observed_at,source_check_id,outcome_artifact_id,state,
 semantic_hash,parser_version,config_hash) ON platform.outcome_versions TO baseline_runtime;
GRANT INSERT(event_id,source_check_id,parser_version,config_hash,outcome_version_id)
 ON platform.outcome_observations TO baseline_runtime;
