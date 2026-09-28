#!/usr/bin/env python3
"""selftest_junit.py — cliolib.junit against the report shapes real runners write (Surefire,
node --test, vitest, PHPUnit, gotestsum) and the batch-template edge cases seen in use.
Prints OK or each mismatch; exit 1 on any."""
import collections
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cliolib import junit  # noqa: E402

bad = 0


def eq(got, want, what):
    global bad
    if got != want:
        print("FAIL %s\n--- got\n%s\n--- want\n%s" % (what, got, want))
        bad = 1


def write(name, text):
    os.makedirs(os.path.dirname(name) or ".", exist_ok=True)
    with open(name, "w", encoding="utf-8") as f:
        f.write(text)


def rows(path):
    return [tuple(r) for r in junit.junit([path])]


with tempfile.TemporaryDirectory() as d:
    os.chdir(d)

    # --- junit(): class, test, status (0 pass · 1 failure/error · 2 skipped), rep (1 repetition · 0 param set)

    # Surefire (Maven): self-closing pass, @RepeatedTest `()[k]`, @ParameterizedTest `(String)[k]`, a
    # failure, an error, a skipped one, and a passing test whose captured log happens to contain `<error>`.
    write("surefire.xml", """<testsuite name="com.a.OrderTest" tests="8">
  <testcase name="createsOrder" classname="com.a.OrderTest" time="0.4"/>
  <testcase name="race()[1]" classname="com.a.OrderTest" time="0.01"/>
  <testcase name="race()[2]" classname="com.a.OrderTest" time="0.01"/>
  <testcase name="sizes(String)[1]" classname="com.a.OrderTest" time="0.01"/>
  <testcase name="rejectsZero" classname="com.a.OrderTest" time="0.1">
    <failure message="expected 400" type="org.opentest4j.AssertionFailedError"><![CDATA[boom]]></failure>
  </testcase>
  <testcase name="crashes" classname="com.a.OrderTest" time="0.1">
    <error message="NPE" type="java.lang.NullPointerException"/>
  </testcase>
  <testcase name="later" classname="com.a.OrderTest" time="0"><skipped/></testcase>
  <testcase name="logsXml" classname="com.a.OrderTest" time="0.2">
    <system-out><![CDATA[parsed <error code="7"/> from the feed
<failure>not ours</failure> either]]></system-out>
  </testcase>
</testsuite>
""")
    eq(rows("surefire.xml"), [
        ("com.a.OrderTest", "createsOrder", 0, 1),
        ("com.a.OrderTest", "race", 0, 1),
        ("com.a.OrderTest", "race", 0, 1),
        ("com.a.OrderTest", "sizes", 0, 0),
        ("com.a.OrderTest", "rejectsZero", 1, 1),
        ("com.a.OrderTest", "crashes", 1, 1),
        ("com.a.OrderTest", "later", 2, 1),
        ("com.a.OrderTest", "logsXml", 0, 1)], "junit: Surefire")

    # node --test --test-reporter=junit: classname is always "test"
    write("node.xml", """<testsuites>
\t<testcase name="lowercases" time="0.000571" classname="test" file="/p/test/slug.test.mjs"/>
\t<testcase name="trimsDashes" time="0.000119" classname="test" file="/p/test/slug.test.mjs">
\t\t<failure type="testCodeFailure" message="Expected values to be strictly equal"/>
\t</testcase>
</testsuites>
""")
    eq(rows("node.xml"), [("test", "lowercases", 0, 1), ("test", "trimsDashes", 1, 1)], "junit: node --test")

    # vitest --reporter=junit: classname is the file; tests the -t filter left out come back <skipped/>
    write("vitest.xml", """<testsuites><testsuite name="test/slug.vitest.test.mjs">
    <testcase classname="test/slug.vitest.test.mjs" name="lowercases" time="0.001">
    </testcase>
    <testcase classname="test/slug.vitest.test.mjs" name="emptyStaysEmpty" time="0">
        <skipped/>
    </testcase>
</testsuite></testsuites>
""")
    eq(rows("vitest.xml"), [("test/slug.vitest.test.mjs", "lowercases", 0, 1),
                            ("test/slug.vitest.test.mjs", "emptyStaysEmpty", 2, 1)], "junit: vitest")

    # PHPUnit --log-junit: nested suites, extra attributes before classname
    write("phpunit.xml", """<testsuites><testsuite name="tests"><testsuite name="SlugTest" file="/app/tests/SlugTest.php">
    <testcase name="testLowercases" file="/app/tests/SlugTest.php" line="7" class="SlugTest" classname="SlugTest" assertions="1" time="0.0005"/>
</testsuite></testsuite></testsuites>
""")
    eq(rows("phpunit.xml"), [("SlugTest", "testLowercases", 0, 1)], "junit: PHPUnit")

    # gotestsum --junitfile: classname is the package path; -count=3 repeats the same name
    write("go.xml", """<testsuites><testsuite name="example.com/app/imageconv">
    <testcase classname="example.com/app/imageconv" name="TestPNGToJPEG" time="0.01"></testcase>
    <testcase classname="example.com/app/imageconv" name="TestPNGToJPEG" time="0.01"></testcase>
    <testcase classname="example.com/app/imageconv" name="TestPNGToJPEG" time="0.01"></testcase>
</testsuite></testsuites>
""")
    eq(collections.Counter(rows("go.xml")), collections.Counter({("example.com/app/imageconv", "TestPNGToJPEG", 0, 1): 3}),
       "junit: gotestsum -count")

    # --- batch_id(): the test id a command fills a template with — word for word, one plain id
    T = "mvn -pl api test -Dtest={tests}"
    eq(junit.batch_id("mvn -pl api test -Dtest=OrderTest#createsOrder", T), "OrderTest#createsOrder", "batch_id: plain")
    eq(junit.batch_id("mvn -q -pl api test -Dtest=OrderTest#x", T), None, "batch_id: an extra -q is another command")
    eq(junit.batch_id("mvn -pl api test -Dtest=A#x,B#y", T), None, "batch_id: a list is not one id")
    eq(junit.batch_id("mvn -pl api test -Dtest=A#x+y", T), None, "batch_id: a + list is not one id")
    eq(junit.batch_id("mvn -pl api test -Dtest=A*", T), None, "batch_id: a pattern is not one id")
    eq(junit.batch_id("go test ./img -run '^(TestA)$'", "go test ./img -run '^({tests})$'"), "TestA",
       "batch_id: template with a suffix")

    # --- batches(): the Batch: lines of .claude/rules/*.md
    write(".claude/rules/java.md", """# Java
- Batch: `mvn -pl api test -Dtest={tests}` · join: `,` · report: `api/target/surefire-reports/TEST-*.xml`
<!-- - Batch: `mvn -q test -Dtest={tests}` · join: `,` · report: `x.xml` -->
Batch: `go test ./... -run '^({tests})$'` · join: `|` · report: `.clio/go.xml`
- Batch: `no placeholder here` · report: `y.xml`
""")
    eq(junit.batches(), [("mvn -pl api test -Dtest={tests}", ",", "api/target/surefire-reports/TEST-*.xml"),
                         ("go test ./... -run '^({tests})$'", "|", ".clio/go.xml")],
       "batches: live lines only, fields split")

    # --- suggest_template(): the template a set of commands that ran alone would fit
    eq(junit.suggest_template(["mvn -pl api test -Dtest=A#x", "mvn -pl api test -Dtest=B#y"]),
       "mvn -pl api test -Dtest={tests}", "suggest_template: mvn")
    eq(junit.suggest_template(["go test ./img -run '^(TestA)$'", "go test ./img -run '^(TestBee)$'"]),
       "go test ./img -run '^({tests})$'", "suggest_template: prefix and suffix")
    eq(junit.suggest_template(["mvn test -Dtest=A#x"]), None, "suggest_template: one command is no pattern")

    os.chdir("/")

if bad == 0:
    print("OK")
sys.exit(bad)
