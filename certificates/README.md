# Supabase database trust anchor

supabase-ca-2021.crt is the public CA downloaded from Baseline's Supabase SSL
Configuration panel. It contains no private key. The session-pooler connection
was verified with this CA on Windows before it was added here for Linux Actions.

SHA-256: 700723581420dd1ac98fd7e9ac529f0ef210eadcaf87fc868a3ad7d114c2f3b7

Hosted checks require sslmode=verify-full. Certificate verification failures
remain failures; review a replacement from the provider dashboard before rotation.
See https://supabase.com/docs/guides/platform/ssl-enforcement.
