# Deployment runbook

The checked-in app is a local coursework implementation. It does not yet ship an S3/Supabase Storage adapter or a provider-specific identity adapter; local files and app-issued tokens are not production equivalents. First deploy only synthetic demo content, then add those adapters before inviting real users.

## Approach A: student demo with managed services

Example composition: static frontend on a static host, FastAPI web service on Render, PostgreSQL database on Render or Supabase, and private object storage on Supabase Storage/S3-compatible provider. Free plans and limits are time-sensitive: Render documents free web services, static sites and Postgres with limitations and says the free tier is for hobby projects/testing; verify current limitations at [Render free services](https://render.com/docs/free) and [Render pricing](https://render.com/pricing). Supabase lists a free plan and usage quotas; review [Supabase pricing](https://supabase.com/pricing) and [database size limits](https://supabase.com/docs/guides/platform/database-size) immediately before deployment. Never assume no card, no suspension, or zero overage without checking the live account terms.

1. Create a GitHub repository and push the project. Ensure `.env`, database files and uploads are ignored; never commit credentials or real-user content.
2. Provision hosted PostgreSQL. Copy its private connection URL into the backend service's `DATABASE_URL` setting; use provider TLS settings and run schema migrations (the current starter calls `create_all` and should be changed to Alembic for a persistent deployment).
3. Create the API web service from this repository. Build: `pip install -r requirements.txt`; start: `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`. Set `APP_SECRET` to a generated random secret, `DATABASE_URL`, `CORS_ORIGINS` to the exact frontend origin, and a provider-specific upload adapter configuration. Do not set `SEED_DEMO` in production.
4. Host the `frontend/` directory as a static site. Configure a rewrite so `/api/*` and `/docs` route to the API origin, or change the frontend API base URL to the API host and allow that exact origin in CORS. A static site needs SPA fallback only if client-side routes are later added.
5. Provision a private object bucket. Replace local `UPLOAD_DIR` handling with an adapter that returns an object key, authorizes the owner, and issues short-lived signed access URLs. Do not mount a public bucket or embed service credentials in browser code.
6. Add the hosted URL to CORS, configure HTTPS, test health, register two synthetic users, verify isolation, upload/attach a sample image, and inspect logs. Check that media works after service restart; ephemeral filesystem storage is not durable.
7. Turn on database backups where available and perform a restore exercise. Add budget alerts, usage monitoring and teardown steps. Capture deployment screenshots only after these checks pass.

**Important starter limitation:** steps 2 and 5 require configuration/code adaptation rather than only environment variables; SQLite schema creation and local uploads currently work out of the box. For a lower-risk course demo, keep the app local and present the cloud deployment architecture as a planned migration until the adapters are implemented.

## Approach B: AWS enterprise reference

1. Build static assets and publish to private S3 origin served through CloudFront and TLS.
2. Use Cognito for identity; validate its JWT issuer/audience in API middleware.
3. Route `/api/*` through API Gateway to Lambda or a container service such as App Runner. Keep compute stateless and configuration in Secrets Manager.
4. Choose RDS PostgreSQL for relational querying or DynamoDB for access-pattern-driven NoSQL design; create indexes and least-privilege IAM policies.
5. Keep media in a private S3 bucket. API verifies authorization and returns short-lived pre-signed upload/download URLs. Add size/type constraints, scanning and lifecycle cleanup.
6. Add CloudWatch logs/metrics/alarms, database backups/restore drills, budget alerts, rate limiting/WAF and CI/CD with separate environments.

Azure equivalents: Static Web Apps/Front Door, Entra External ID, API Management + Functions/Container Apps, Azure Database for PostgreSQL or Cosmos DB, private Blob Storage/SAS tokens, Monitor and Key Vault. GCP equivalents: Firebase Hosting/Cloud CDN, Identity Platform, API Gateway + Cloud Run/Functions, Cloud SQL or Firestore, private Cloud Storage signed URLs, Cloud Monitoring and Secret Manager.
