RESET ROLE;
-- Hosted postgres cannot grant access to managed auth. Read the same trusted
-- request claims without granting provider role memberships to the owner.
SET LOCAL ROLE baseline_owner;
CREATE TABLE platform.artifact_storage_bindings (
 binding_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 backend_user_id uuid NOT NULL,
 bucket_id text NOT NULL CHECK (bucket_id ~ '^[a-z0-9-]{1,63}$'),
 configured_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
-- No binding means no runtime object access. Setup appends reviewed settings.
CREATE FUNCTION platform.artifact_identity_allowed(bucket text) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS $$
 SELECT coalesce((SELECT backend_user_id=coalesce(
     nullif(current_setting('request.jwt.claim.sub',true),''),
     nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'sub'
   )::uuid AND bucket_id=bucket
   FROM platform.artifact_storage_bindings ORDER BY binding_id DESC LIMIT 1),false)
$$;
GRANT USAGE ON SCHEMA platform TO authenticated;
GRANT EXECUTE ON FUNCTION platform.artifact_identity_allowed(text) TO authenticated;
-- Only the privileged setup connection can install policies on provider objects.
RESET ROLE;
DO $$ BEGIN
 IF NOT EXISTS (SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='storage' AND c.relname='objects' AND c.relrowsecurity)
    OR NOT EXISTS (SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='storage' AND c.relname='buckets' AND c.relrowsecurity) THEN
   RAISE EXCEPTION 'Provider Storage row security must be verified before Baseline';
 END IF;
 IF EXISTS (SELECT FROM pg_policies WHERE schemaname='storage' AND tablename IN ('objects','buckets')) THEN
   RAISE EXCEPTION 'Review existing Storage policies before enabling Baseline';
 END IF;
END $$;
CREATE POLICY baseline_artifact_read ON storage.objects FOR SELECT TO authenticated
 USING (platform.artifact_identity_allowed(bucket_id));
CREATE POLICY baseline_artifact_create ON storage.objects FOR INSERT TO authenticated
 WITH CHECK (platform.artifact_identity_allowed(bucket_id)
   AND name ~ '^(raw|history|features|models|reports)/[0-9a-f]{2}/[0-9a-f]{64}$'
   AND split_part(name,'/',2)=left(split_part(name,'/',3),2));
SET LOCAL ROLE baseline_owner;
