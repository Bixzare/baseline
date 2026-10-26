CREATE TABLE platform.events (
 event_id uuid PRIMARY KEY,
 domain text NOT NULL CHECK (domain ~ '^[a-z][a-z0-9_-]{0,63}$'),
 source_event_id text NOT NULL CHECK (length(source_event_id) BETWEEN 1 AND 128),
 competition text NOT NULL CHECK (length(competition) BETWEEN 1 AND 64),
 season text NOT NULL CHECK (length(season) BETWEEN 1 AND 32),
 occurrence_no integer NOT NULL CHECK (occurrence_no>0),
 predecessor_event_id uuid REFERENCES platform.events,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(domain,source_event_id,occurrence_no),
 CHECK(predecessor_event_id IS NULL OR predecessor_event_id<>event_id)
);
CREATE FUNCTION platform.check_predecessor() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 IF NEW.predecessor_event_id IS NOT NULL AND NOT EXISTS (
   SELECT FROM platform.events p WHERE p.event_id=NEW.predecessor_event_id
   AND p.domain=NEW.domain AND p.source_event_id=NEW.source_event_id
   AND p.occurrence_no<NEW.occurrence_no) THEN
   RAISE EXCEPTION 'Invalid occurrence predecessor' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER event_predecessor BEFORE INSERT ON platform.events FOR EACH ROW EXECUTE FUNCTION platform.check_predecessor();
CREATE TABLE platform.event_observations (
 observation_id uuid PRIMARY KEY,
 event_id uuid NOT NULL REFERENCES platform.events,
 source_check_id uuid NOT NULL REFERENCES platform.source_checks,
 observed_at timestamptz NOT NULL CHECK (isfinite(observed_at)),
 scheduled_start timestamptz CHECK (isfinite(scheduled_start)),
 actual_start timestamptz CHECK (isfinite(actual_start)),
 state text NOT NULL CHECK (state IN ('scheduled','in_progress','final','postponed','cancelled','unknown')),
 details jsonb NOT NULL CHECK (platform.safe_summary(details)),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(observed_at<=recorded_at),
 UNIQUE(event_id,source_check_id),
 UNIQUE(observation_id,event_id)
);
CREATE INDEX event_observations_event ON platform.event_observations(event_id,observed_at);
CREATE TABLE nba.teams (
 team_id text PRIMARY KEY CHECK(team_id ~ '^[1-9][0-9]*$'),
 display_name text,
 abbreviation text
);
CREATE TABLE nba.players (
 player_id text PRIMARY KEY CHECK(player_id ~ '^[1-9][0-9]*$'),
 display_name text
);
CREATE TABLE nba.games (
 event_id uuid PRIMARY KEY REFERENCES platform.events,
 home_team_id text NOT NULL REFERENCES nba.teams,
 away_team_id text NOT NULL REFERENCES nba.teams,
 source_season_type text NOT NULL,
 CHECK(home_team_id<>away_team_id)
);
CREATE TABLE nba.roster_snapshots (
 roster_id uuid PRIMARY KEY,
 team_id text NOT NULL REFERENCES nba.teams,
 season text NOT NULL,
 source_check_id uuid NOT NULL REFERENCES platform.source_checks,
 validated_at timestamptz NOT NULL CHECK(isfinite(validated_at)),
 members_artifact_id uuid NOT NULL REFERENCES platform.artifacts,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(team_id,season,source_check_id),
 CHECK(validated_at<=recorded_at)
);
CREATE INDEX roster_snapshots_check ON nba.roster_snapshots(source_check_id);
CREATE TABLE nba.player_game_versions (
 fact_id uuid PRIMARY KEY,
 event_id uuid NOT NULL REFERENCES nba.games,
 player_id text NOT NULL REFERENCES nba.players,
 team_id text NOT NULL REFERENCES nba.teams,
 source_check_id uuid NOT NULL REFERENCES platform.source_checks,
 observed_at timestamptz NOT NULL CHECK(isfinite(observed_at)),
 evidence_tier text NOT NULL CHECK(evidence_tier IN ('archived_observed','live_observed','historical_assumption')),
 participation text NOT NULL CHECK(participation IN ('played','did_not_play','unknown')),
 minutes_seconds numeric CHECK(minutes_seconds>=0 AND minutes_seconds<'Infinity'::numeric),
 points integer CHECK(points>=0),
 rebounds integer CHECK(rebounds>=0),
 assists integer CHECK(assists>=0),
 threes_made integer CHECK(threes_made>=0),
 started boolean,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(event_id,player_id,source_check_id),
 CHECK(observed_at<=recorded_at),
 CHECK(participation<>'did_not_play' OR
   (minutes_seconds IS NOT NULL AND minutes_seconds=0 AND points IS NOT NULL AND points=0
    AND rebounds IS NOT NULL AND rebounds=0 AND assists IS NOT NULL AND assists=0
    AND threes_made IS NOT NULL AND threes_made=0))
);
CREATE INDEX player_history_lookup ON nba.player_game_versions(player_id,event_id,observed_at);
CREATE INDEX player_history_check ON nba.player_game_versions(source_check_id);
CREATE TABLE nba.team_game_versions (
 fact_id uuid PRIMARY KEY,
 event_id uuid NOT NULL REFERENCES nba.games,
 team_id text NOT NULL REFERENCES nba.teams,
 source_check_id uuid NOT NULL REFERENCES platform.source_checks,
 observed_at timestamptz NOT NULL CHECK(isfinite(observed_at)),
 evidence_tier text NOT NULL CHECK(evidence_tier IN ('archived_observed','live_observed','historical_assumption')),
 points_for integer NOT NULL CHECK(points_for>=0),
 points_against integer NOT NULL CHECK(points_against>=0),
 extras_artifact_id uuid REFERENCES platform.artifacts,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(event_id,team_id,source_check_id),
 CHECK(observed_at<=recorded_at)
);
CREATE INDEX team_history_lookup ON nba.team_game_versions(team_id,event_id,observed_at);
CREATE INDEX team_history_check ON nba.team_game_versions(source_check_id);

CREATE FUNCTION platform.check_observed_source() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 IF NOT EXISTS (SELECT FROM platform.source_checks s WHERE s.check_id=NEW.source_check_id
     AND s.state='accepted' AND s.validated_at<=NEW.observed_at) THEN
   RAISE EXCEPTION 'Accepted source evidence must precede observation' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER event_source BEFORE INSERT ON platform.event_observations FOR EACH ROW EXECUTE FUNCTION platform.check_observed_source();
CREATE FUNCTION nba.check_history_row() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 IF NOT EXISTS (SELECT FROM nba.games g JOIN platform.events e USING(event_id)
    JOIN platform.source_checks s ON s.check_id=NEW.source_check_id
    WHERE g.event_id=NEW.event_id AND e.domain='nba'
    AND NEW.team_id IN (g.home_team_id,g.away_team_id)
    AND s.state='accepted' AND s.validated_at<=NEW.observed_at) THEN
   RAISE EXCEPTION 'Invalid game team or accepted revision' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER player_history_source BEFORE INSERT ON nba.player_game_versions FOR EACH ROW EXECUTE FUNCTION nba.check_history_row();
CREATE TRIGGER team_history_source BEFORE INSERT ON nba.team_game_versions FOR EACH ROW EXECUTE FUNCTION nba.check_history_row();
CREATE FUNCTION nba.check_game() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 IF NOT EXISTS (SELECT FROM platform.events e WHERE e.event_id=NEW.event_id
     AND e.domain='nba' AND e.source_event_id ~ '^[0-9]{10}$') THEN
   RAISE EXCEPTION 'NBA occurrence identity required' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER nba_game_identity BEFORE INSERT ON nba.games FOR EACH ROW EXECUTE FUNCTION nba.check_game();
CREATE FUNCTION nba.check_roster() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 IF NOT EXISTS (SELECT FROM platform.source_checks s JOIN platform.artifacts a
     ON a.artifact_id=NEW.members_artifact_id WHERE s.check_id=NEW.source_check_id
     AND s.state='accepted' AND s.validated_at=NEW.validated_at
     AND s.validation_summary->>'capability'='roster' AND a.kind='history'
     AND a.format='json' AND a.schema_version=1
     AND a.manifest->>'team_id'=NEW.team_id AND a.manifest->>'season'=NEW.season) THEN
   RAISE EXCEPTION 'Verified roster identity and artifact required' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER nba_roster_identity BEFORE INSERT ON nba.roster_snapshots FOR EACH ROW EXECUTE FUNCTION nba.check_roster();

GRANT SELECT ON platform.events,platform.event_observations,nba.teams,nba.players,nba.games,
 nba.roster_snapshots,nba.player_game_versions,nba.team_game_versions TO baseline_runtime;
GRANT INSERT(event_id,domain,source_event_id,competition,season,occurrence_no,predecessor_event_id) ON platform.events TO baseline_runtime;
GRANT INSERT(observation_id,event_id,source_check_id,observed_at,scheduled_start,actual_start,state,details) ON platform.event_observations TO baseline_runtime;
GRANT INSERT(team_id,display_name,abbreviation),UPDATE(display_name,abbreviation) ON nba.teams TO baseline_runtime;
GRANT INSERT(player_id,display_name),UPDATE(display_name) ON nba.players TO baseline_runtime;
GRANT INSERT ON nba.games TO baseline_runtime;
GRANT INSERT(roster_id,team_id,season,source_check_id,validated_at,members_artifact_id) ON nba.roster_snapshots TO baseline_runtime;
GRANT INSERT(fact_id,event_id,player_id,team_id,source_check_id,observed_at,evidence_tier,participation,minutes_seconds,points,rebounds,assists,threes_made,started) ON nba.player_game_versions TO baseline_runtime;
GRANT INSERT(fact_id,event_id,team_id,source_check_id,observed_at,evidence_tier,points_for,points_against,extras_artifact_id) ON nba.team_game_versions TO baseline_runtime;
