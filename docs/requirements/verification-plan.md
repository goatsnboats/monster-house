# Verification plan

> **Status:** Draft for the owner (SRR package, item 3) · **Updated:** 2026-11-12 · **Events:** [verification.yaml](verification.yaml) · **Table:** [trace.md](trace.md#verification-plan)

How each requirement will be shown to be met. Every requirement names its method
(`verify`); each **verification event** below is one occasion when requirements are
checked by that method, at a stage. The checker makes sure every requirement is covered
by at least one event of its own method (today: 168 of 168).

## The methods

| Method | Means | Typical evidence |
|---|---|---|
| test | Run it and measure, against a number or an expected result | An automated test, a logged measurement |
| demonstration | Run it and watch; the owner judges | A session with the owner, notes or a short video |
| inspection | Look at it: the code, the content, the install | A review checklist, photos |
| analysis | Work it out from figures or a model | The budget check, a loudness report |

## The events by stage

| Stage | Events |
|---|---|
| 0, simulator | VE-001 brain tests · VE-002 eye renderer tests · VE-003 simulator and broker tests · VE-004 scripted pretend visits · VE-005 pretend-visit demonstration with the owner · VE-006 design inspection · VE-007 budget analysis (from Stage 1, before each CDR) |
| 1, eyes | VE-101 eye pod bench test · VE-102 Pi setup demonstration · VE-103 first window install inspection · VE-104 network inspection · VE-105 bedtime demonstration · VE-106 setup and teardown demonstration (each stage) |
| 2, ears | VE-201 radar walk test · VE-202 radar install inspection |
| 3, voice | VE-301 voice bench test · VE-302 sound level at the sidewalk · VE-303 clip loudness analysis · VE-304 content and voice install inspection · VE-305 sequence upload demonstration |
| 4, mouth | VE-401 lip bench test · VE-402 lip demonstration · VE-403 lip install inspection |
| 5, show | VE-501 dress rehearsal |

Each event's setup, method and pass criteria are in `verification.yaml`; which
requirements each covers is listed there and in `trace.md`.

## How it is used

- **SRR:** this plan exists and covers every requirement (SRR entry criterion 5).
- **PDR:** the Stage 0 events have been run; their results fill each requirement's
  `verified_by` (PDR entry criterion 7).
- **Each CDR:** that stage's events get a written procedure (CDR entry criterion 2); after
  the build they are run and recorded.
- **Results:** an automated test is named in `verified_by` (e.g.
  `brain/tests/test_moods.py::test_goodbye_after_quiet`); a demonstration or inspection
  is recorded in the stage's review folder (`docs/reviews/<review>/`).

## Open points

- Several pass criteria wait for numbers that are still TBDs (reaction times TBD-020,
  TBD-021, TBD-023; sound level TBD-026; brightness TBD-027). The events are planned now;
  their pass values are filled in as those TBDs close.
- The real-hardware timing events (VE-101, VE-201, VE-301, VE-401) depend on the latency
  model (TBD-034).
