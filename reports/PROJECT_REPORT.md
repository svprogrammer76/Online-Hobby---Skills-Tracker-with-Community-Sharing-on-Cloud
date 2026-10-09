# Online Hobby & Skills Tracker with Community Sharing on Cloud

## Abstract

This project designs and implements a cloud-oriented platform for recording hobbies, skills, practice sessions, measurable goals and community achievements. A FastAPI REST service provides authentication and user-scoped authorization, SQLAlchemy models structured learning/social data, and a responsive browser client presents progress and community interactions. Local SQLite/files mode makes the project reproducible without paid services. The project author deployed and checked the app on Render with Supabase PostgreSQL; private cloud object storage is not yet integrated. Automated tests cover core ownership and workflow behavior.

## Introduction and problem statement

Learners often use disconnected notes, timers and communities, making progress difficult to measure and share. The proposed service centralizes activity history and goals so a learner can continue on another device and optionally celebrate milestones with others.

## Objectives

Implement synthetic-user registration, profiles, skill CRUD, goal/milestone tracking, practice logging, file upload simulation, community posts, likes/comments, analytics, REST APIs, local execution, cloud deployment design, automated verification and GitHub documentation.

## Existing and proposed system

The existing workflow relies on separate notebooks, spreadsheets and social platforms. Growlog stores structured progress and community records behind an API and keeps media separate from database rows. Ownership checks prevent one user from editing another user's private progress.

## Industry relevance and cloud concepts

The same design supports EdTech/LMS, fitness, creator communities, employee learning and portfolio services. It demonstrates client-server SaaS, PaaS/IaaS boundaries, REST, authentication/authorization, relational data, object storage, serverless alternatives, event processing, elastic scaling, CDN, load balancing, API gateways, caching, secrets, logs, monitoring, backup and CI/CD through its local implementation and documented production evolution.

## Technology stack and architecture

Python, FastAPI, SQLAlchemy, SQLite for local mode, HTML/CSS/JavaScript frontend, pytest, and filesystem uploads. A production adaptation can use React, managed PostgreSQL/Auth/object storage, container/serverless hosting, CDN, gateway, secret manager and monitoring. Browser → API → auth/owner checks → relational DB; file bytes go through a storage boundary; analytics aggregate practice records; the feed returns public post data and social counts.

## Database, storage and authentication

Users own skills, goals, sessions, posts and comments; goals contain milestones; likes have a unique user/post pair; follows relate user pairs. Primary and foreign keys protect references; owner/timestamp fields are indexed. Passwords are salted PBKDF2 hashes. Signed bearer tokens are time-limited. Local file validation demonstrates a safe baseline, while production media belongs in a private object bucket with signed URLs. Email is omitted from public profile output.

## Functional modules

Skill records track category, level, status and descriptions. Practice records use minutes and timestamps. Hourly progress equals logged minutes / 60 divided by target, clamped for display. Milestones are achieved when their threshold is met. Community posts are explicit sharing actions; likes/comments are separate records. Dashboard analytics include total/weekly/monthly practice, streaks, skill breakdown, goals, milestones and engagement.

## API and implementation

FastAPI exposes registration/login/logout, profile, skill, goal, practice, post/feed, likes/comments, upload, follow and analytics endpoints. Pydantic validates inputs; bearer dependencies authenticate; queries scope private records by user. The frontend uses fetch and escapes user-provided text before rendering.

## Testing

Run `python -m pytest -q`. Tests cover register/duplicate/login, skills and isolation, goal progress, practice totals, feed, idempotent likes, comments and unauthorized deletion. Use `docs/TEST_PLAN.md` for manual test IDs, expected results and actual result fields. Report only results actually observed in the submission environment.

## Cloud deployment, security, privacy and scale

The student deployment runs FastAPI and the browser frontend on Render and stores relational data in an existing Supabase PostgreSQL project; secrets are configured in the Render environment. The author reports checking the live app at https://online-hobby-and-skills-tracker-with.onrender.com/. The app uses its own signed bearer tokens, not Supabase Auth, and uploads remain on the service's ephemeral filesystem rather than cloud object storage. Enterprise reference uses S3/CloudFront, Cognito, API Gateway/Lambda, RDS or DynamoDB, private S3, optional cache, CloudWatch and Secrets Manager. Apply TLS, least privilege, encryption, rate limits, upload scanning, input validation, moderation, backup and restore tests. At scale add stateless replicas, load balancing, indexes, keyset pagination, caches and queues. Feed fan-out may evolve from read-time queries to write-time/hybrid delivery.

## Results, advantages and limitations

The project supports end-to-end skill, practice, goal and community flows with a reproducible test suite and has been deployed to a public Render URL with Supabase PostgreSQL. Local SQLite and the deployed service's filesystem uploads are not durable cloud object storage. Supabase Auth, private cloud uploads, moderation, deletion lifecycle, refresh/revocation, migrations and a restore exercise remain future work.

## Future scope and conclusion

Implement private signed uploads, schema migrations, user timezone policies, report/block/moderation, account deletion, notifications, CI/CD, observability and backup restoration. The project shows how cloud infrastructure can turn a personal tracker into a secure, scalable multi-user service while maintaining a local learning path.
