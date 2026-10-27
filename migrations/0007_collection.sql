-- Exactly one linked successor, even when two workers observe the same reschedule.
CREATE UNIQUE INDEX one_occurrence_successor ON platform.events(predecessor_event_id)
WHERE predecessor_event_id IS NOT NULL;
CREATE INDEX roster_team_season_time ON nba.roster_snapshots(team_id,season,validated_at);
