# GitHub to Notion Verification Matrix sync

Tracked Issues and PRs carry explicit V&V metadata. The sync key is the pair REQ-ID + TC-ID.

Supported fields: REQ-ID, TC-ID, Knowledge Node URL, Requirement, Test Case, Verification Level, Acceptance Criteria, Evidence Path, Evidence URL, Bench / DUT, HW Revision, FW SHA, Bitstream, Result, Verification Status.

Result is one of PASS, FAIL, PARTIAL, BLOCKED, NOT RUN. PR merged and Issue closed only update GitHub lifecycle fields; they never imply PASS.

## Repository configuration

Set secret NOTION_TOKEN to a Notion integration token that can access the Engineering Evidence / Verification Matrix.
Set repository variable NOTION_VERIFICATION_DATA_SOURCE_ID to that Matrix data-source UUID.
Share the Matrix with the integration. The workflow uses Notion API version 2026-03-11.

If either setting is missing, the workflow runs contract validation and reports that Notion sync was skipped.

## Security

The workflow uses pull_request_target so public-fork PR metadata can sync. It always checks out the trusted default branch and never checks out or executes PR code.

## Upsert

One matching Matrix row is updated. No match is auto-created only when Knowledge Node URL is present. Duplicate rows fail closed.
Evidence and Result are changed only when explicitly present in metadata.
