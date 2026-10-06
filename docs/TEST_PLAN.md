# Verification plan

Run `python -m pytest -q`. The tests create synthetic accounts ending in `@example.test`. The API currently returns FastAPI's actual HTTP responses; mark actual results only after running the app in the target cloud environment. Do not claim a cloud test when it was only run locally.

| ID | Scenario / input | Expected result | Actual result | Pass/Fail |
|---|---|---|---|---|
| T01 | Register unique valid account | 201, profile + token | Record after run | |
| T02 | Register existing email/username | 409 | | |
| T03 | Login correct email/password | 200 token | | |
| T04 | Login wrong password | 401 | | |
| T05 | Update own profile | 200, changed public fields | | |
| T06 | Add skill | 201 | | |
| T07 | Update own skill | 200 | | |
| T08 | Delete own skill | Message; subsequent lookup 404 | | |
| T09 | Create goal and milestones | 201, zero progress | | |
| T10 | Log practice session | 201 record | | |
| T11 | Log 60 min toward 2h target | Goal progress 50% | | |
| T12 | Log enough practice to reach milestone | Milestone marked achieved on milestone read | | |
| T13 | Upload supported valid JPEG/PNG/PDF with auth | 201 URL | | |
| T14 | Unsupported MIME or invalid file signature | 415 | | |
| T15 | Create community post | 201 | | |
| T16 | Retrieve feed | Post returned, paginated | | |
| T17 | Like post | liked true | | |
| T18 | Repeat same like | one like only | | |
| T19 | Unlike | liked false | | |
| T20 | Add comment | 201 | | |
| T21 | Delete another user's post/comment | 403 | | |
| T22 | Dashboard after known practice rows | correct totals/streak | | |
| T23 | User B requests user A private skill | 404; B list empty | | |
| T24 | Stop object store / local filesystem unwritable | graceful 5xx; no false success (inject in production adapter) | | |
| T25 | Stop database | graceful 5xx and logged failure (integration environment) | | |
| T26 | Use expired or tampered bearer token | 401 | | |
| T27 | Logout then clear client token; retry private endpoint | 401 without token | | |

File upload/database failure behavior, token expiry timing, and cloud backup/restore need dedicated fault-injection tests before production. The current tests demonstrate core local behavior, not a full security audit.
