-- Exact artifact bytes use UTF-8 JSON with unique keys. Server-generated content
-- identity uses publication-jsonb-v1 (PG17 rendering), never a client JSONB hash.
ALTER TABLE platform.forecast_batches ADD COLUMN family text;
ALTER TABLE platform.forecast_batches ADD COLUMN prepared_artifact_id uuid REFERENCES platform.artifacts;
ALTER TABLE platform.forecast_batches ADD CONSTRAINT one_family_batch UNIQUE(event_id,family);
GRANT SELECT ON nba.games,nba.roster_snapshots,nba.player_game_versions TO baseline_publisher;
-- Advisory locks serialize all observation and publication writers for an occurrence.
CREATE FUNCTION platform.lock_observation() RETURNS trigger LANGUAGE plpgsql
SET search_path=pg_catalog AS $$ BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended(NEW.event_id::text,617)); RETURN NEW;
END $$;
CREATE TRIGGER observation_lock BEFORE INSERT ON platform.event_observations
FOR EACH ROW EXECUTE FUNCTION platform.lock_observation();
GRANT EXECUTE ON FUNCTION platform.lock_observation() TO baseline_publisher;

CREATE FUNCTION platform.bound_json(identity uuid,body bytea,expected_kind text) RETURNS jsonb
LANGUAGE plpgsql SET search_path=pg_catalog AS $$ DECLARE content text; BEGIN
 IF body IS NULL OR octet_length(body)>2097152 OR NOT EXISTS (
 SELECT FROM platform.artifacts a WHERE a.artifact_id=identity AND a.kind=expected_kind
 AND a.format='json' AND a.schema_version=1 AND a.byte_count=octet_length(body)
 AND a.sha256=encode(sha256(body),'hex')) THEN RAISE EXCEPTION 'artifact_binding'; END IF;
 content:=convert_from(body,'UTF8');
 IF NOT (content IS JSON WITH UNIQUE KEYS) THEN RAISE EXCEPTION 'json_encoding'; END IF;
 RETURN content::jsonb;
END $$;
CREATE FUNCTION platform.source_fresh(identity uuid,at_time timestamptz,max_age interval)
RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog AS $$
 SELECT coalesce((SELECT s.state='accepted' AND s.requested_at<=s.received_at
 AND s.received_at<=s.validated_at AND s.validated_at<=at_time
 AND s.received_at>=at_time-max_age
 AND (s.source_published_at IS NULL OR s.source_published_at BETWEEN at_time-max_age AND at_time)
 AND (NOT(s.validation_summary ? 'source_generated_at') OR
   (s.validation_summary->>'source_generated_at')::timestamptz BETWEEN at_time-max_age AND at_time)
 FROM platform.source_checks s WHERE s.check_id=identity),false)
$$;
CREATE FUNCTION platform.eligible_occurrence(identity uuid)
RETURNS TABLE(observation_id uuid,scheduled_start timestamptz,deadline timestamptz)
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE o record; effective timestamptz; selected uuid; latest_check uuid; BEGIN
 PERFORM pg_advisory_xact_lock(hashtextextended(identity::text,617));
 FOR o IN SELECT v.*,s.validated_at FROM platform.event_observations v
 JOIN platform.source_checks s ON s.check_id=v.source_check_id
 WHERE v.event_id=identity ORDER BY v.observed_at,v.recorded_at,v.observation_id LOOP
   IF o.state IN('in_progress','final','postponed','cancelled') OR o.actual_start IS NOT NULL THEN
     RAISE EXCEPTION 'occurrence_ineligible';
   END IF;
   IF o.state='unknown' OR o.scheduled_start IS NULL THEN CONTINUE; END IF;
   IF effective IS NOT NULL AND o.scheduled_start>effective
      AND greatest(o.observed_at,o.recorded_at)>=effective-interval '15 minutes' THEN
      RAISE EXCEPTION 'closed_deadline';
   END IF;
   effective:=o.scheduled_start; selected:=o.observation_id; latest_check:=o.source_check_id;
 END LOOP;
 IF effective IS NULL OR o.state<>'scheduled' OR o.scheduled_start IS NULL
 OR clock_timestamp()>=effective-interval '15 minutes'
 OR NOT platform.source_fresh(latest_check,clock_timestamp(),interval '30 minutes') THEN
   RAISE EXCEPTION 'deadline_or_status';
 END IF;
 RETURN QUERY SELECT selected,effective,effective-interval '15 minutes';
END $$;

-- Internal generic operation. It is intentionally unavailable to runtime callers.
CREATE FUNCTION platform.store_batch(p jsonb,bundle uuid,prepared uuid,features uuid,cohort uuid,
 observation uuid,start_at timestamptz,family_name text) RETURNS uuid
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
DECLARE identity uuid; old platform.forecast_batches; entry jsonb; components jsonb;
 hash text; event uuid:=(p->'event'->>'event_id')::uuid; BEGIN
 hash:=encode(sha256(convert_to(jsonb_build_object('encoding','publication-jsonb-v1',
 'prepared',p-'run_id','bundle',bundle,'features',features,'cohort',cohort)::text,'UTF8')),'hex');
 SELECT * INTO old FROM platform.forecast_batches f WHERE f.event_id=event AND f.family=family_name;
 IF FOUND THEN
   IF old.content_hash<>hash THEN RAISE EXCEPTION 'conflicting_official_content'; END IF;
   RETURN old.batch_id;
 END IF;
 SELECT b.components INTO STRICT components FROM platform.model_bundles b WHERE b.bundle_id=bundle;
 identity:=gen_random_uuid();
 INSERT INTO platform.forecast_batches(batch_id,run_id,event_id,bundle_id,feature_artifact_id,
 cohort_artifact_id,schedule_observation_id,generated_at,feature_cutoff,scheduled_start,
 publication_policy_version,content_hash,family,prepared_artifact_id)
 VALUES(identity,(p->>'run_id')::uuid,event,bundle,features,cohort,observation,
 (p->>'generated_at')::timestamptz,(p->>'feature_cutoff')::timestamptz,start_at,
 'publication-jsonb-v1',hash,family_name,prepared);
 FOR entry IN SELECT * FROM jsonb_array_elements(p->'entries') LOOP
   INSERT INTO platform.official_slots(event_id,subject_type,subject_id,target,batch_id,decision_kind)
   VALUES(event,entry->>'subject_type',entry->>'subject_id',entry->>'target',identity,
    CASE WHEN entry->>'value' IS NULL THEN 'abstention' ELSE 'prediction' END);
   IF entry->>'value' IS NULL THEN
     INSERT INTO platform.abstentions(abstention_id,batch_id,subject_type,subject_id,target,
      role,reason_code,details) VALUES(gen_random_uuid(),identity,entry->>'subject_type',
      entry->>'subject_id',entry->>'target','official',entry->>'reason_code','{}');
   ELSE
     INSERT INTO platform.predictions(prediction_id,batch_id,subject_type,subject_id,target,
      role,model_id,value,unit) VALUES(gen_random_uuid(),identity,entry->>'subject_type',
      entry->>'subject_id',entry->>'target','official',(components->>(entry->>'target'))::uuid,
      (entry->>'value')::float8,entry->>'unit');
   END IF;
 END LOOP;
 RETURN identity;
END $$;

CREATE FUNCTION nba.publish_player(prepared uuid,pbody bytea,features uuid,fbody bytea,
 cohort uuid,cbody bytea,roster_bodies jsonb,bundle uuid) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog SET lock_timeout='2s' AS $$
DECLARE p jsonb; c jsonb; f jsonb; r jsonb; body jsonb; row nba.roster_snapshots;
 eligible record; g record; item jsonb; h jsonb; fact record; expected text[]:=ARRAY[]::text[];
 actual text[]; cutoff timestamptz; identity uuid; t text; units jsonb;
 BEGIN
 IF octet_length(roster_bodies::text)>1048576 THEN RAISE EXCEPTION 'roster_limit'; END IF;
 p:=platform.bound_json(prepared,pbody,'reports');
 f:=platform.bound_json(features,fbody,'features'); c:=platform.bound_json(cohort,cbody,'features');
 IF NOT(p ?& ARRAY['schema_version','event','run_id','environment','descriptor','features',
 'cohort','schedule','roster_sources','entries','feature_cutoff','generated_at','official_publication'])
 OR p->'features' IS DISTINCT FROM f OR p->'cohort' IS DISTINCT FROM c
 OR p->>'schema_version'<>'1' OR p->>'official_publication'<>'false'
 OR p->'descriptor'->>'domain'<>'nba'
 OR p->'descriptor'->>'family'<>'player_recent_appearance_mean'
 OR p ?| ARRAY['recorded_at','insertion_transaction_id','observed_committed_at'] THEN
   RAISE EXCEPTION 'prepared_binding'; END IF;
 SELECT e.*,n.home_team_id,n.away_team_id INTO STRICT g FROM platform.events e
 JOIN nba.games n USING(event_id) WHERE e.event_id=(p->'event'->>'event_id')::uuid;
 IF g.domain<>'nba' OR g.season<>p->'event'->>'season'
 OR g.source_event_id<>p->'event'->>'source_event_id' THEN RAISE EXCEPTION 'event_identity'; END IF;
 -- Exact retry can be read after closure, but never stores new content.
 PERFORM pg_advisory_xact_lock(hashtextextended(g.event_id::text,617));
 IF EXISTS(SELECT FROM platform.forecast_batches b WHERE b.event_id=g.event_id
 AND b.family='player_recent_appearance_mean') THEN
   RETURN platform.store_batch(p,bundle,prepared,features,cohort,NULL,NULL,'player_recent_appearance_mean');
 END IF;
 SELECT * INTO STRICT eligible FROM platform.eligible_occurrence(g.event_id);
 cutoff:=(p->>'feature_cutoff')::timestamptz;
 IF NOT isfinite(cutoff) OR cutoff>(p->>'generated_at')::timestamptz
 OR (p->>'generated_at')::timestamptz>clock_timestamp()
 OR NOT EXISTS (SELECT FROM platform.runs x WHERE x.run_id=(p->>'run_id')::uuid
   AND x.domain='nba' AND x.environment=p->>'environment')
 OR NOT EXISTS (SELECT FROM platform.event_observations o WHERE
   o.observation_id=(p->'schedule'->>'observation_id')::uuid AND o.event_id=g.event_id
   AND o.observed_at<=cutoff AND o.source_check_id=(p->'schedule'->>'source_check_id')::uuid
   AND platform.source_fresh(o.source_check_id,cutoff,interval '30 minutes')) THEN
   RAISE EXCEPTION 'cutoff_evidence'; END IF;
 IF jsonb_array_length(p->'roster_sources')<>2 OR jsonb_array_length(roster_bodies)<>2
 OR jsonb_array_length(c) NOT BETWEEN 1 AND 60 THEN RAISE EXCEPTION 'roster_count'; END IF;
 FOR r IN SELECT * FROM jsonb_array_elements(p->'roster_sources') LOOP
   SELECT * INTO STRICT row FROM nba.roster_snapshots s WHERE s.roster_id=(r->>'roster_id')::uuid;
   SELECT x INTO STRICT body FROM jsonb_array_elements(roster_bodies) x
     WHERE x->>'roster_id'=row.roster_id::text;
   body:=platform.bound_json(row.members_artifact_id,convert_to(body->>'body','UTF8'),'history');
   IF row.team_id NOT IN(g.home_team_id,g.away_team_id) OR row.season<>g.season
   OR row.source_check_id<>(r->>'source_check_id')::uuid
   OR row.members_artifact_id IS DISTINCT FROM (r->'artifact'->>'artifact_id')::uuid
   OR body->>'team_id'<>row.team_id OR body->>'season'<>row.season
   OR body->>'schema_version'<>'1' OR row.validated_at>cutoff
   OR NOT platform.source_fresh(row.source_check_id,cutoff,interval '24 hours')
   OR NOT platform.source_fresh(row.source_check_id,clock_timestamp(),interval '24 hours')
   OR EXISTS(SELECT FROM nba.roster_snapshots newer WHERE newer.team_id=row.team_id
     AND newer.season=row.season AND newer.validated_at>row.validated_at) THEN
       RAISE EXCEPTION 'roster_identity_or_freshness'; END IF;
   FOR item IN SELECT * FROM jsonb_array_elements(body->'players') LOOP
     IF item->>'player_id' !~ '^[1-9][0-9]*$' OR item->>'player_id'=ANY(expected)
     OR NOT EXISTS(SELECT FROM jsonb_array_elements(c) x WHERE x->>'player_id'=item->>'player_id'
       AND x->>'team_id'=row.team_id) THEN RAISE EXCEPTION 'cohort_membership'; END IF;
     expected:=array_append(expected,item->>'player_id');
   END LOOP;
 END LOOP;
 SELECT array_agg(x->>'player_id' ORDER BY x->>'player_id') INTO actual FROM jsonb_array_elements(c) x;
 IF actual IS DISTINCT FROM (SELECT array_agg(x ORDER BY x) FROM unnest(expected) x)
 OR (SELECT count(DISTINCT x->>'team_id') FROM jsonb_array_elements(c) x)<>2
 OR (SELECT array_agg(x->>'player_id' ORDER BY x->>'player_id') FROM jsonb_array_elements(f) x)
   IS DISTINCT FROM actual THEN
   RAISE EXCEPTION 'cohort_exactness'; END IF;
 units:='{"minutes":"minutes","points":"points","rebounds":"rebounds","assists":"assists","threes_made":"threes made"}';
 IF NOT EXISTS(SELECT FROM platform.active_bundles a JOIN platform.model_bundles b USING(bundle_id)
 WHERE a.domain='nba' AND a.family='player_recent_appearance_mean' AND a.bundle_id=bundle
 AND b.config_hash=p->'descriptor'->>'config_hash' AND (SELECT count(*) FROM jsonb_object_keys(b.components))=5)
 OR EXISTS(SELECT FROM platform.model_bundles b CROSS JOIN LATERAL jsonb_each_text(b.components) q
 JOIN platform.models m ON m.model_id=q.value::uuid WHERE b.bundle_id=bundle
 AND (m.code_version<>p->'descriptor'->>'code_version'
 OR m.config_hash<>p->'descriptor'->>'config_hash' OR NOT(units ? m.target))) THEN
   RAISE EXCEPTION 'active_model_binding'; END IF;
 IF jsonb_array_length(p->'entries')<>cardinality(expected)*5 THEN RAISE EXCEPTION 'slot_count'; END IF;
 FOR item IN SELECT * FROM jsonb_array_elements(p->'entries') LOOP
   t:=item->>'target';
   IF NOT(item ?& ARRAY['subject_type','subject_id','target','unit','value','reason_code'])
   OR item->>'subject_type' IS DISTINCT FROM 'player'
   OR NOT(item->>'subject_id'=ANY(expected))
   OR NOT(units ? t) OR item->>'unit' IS DISTINCT FROM units->>t
   OR (item->>'value' IS NOT NULL AND (jsonb_typeof(item->'value')<>'number'
     OR (item->>'value')::float8<0 OR (item->>'value')::float8>='Infinity'::float8
     OR item->>'reason_code' IS NOT NULL))
   OR (item->>'value' IS NULL AND item->>'reason_code' IS NULL) THEN RAISE EXCEPTION 'invalid_decision'; END IF;
 END LOOP;
 -- Every feature history fact must match its saved revision and predate cutoff.
 FOR item IN SELECT * FROM jsonb_array_elements(f) LOOP
   FOR h IN SELECT * FROM jsonb_array_elements(item->'history') LOOP
     SELECT v.* INTO STRICT fact FROM nba.player_game_versions v WHERE v.fact_id=(h->>'fact_id')::uuid;
     IF fact.event_id=g.event_id OR fact.player_id<>item->>'player_id' OR fact.observed_at>cutoff
     OR fact.source_check_id<>(h->>'source_check_id')::uuid
     OR NOT platform.source_fresh(fact.source_check_id,cutoff,interval '100 years')
     OR fact.minutes_seconds IS DISTINCT FROM (h->>'minutes_seconds')::numeric
     OR fact.points IS DISTINCT FROM (h->>'points')::integer
     OR fact.rebounds IS DISTINCT FROM (h->>'rebounds')::integer
     OR fact.assists IS DISTINCT FROM (h->>'assists')::integer
     OR fact.threes_made IS DISTINCT FROM (h->>'threes_made')::integer
     OR NOT EXISTS(SELECT FROM platform.events he WHERE he.event_id=fact.event_id
       AND he.competition='regular')
     OR NOT EXISTS(SELECT FROM platform.event_observations ho WHERE ho.event_id=fact.event_id
       AND ho.observed_at<=cutoff AND ho.state='final'
       AND platform.source_fresh(ho.source_check_id,cutoff,interval '100 years')
       AND ((ho.actual_start IS NOT NULL AND ho.actual_start<cutoff)
         OR (ho.details->>'date_convention'='source_calendar_verified'
         AND (ho.details->>'game_date')::date<(cutoff AT TIME ZONE 'America/New_York')::date))) THEN
       RAISE EXCEPTION 'history_binding'; END IF;
   END LOOP;
 END LOOP;
 identity:=platform.store_batch(p,bundle,prepared,features,cohort,eligible.observation_id,
 eligible.scheduled_start,'player_recent_appearance_mean');
 PERFORM platform.eligible_occurrence(g.event_id); RETURN identity;
END $$;

CREATE FUNCTION platform.confirm_batch(identity uuid) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog SET lock_timeout='2s' AS $$
DECLARE b platform.forecast_batches; receipt uuid; BEGIN
 SELECT * INTO STRICT b FROM platform.forecast_batches WHERE batch_id=identity;
 PERFORM pg_advisory_xact_lock(hashtextextended(b.event_id::text,617));
 SELECT receipt_id INTO receipt FROM platform.publication_receipts WHERE batch_id=identity;
 IF receipt IS NOT NULL THEN RETURN receipt; END IF;
 IF b.insertion_transaction_id=pg_current_xact_id()::text OR EXISTS (
 SELECT FROM platform.prediction_events WHERE batch_id=identity AND kind='invalidation') THEN
   RAISE EXCEPTION 'confirmation_ineligible'; END IF;
 PERFORM platform.eligible_occurrence(b.event_id);
 receipt:=gen_random_uuid();
 INSERT INTO platform.publication_receipts(receipt_id,batch_id,policy_version)
 VALUES(receipt,identity,b.publication_policy_version);
 PERFORM platform.eligible_occurrence(b.event_id); RETURN receipt;
END $$;
CREATE FUNCTION platform.append_lifecycle(identity uuid,observation uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog SET lock_timeout='2s' AS $$
DECLARE b platform.forecast_batches; o platform.event_observations; reason text; BEGIN
 SELECT * INTO STRICT b FROM platform.forecast_batches WHERE batch_id=identity;
 PERFORM pg_advisory_xact_lock(hashtextextended(b.event_id::text,617));
 SELECT * INTO STRICT o FROM platform.event_observations WHERE observation_id=observation AND event_id=b.event_id;
 reason:=CASE WHEN o.state IN('postponed','cancelled') THEN o.state
 WHEN o.actual_start<=b.recorded_at THEN 'earlier_actual_start'
 WHEN o.scheduled_start-interval '15 minutes'<=b.recorded_at THEN 'earlier_schedule' END;
 IF reason IS NULL THEN RETURN; END IF;
 IF NOT EXISTS(SELECT FROM platform.prediction_events WHERE batch_id=identity
 AND kind='invalidation' AND source_check_id=o.source_check_id) THEN
 INSERT INTO platform.prediction_events(prediction_event_id,batch_id,kind,reason_code,source_check_id)
 VALUES(gen_random_uuid(),identity,'invalidation',reason,o.source_check_id); END IF;
END $$;
CREATE VIEW platform.batch_status AS
 SELECT b.batch_id,b.event_id,b.content_hash,b.recorded_at,r.receipt_id,r.observed_committed_at,
 CASE WHEN EXISTS(SELECT FROM platform.prediction_events e WHERE e.batch_id=b.batch_id AND e.kind='invalidation')
 OR EXISTS(SELECT FROM platform.event_observations o WHERE o.event_id=b.event_id
 AND (o.state IN('postponed','cancelled') OR o.actual_start<=coalesce(r.observed_committed_at,b.recorded_at)
 OR o.scheduled_start-interval '15 minutes'<=coalesce(r.observed_committed_at,b.recorded_at)))
 THEN 'invalidated' WHEN r.receipt_id IS NULL THEN 'stored_unverified' ELSE 'timely_confirmed' END AS state
 FROM platform.forecast_batches b LEFT JOIN platform.publication_receipts r USING(batch_id);
GRANT SELECT ON platform.batch_status TO baseline_runtime;

-- The schema owner creates functions, then a controlled migration identity
-- transfers only these function identities. Runtime never gains owner membership.
RESET ROLE;
GRANT CREATE ON SCHEMA platform,nba TO baseline_publisher;
ALTER FUNCTION platform.bound_json(uuid,bytea,text) OWNER TO baseline_publisher;
ALTER FUNCTION platform.source_fresh(uuid,timestamptz,interval) OWNER TO baseline_publisher;
ALTER FUNCTION platform.eligible_occurrence(uuid) OWNER TO baseline_publisher;
ALTER FUNCTION platform.store_batch(jsonb,uuid,uuid,uuid,uuid,uuid,timestamptz,text) OWNER TO baseline_publisher;
ALTER FUNCTION nba.publish_player(uuid,bytea,uuid,bytea,uuid,bytea,jsonb,uuid) OWNER TO baseline_publisher;
ALTER FUNCTION platform.confirm_batch(uuid) OWNER TO baseline_publisher;
ALTER FUNCTION platform.append_lifecycle(uuid,uuid) OWNER TO baseline_publisher;
REVOKE CREATE ON SCHEMA platform,nba FROM baseline_publisher;
REVOKE ALL ON FUNCTION platform.bound_json(uuid,bytea,text),platform.source_fresh(uuid,timestamptz,interval),
 platform.eligible_occurrence(uuid),platform.store_batch(jsonb,uuid,uuid,uuid,uuid,uuid,timestamptz,text),
 nba.publish_player(uuid,bytea,uuid,bytea,uuid,bytea,jsonb,uuid),platform.confirm_batch(uuid),
 platform.append_lifecycle(uuid,uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION nba.publish_player(uuid,bytea,uuid,bytea,uuid,bytea,jsonb,uuid),
 platform.confirm_batch(uuid),platform.append_lifecycle(uuid,uuid) TO baseline_runtime;
SET LOCAL ROLE baseline_owner;
