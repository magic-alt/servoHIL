# GitHub ↔ Notion Verification Matrix sync

Tracked Issues and PRs carry explicit V&V metadata. The sync key is the pair
`REQ-ID + TC-ID`.

The design deliberately separates **GitHub lifecycle state** from **engineering
verification state**:

- Issue closed / PR merged never implies `PASS`.
- A new PR head (`synchronize`) makes PR-bound evidence stale and resets the
  Matrix verdict to `NOT RUN / Ready` until evidence is explicitly refreshed.
- Closing or merging a PR does not re-apply an older body verdict after a new
  commit invalidated it.

## Metadata contract

Supported fields:

- `REQ-ID`
- `TC-ID`
- `Knowledge Node URL`
- `Requirement`
- `Test Case`
- `Verification Level`
- `Acceptance Criteria`
- `Evidence Path`
- `Evidence URL`
- `Evidence Date` (`YYYY-MM-DD`)
- `Bench / DUT`
- `HW Revision`
- `FW SHA`
- `Bitstream`
- `Result`
- `Verification Status`

`Result` is one of `PASS`, `FAIL`, `PARTIAL`, `BLOCKED`, `NOT RUN`.

## Field ownership

GitHub automation owns only machine-oriented Matrix fields:

- GitHub Issue/PR URL, number and lifecycle state
- Git SHA
- FW SHA
- Bitstream
- HW Revision
- Evidence Path / Evidence URL / Evidence Date
- Result / Verification Status when explicitly present in trusted metadata
- Evidence freshness and Evidence Git SHA
- Last Synced / Sync Contract

Human/test-report fields such as `Evidence` and the curated
`Commit/FW/Bitstream` summary are **not overwritten** by automation.

For an existing Matrix row, the legacy `Issue/PR` URL is also left unchanged;
dedicated `GitHub Issue` and `GitHub PR` fields preserve both links instead of
letting Issue and PR events overwrite each other.

## Evidence freshness

For PR-backed evidence:

- explicit `PASS` / `FAIL` / `PARTIAL` binds `Evidence Git SHA` to the current
  PR head and marks freshness `current`;
- a later `synchronize` event updates `Git SHA`, marks evidence `stale`, and
  resets the verdict to `NOT RUN / Ready`;
- a later PR close/merge updates only lifecycle fields and cannot silently
  restore the stale verdict.

This enforces the rule that evidence from an older commit is not inherited by
a newer commit.

## Repository / organization configuration

Configure:

- secret `NOTION_TOKEN`: Notion integration token with access to the Engineering
  Evidence / Verification Matrix;
- variable `NOTION_VERIFICATION_DATA_SOURCE_ID`: Matrix data-source UUID.

Prefer organization-level secret/variable scoped to these four repositories so
the same contract is configured once:

- `magic-alt/hil_lab`
- `magic-alt/igh-lab`
- `magic-alt/servo_host`
- `magic-alt/servoHIL`

Share the Matrix and related Knowledge Node database with the Notion
integration. The workflow uses Notion API version `2026-03-11`.

If either setting is missing, contract validation still runs but Notion writes
are skipped.

## Security

The workflow uses `pull_request_target` so metadata can be validated for fork
PRs. It always checks out the trusted default branch and never checks out or
executes PR code.

Notion credentials and GitHub write-back are used only for:

- same-repository PRs; or
- `OWNER` / `MEMBER` / `COLLABORATOR` authored Issues/PRs.

Untrusted external Issues/PRs are validation-only.

## Upsert and reverse link

Exactly one Matrix row is matched by `REQ-ID + TC-ID`.

- one match: update it;
- no match: create only when `Knowledge Node URL` is present;
- duplicate matches: fail closed.

After a successful Notion write, the workflow creates or updates a single bot
comment containing the Matrix record URL. This gives direct navigation in both
directions without making Notion edits mutate engineering state back into
GitHub.

## Recommended workflow

1. Create the Matrix Requirement/Test Case first (or provide Knowledge Node URL
   for first-write creation).
2. Put the same `REQ-ID / TC-ID` in the Issue and implementing PR.
3. Let CI/HIL/physical tests produce versioned evidence.
4. Update `Evidence Path`, configuration fields and explicit `Result`.
5. If the PR head changes, re-run the evidence before restoring `PASS`.
