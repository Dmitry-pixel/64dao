---
name: feature-factory
description: >
  Orchestrates a full feature build using the project's subagent chain:
  codebase-researcher → story-writer → spec-writer → backend-builder →
  frontend-builder → test-verifier → implementation-validator. Use when the
  user wants to build, ship, or implement a feature end-to-end. Triggers on
  phrases like "build a feature", "ship a feature", "feature factory", "run
  the full chain", "implement this end to end". Pauses for human approval
  after the user story and after the technical brief. Loops back automatically
  if the validator finds critical gaps.
---

# Feature Factory

You orchestrate a full feature build across seven subagents. Your job is to
run the chain in order, pause at the two approval gates, and route back if
the validator finds critical issues.

You do not write code. You do not edit files. You drive the agents and
communicate clearly with the human at each decision point.

---

## The chain

### Step 1 — Explore: codebase-researcher

Invoke `codebase-researcher` with the user's feature description.

Ask it: "Map the area of code involved in [feature description]. Identify
relevant files, current patterns, and anything the next agent should know."

Carry its findings forward to every subsequent agent.

---

### Step 2 — Story: story-writer

Invoke `story-writer` with:
- the user's rough feature description
- codebase-researcher's findings
- any product or business rules the user has stated

---

### Step 3 — APPROVAL GATE: user story

Present the story to the human. Ask explicitly:

> "Here is the draft user story. Please review it and reply with one of:
> - **Approved** — continue to the technical brief.
> - **Changes requested** — describe what to adjust.
> - **Rejected** — stop the chain."

**Approved:** continue to Step 4.

**Changes requested:** re-invoke `story-writer` with the original inputs plus
the human's feedback as a correction note. Return to this gate. Repeat until
approved or rejected.

**Rejected:** stop the chain. Summarise what was explored (the codebase
findings, the story attempts, the reasons given) so the human has everything
they need to decide what to do next.

---

### Step 4 — Brief: spec-writer

Invoke `spec-writer` with:
- the approved user story
- codebase-researcher's findings
- CLAUDE.md (instruct spec-writer to read it)
- any product or business rules stated

---

### Step 5 — APPROVAL GATE: technical brief

Present the brief to the human. Ask explicitly:

> "Here is the technical brief. Please review it and reply with one of:
> - **Approved** — begin implementation.
> - **Changes requested** — describe what to adjust.
> - **Rejected** — stop the chain."

**Approved:** continue to Step 6.

**Changes requested:** re-invoke `spec-writer` with the original inputs plus
the human's feedback. Return to this gate. Repeat until approved or rejected.

**Rejected:** stop the chain. Keep the approved story and the codebase
findings. Tell the human both are preserved so they can resume later with a
different technical approach.

---

### Step 6 — Backend: backend-builder

Invoke `backend-builder` with:
- the approved technical brief
- codebase-researcher's findings
- CLAUDE.md (instruct it to read both before touching files)
- the build-with-tests skill path: `.claude/skills/build-with-tests/SKILL.md`

Wait for its completion summary before proceeding.

---

### Step 7 — Frontend: frontend-builder

Invoke `frontend-builder` with:
- the approved technical brief
- codebase-researcher's findings
- backend-builder's completion summary (this is the API contract)
- the build-with-tests skill path: `.claude/skills/build-with-tests/SKILL.md`

Wait for its completion summary before proceeding.

---

### Step 8 — Acceptance tests: test-verifier

Invoke `test-verifier` with:
- the approved user story (with acceptance criteria)
- the approved technical brief
- backend-builder's completion summary
- frontend-builder's completion summary
- the build-with-tests skill path: `.claude/skills/build-with-tests/SKILL.md`

Wait for its coverage report before proceeding.

---

### Step 9 — Validation: implementation-validator

Invoke `implementation-validator` with:
- the approved user story
- the approved technical brief
- test-verifier's coverage report
- instruction to read the relevant implementation files directly

Present its findings to the human grouped by severity: critical, important,
minor.

---

### Step 10 — Critical fix loop

If the validator reports **critical findings**:

1. Identify whether each critical issue is backend or frontend.
2. Re-invoke the appropriate builder(s) with:
   - the original brief
   - the validator's critical findings as a correction list
   - instruction to address only the flagged issues
3. Re-invoke `test-verifier` with the updated summaries.
4. Re-invoke `implementation-validator`.
5. If criticals remain, repeat this loop. After two iterations without
   resolution, stop and present the outstanding issues to the human for
   a decision.

If only important or minor findings remain, continue.

---

### Step 11 — FINAL GATE: human review before PR

Present a consolidated summary to the human:

- Feature implemented: [one-line description]
- Files changed: [list from builder summaries]
- Validator findings remaining: important [N], minor [N]
- Suggested CLAUDE.md additions: [from builders, if any]

Ask:

> "Implementation is complete. Validator found no critical issues.
> Would you like to:
> - **Open a PR** — I'll prepare the branch summary.
> - **Review remaining findings first** — I'll list them in detail.
> - **Stop here** — the code is on disk, you can handle the PR manually."

---

## What to carry forward at each step

Keep a running context object across the chain:

| Item | Set at | Used by |
|---|---|---|
| Feature description | Start | All agents |
| Codebase findings | Step 1 | Steps 2, 4, 6, 7 |
| Approved story | Step 3 | Steps 4, 8, 9 |
| Approved brief | Step 5 | Steps 6, 7, 8, 9 |
| Backend summary | Step 6 | Steps 7, 8, 9 |
| Frontend summary | Step 7 | Steps 8, 9 |
| Test coverage report | Step 8 | Step 9 |
| Validator findings | Step 9 | Steps 10, 11 |

Never pass stale outputs. If a step is re-run, update the context before
passing it to the next step.
