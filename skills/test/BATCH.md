# Batch — the fastest way to run, found once per stack

Read by `/clio:test` step 1 before the first run on a stack. Everything here is about *how* cases run,
never about *what* they test.

How cases run costs more than anything else here, whatever the stack: a runner that boots something
(a JVM, a framework, a container, a bundler) pays it once per command. One example, measured on a
Maven + Spring Boot repo: 8 cases each as its own `mvn` took 72 s (boot ~7 s every time, test bodies
under 0.5 s); the same 8 in one `mvn` took 11 s. So **before the first run** — new cases, and
just as much existing ones (a re-run, cases written before 4.2.0) — check for a `Batch:` line:

- **A `Batch:` line in `.claude/rules/*.md` already covers this stack** → use it, skip the rest. Each
  case's `Command` is that template with `{tests}` replaced by the one test it runs — word for word,
  or the script will not merge it (it then runs alone, correct but slow).
- **The cases already exist and no `Batch:` line does** → do the steps below now, before
  running anything, and write the template **in the exact form the existing commands already use**
  (`mvn -pl cafefin-api test -Dtest={tests}` for commands reading `mvn -pl cafefin-api test -Dtest=X#y`):
  those cases then merge as they are — no case edited, no approval voided. A case that does not fit the
  template runs alone; say which.
- **None yet** → find it, before designing commands:
  1. **Identify the stack and its runner from the repo**, not from habit: the manifests present
     (`pom.xml`, `build.gradle*`, `package.json` scripts + `jest`/`vitest` config, `pyproject.toml` /
     `pytest.ini`, `go.mod`, `Cargo.toml`, `*.csproj` / `*.sln`, `composer.json`…), the test config in
     them, and how CI invokes the tests.
  2. Look the runner up in **Context7** (web search if it has nothing; say which): how one command
     selects several named tests (`-Dtest=A#m,B#n`, `--tests`, `-t`, `-k "a or b"`, `-run '^(A|B)$'`);
     where it writes a **machine-readable report** — the script reads JUnit XML, which most runners
     emit (Surefire by default; jest via `jest-junit`, pytest `--junitxml`, Go `gotestsum
     --junitfile`, Rust `cargo nextest` JUnit profile, .NET `--logger junit`); no JUnit XML → no
     batch line. How to repeat a test **inside one process** so the report shows repetitions of the
     same call — JUnit 5 `@RepeatedTest(n)` (`name()[k]`), Go `-count=n` (the same name n times);
     anything else (`pytest-repeat`'s `name[k-n]`, parameter sets) reads as different calls and the
     case falls back to its own command. What keeps a heavy fixture warm across tests
     (Spring's test-context cache — same config, one boot; Testcontainers reuse).
  3. **Measure**, don't assume: one existing test on its own, then several in one command. Show both
     numbers.
  4. Propose the line for `.claude/rules/<stack>.md` and ask before writing it. Format: `- Batch: ` then the command template in backticks, then `· join: ` the separator in backticks, then `· report: ` the glob of the XML report in backticks. For example, a Maven repo uses `mvn -pl cafefin-api test -Dtest={tests}`, join `,`, and report glob `cafefin-api/target/surefire-reports/TEST-*.xml`.
     The template is the case commands' own text with the test id cut out. Copy it from the cases, never from this example: one extra flag (`-q`) and not a single case matches. `run-task` prints a `note:` with the template the commands actually fit when two or more cases end up running alone. `{tests}` is where the joined test ids go, `join` the separator the runner wants, `report` the glob of the JUnit XML it leaves. Write one line per runner (per module when modules test apart).
  5. No way to select several tests in one command, no XML report, or the measurement shows no gain
     → no line; say why. Cases then run one command each, as before.

## Repeat

- **Repeat without restarting.** A `concurrency` case needs `repeat` ≥ 20: write the test to repeat
  itself (`@RepeatedTest(20)`, `-count=20`) so the report shows 20 entries — the script counts them.
  A test that does not repeat itself still works: the script sees fewer entries than `repeat` and
  runs that case alone, 20 times over, at 20 boots' cost. An existing concurrency test written that
  way → propose the one-line change (`@Test` → `@RepeatedTest(20)`) before running it: the case record
  stays as it is, only the test file changes.
