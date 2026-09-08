# Step 3a — UPDATE mode

**Hard rules:** never rename the file (date = creation date). Never delete/rewrite existing bullets
except `## Follow-up`. Missing section → add in canonical order below. Superseded section → relabel
in place: `## [SUPERSEDED YYYY-MM-DD] <heading>`, add `— REVERTED, DO NOT RE-IMPLEMENT` if code is
gone, keep body + one `>` pointer (labelling, not deletion).

**Header:** keep original `Date:`, refresh `Updated:` to today, append (don't replace) `Commit:`.

| Section | What to do |
|---|---|
| `## Summary` | Leave alone; rewrite only if scope genuinely changed. |
| `## Files Changed` | Merge — new paths only; new reason for existing file → append `; <reason> (date)`. |
| `## Decisions` | Append. Reversed → append `Superseded YYYY-MM-DD: now Y instead of X, because …`. |
| `## Side Effects` / `## Testing Done` (dated) / `## Related` | Append. |
| `## Follow-up` | Only section edited destructively — delete completed, add new open. Empty → `none`. |
| `## Change Log` | Append `- YYYY-MM-DD — <summary> (commit <hash>)`. Create if missing, seed with `- <original Date> — initial`. |

## Hub + entry split

**Condition:** target doc is a page/route about to gain a *new* body of work that's large (many
files/decisions) AND conceptually separable from what the doc already covers — not a continuation
of an existing entry. Otherwise skip straight to `INDEX-IT.md`.

**Proactively ask, don't just silently grow the doc or silently split it.** If the condition above
is met, or a doc has accumulated multiple genuinely separable bodies of work across UPDATE runs
(several unrelated Decisions clusters, a Files Changed list spanning distinct features, a Summary
that now needs "and" three times to describe what the doc covers) — stop and ask the user whether to
split into sub-tasks now, in plain terms (name the doc, name the separable pieces you'd split it
into). Only split on their confirmation; if they decline, keep appending to the single doc as normal
and don't ask again same-session. This applies both when writing a fresh large addition (split now
instead of bolting it onto an unrelated doc) and retroactively on a doc that already got bloated
across sessions.

- **Hub** (`.claude/docs/tasks/YYYY-MM-DD_<keywords>.md`, path never changes): header + one-sentence
  `## Summary` + `## Entries` list: `- [Title](sub-tasks/YYYY-MM-DD_entry-keywords.md) — summary
  (date)`. No `Files Changed`/`Decisions`/`Testing Done` at hub level.
- **Entry** (`.claude/docs/tasks/sub-tasks/`): normal CREATE-mode doc (`CREATE-MODE.md`), own
  filename, own full history.

**Entries aren't indexed individually — only the hub is.** New entry:
1. Write entry file, CREATE template — no index.jsonl line for it.
2. Append one line to hub's `## Entries` (append-only, like Follow-up).
3. Update hub's own index.jsonl line, rolling the entry's keywords into the hub's keyword list.

Extending an existing entry → UPDATE that entry file directly; hub only changes if its
summary/keywords need a refresh.

Retroactive split → only if user explicitly asks. Move each section verbatim into `sub-tasks/`,
reduce hub to Summary+Entries, consolidate obsolete index lines into the hub's (the one exception to
append-only, done in the same session).
