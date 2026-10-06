# Architecture and design notes

## Simple explanation

Growlog is a shared notebook for learning goals. A person signs in, records a skill and practice, and the server calculates totals. They can choose to share a post with the community. Their next device reads the same cloud account because records are stored centrally, while the actual pictures live in object storage.

## Technical flow

Browser → HTTPS → identity token → REST API → authorization/validation → relational database. Practice rows feed analytics. Upload bytes go to object storage; only keys and safe metadata belong in the database. A post references an uploaded object or achievement. Feed requests return public post fields, author display name, counts and paging cursor. Likes/comments are separate rows so uniqueness and ownership can be enforced.

## ER model (text)

```text
USERS(user_id PK, username UQ, email UQ, password_hash, profile fields)
  1 ──< SKILLS(skill_id PK, user_id FK, name, category, level, status)
SKILLS 1 ──< GOALS(goal_id PK, skill_id FK, user_id FK, target, unit, deadline)
GOALS 1 ──< MILESTONES(milestone_id PK, goal_id FK, target, achieved, achieved_at)
SKILLS 1 ──< PRACTICE_SESSIONS(session_id PK, user_id FK, skill_id FK, minutes, timestamp)
USERS 1 ──< POSTS(post_id PK, user_id FK, skill_id nullable FK, content, media_key)
POSTS 1 ──< COMMENTS(comment_id PK, post_id FK, user_id FK, content)
USERS >──< POSTS through LIKES(user_id FK, post_id FK, UNIQUE(user_id,post_id))
USERS >──< USERS through FOLLOWS(follower_id FK, followed_id FK, unique pair)
FILES(file_id PK, owner_id FK, object_key, content_type, bytes, visibility) [cloud extension]
```

## Data flow and cloud boundaries

Registration creates a user record and a signed session token. Each API request verifies signature/expiry and scopes queries by that user. Skills/goals/practice are relational data. `progress = min(100, practice minutes / 60 / target hours * 100)`. Streak is the run of unique calendar dates ending today (or yesterday when no session today). Upload is size/type/signature checked; production uploads should use API-issued short-lived signed upload URLs to a private bucket, then verify object metadata before attaching it. Public post sharing is explicit and should never make profile or proof private by default.

## Industry mapping

The same boundary appears in learning platforms, LMS/EdTech, fitness, creator networks, employee learning and portfolio products: identity, tenant/user data isolation, activity events, media assets, feeds, analytics and notifications. Centralization improves cross-device continuity; cloud object storage scales media separately from relational transactions; aggregate analytics can personalize goals and demonstrate engagement.

## Scale evolution

10 users: one app instance, SQLite/local files for classroom demo. 1,000 users: hosted stateless API, managed PostgreSQL, object store/CDN, indexes, backups and rate limits. 100,000 users: multiple API replicas behind load balancer, managed DB connection pool/read replica, cache, async workers/queue for notifications and image processing. One million posts: keyset pagination, time/author indexes, precomputed reaction counts, partition/archive strategy and feed ranking. At high scale fan-out-on-write speeds reads but creates write amplification for users with many followers; fan-out-on-read is easy and compute-heavy per request. Hybrid strategy handles celebrity accounts.

## Failure and operations

Use bounded retries with jitter only for transient network errors; idempotency keys for repeatable writes; explicit timeouts; user-safe error messages; structured logs with request ID and no passwords/tokens. If upload succeeds but metadata write fails, delete the object or enqueue cleanup; if the DB record exists but upload fails, leave attachment unset and let the user retry. DB errors should fail closed and return a correlation ID. Backups require restore testing. Monitor latency, error rate, DB pool/storage usage, queue lag, auth failures and spend. Build/deploy via CI after automated tests; separate dev/stage/prod secrets.

## Privacy / moderation work before public launch

Profile email is private. Add configurable profile/post visibility, report/block flows, spam rate limits, moderator review, comment removal, malware scanning and user deletion that removes DB records plus storage objects. Public APIs should use allowlisted fields. React/text rendering must escape untrusted content; SQLAlchemy parameterizes SQL values. Public media should be deliberate and revocable.
