# Private Supabase credential setup

The new project is [baseline](https://supabase.com/dashboard/project/lkwfzdfaqempnwffocmm).
Its reviewed schemas through 0008 are applied. MCP cannot provide the private
credentials needed by the native runtime and Auth/Storage verification commands.

## Enter two private values

An ignored `.env` already exists at the repository root with the verified public
URL/key filled in. Preserve those entries. The tracked `.env.example` contains
names and blank placeholders only; never copy real keys into that example.

1. Open the project Dashboard. In Database settings, set/reset its database
   password if you do not already know it. Save the new generated password in
   your password manager. It is separate from your Supabase account password.
2. Open Connect and choose **Session pooler**, port **5432**. Copy the actual host
   and username shown for this project. Keep `BASELINE_DB_CONNECTION_MODE=session`.
   Do not choose transaction pooling, port 6543. The application uses session
   coordination and separate commit-confirmation transactions.
3. Download the project CA certificate from Database settings, SSL Configuration.
   Save it locally as `artifacts/supabase-ca.crt`; `.env` points PGSSLROOTCERT there.
4. Fill `BASELINE_MIGRATION_DSN` in `.env`. The keyword form avoids URL password
   encoding. Use the real host from Connect, not an invented region endpoint:

   ```dotenv
   BASELINE_MIGRATION_DSN="host=ACTUAL_SESSION_HOST port=5432 dbname=postgres user=postgres.lkwfzdfaqempnwffocmm password='YOUR_DATABASE_PASSWORD' sslmode=verify-full"
   ```

   If the password contains a single quote or backslash, escape it according to
   libpq connection-string rules, or use the Dashboard URI with a locally URL
   encoded password. Keep the value out of chat and terminal history.
5. Open Settings, API Keys. Copy a server **secret key** beginning `sb_secret_`
   into `BASELINE_SUPABASE_ADMIN_KEY` in the private `.env`. Create a dedicated
   setup key there if none exists. The controlled setup client sends it through
   the apikey header. It never belongs in scheduled prediction jobs or a frontend.

Sources: [connection modes](https://supabase.com/docs/guides/database/connecting-to-postgres),
[CA verification](https://supabase.com/docs/guides/platform/ssl-enforcement), and
[API keys](https://supabase.com/docs/guides/getting-started/api-keys).

## Close public signup

The live Auth settings endpoint currently reports `disable_signup=false`. In
Authentication, Sign In / Providers, switch off **Allow new users to sign up**.
This matches Baseline's backend-only identity design. Controlled administrator
creation of the dedicated backend/test identities remains the supported setup.
The agent will read back the setting; no user signup request is needed.
[Auth configuration](https://supabase.com/docs/guides/auth/general-configuration)

## Safe next check

Tell the agent that the private file is configured. The agent can load it with
uv's verified `--env-file .env` option and run the existing connection checks
without displaying credentials. `git check-ignore .env` must return `.env`.
Inspecting pending migrations is read-only; do not apply unreviewed later files
merely because credentials are now available.

Provision the separate runtime password and backend/negative-test Auth identities
through the existing controlled operations, then configure only restricted
runtime/backend values for Windows and Actions. The private setup key stays out
of those jobs. Actual TLS, sign-in, renewal and denied Storage mutations still
need recorded verification; the successful MCP SQL session does not establish
those client paths.

OneDrive configuration is a separate next step: a dedicated existing sync folder,
permitted rclone OAuth configuration, native Postgres 17 tools, actual remote
readback and a disposable restore target. See [backup operations](backups.md).
