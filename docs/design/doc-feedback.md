# Doc feedback — design note

> **Status:** Superseded by gloss (2026-11-12) · **Kind:** infrastructure (no trade study; owner, 2026-11-11)

Reading and commenting on these design documents from a phone or a computer, with each
comment going to Claude and a resolved state, is now its own project: **gloss**
(`~/dev/gloss` for now; its home repository will be on the NAS `zobar`). Monster House is
its first user. The design, decisions and build plan are in gloss's
`docs/design/gloss.md` and `docs/plan.md`.

## What was decided here (owner, 2026-11-11)

- Our own comment service on the NAS behind Tailscale, not GitHub issues or pull
  requests: the owner is moving away from GitHub.
- One service for all projects, one SQLite file per project.
- Only the owner resolves a comment; Claude marks it answered.
- Considered and set aside: GitHub issues or pull-request comments, Wiki.js, Obsidian,
  Claude Docs as the source.

## What Monster House adds when gloss goes live

- `.gloss.json` at the repository root (project id `monster-house`, the service's
  address).
- A docsify site for `docs/`, with the gloss plugin and readable requirement pages.
- Its review gates (SRR, PDR, CDR-1 to CDR-5) in gloss's configuration.

## Until then

Feedback comes through a Claude session: name the document and the place (a heading, a
scenario step such as `S3.5`, a requirement such as `EYE-012`, or a quoted phrase), and
Claude records it, works it and reports back. Claude Docs copies of the documents under
review (for example the SRR drafts) can take comments from a phone in the meantime.
