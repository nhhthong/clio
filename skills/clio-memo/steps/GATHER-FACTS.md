# Step 2 — Gather facts

- `date +%Y-%m-%d` for today's date. Committed: `git log -1 --format=%h`. Not committed: `null`.
- Read the **entire** target doc first. Ask only what you can't derive: feature name (CREATE only),
  intent behind non-obvious changes.

## Files changed

1. List files you Edit/Write'd this run (primary source — `git diff` goes empty once committed).
2. Verify each on disk: `git status --porcelain <file>` or `git show --name-only --format= <hash>`.
   Reverted mid-session → drop it.
3. Anything in `git status --porcelain` not in your session list → show me, ask.
4. **No session context available** (compacted/fresh session)?
   ```bash
   t=$(ls -1t ~/.claude/projects/$(pwd | tr '/_' '--')/*.jsonl | head -1)
   jq -r 'select(.message.content?|type=="array") | .message.content[]?
     | select(.type=="tool_use" and (.name=="Edit" or .name=="Write" or .name=="MultiEdit"))
     | .input.file_path' "$t" | sort -u
   ```
   Still nothing → fall back to `git diff --name-only HEAD` (uncommitted) or `git show --name-only
   --format= <hash>` (committed), and note in the final report that the list came from git rather
   than the run itself.

Subagent-edited files don't appear in your tool calls — take them from its report, verify per step 2
above.

**Drop build output** — a build step rewrites tracked files you didn't edit; record the source, not
the generated copy.

The generated-vs-source map lives in `.claude/CONTEXT.md` § Source of truth. No section there →
assume nothing is generated, but check the three usual shapes before recording: build output
(`dist/`, `target/`, `build/`), code-from-code (`*.g.dart`, `*.pb.go`, generated API clients) and
asset pipelines (atlases, icon fonts). Found one → record the source, and propose the CONTEXT.md line
in WRAP-UP.

If a generated path is the *only* thing that changed, you edited the copy — stop, tell me, don't
document it.

**Scaffold run** (`composer create-project`, `flutter create`, `npx create-*`, Spring Initializr,
`go mod init` + first layout): hundreds of files nobody wrote. Record the scaffold command and the
tool version in `## Decisions`, list under `## Files Changed` only what was hand-edited afterwards,
and put the scaffold command in `files` as a single entry `scaffold:<command>` — not the tree.

## Which requirement this work serves

Every record carries `specs` (spec files) + `req` (requirement row numbers), from
`.claude/docs/specs/requirements.md`:
```bash
grep -in "<feature keyword>" .claude/docs/specs/requirements.md
```
- `req` = matching row number(s), can be several. `specs` = the `memory/*.md` file(s) that row maps
  to.
- No match → `"req":[]`, don't invent one; keep `specs` only if a spec file still governs the area,
  say so in the final report.
- Row marked ⚠️/❌ → note it (DEBT-IT.md's ledger-honesty check may need a record). ✅ means decision
  exists, not built — still write a record.
- Don't tag on keyword resemblance alone — wrong `req` misdirects future sessions worse than `[]`.
