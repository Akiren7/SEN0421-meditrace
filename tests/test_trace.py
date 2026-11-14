"""Unit tests for the Compliance Reporter v0 (ARC-009, IEEE 1012 integrity level 2)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import UTC, datetime  # noqa: E402
from textwrap import dedent  # noqa: E402

from tools.trace import trace  # noqa: E402

SAMPLE_SRS = dedent(
    """\
    # SRS

    ## 3. Requirements

    Mentions of REQ-099 outside a block are ignored.

    ### REQ-001 — Simulation

    | Attribute | Value |
    | --- | --- |
    | Priority | Must |
    | Related risks | – |

    ### REQ-002 — Plausibility check

    | Attribute | Value |
    | --- | --- |
    | Statement | Text that mentions RISK-009 is not a risk link. |
    | Priority | Must |
    | Related risks | RISK-002, RISK-005 |

    ### REQ-014 — Chart

    | Attribute | Value |
    | --- | --- |
    | Priority | Should |
    | Related risks | – |

    ### REQ-017 — Trend alert

    | Attribute | Value |
    | --- | --- |
    | Priority | Optional |
    | Related risks | – |

    ### REQ-021 — Reserved

    | Attribute | Value |
    | --- | --- |
    | Priority | Reserved |

    ## 4. Traceability
    | Priority | Must |
    """
)

SAMPLE_TESTS = dedent(
    '''\
    def test_plausibility_hr_350():
        """TC-002 / REQ-002: HR 350 is marked invalid.

        More text that mentions REQ-001 must not create a link.
        """


    def test_two_requirements():
        """TC-002 / REQ-002, REQ-014: one test may verify more than one requirement."""


    def test_without_tag():
        """Just a smoke test, no traceability tag."""


    def test_without_docstring():
        pass


    def helper_not_a_test():
        """TC-001 / REQ-001: not collected because the name does not start with test."""


    class TestGroup:
        def test_in_class(self):
            """TC-014 / REQ-014: tests inside Test* classes are read as well."""
    '''
)

BACKEND_SOURCE = dedent(
    """\
    # Implements REQ-002
    # Controls RISK-002
    def validate(reading):
        return True

    # Not tagged "Implements REQ-001" on purpose
    """
)


def make_repo(tmp_path: Path) -> Path:
    """Create a tiny fake repository with an SRS, one test file and one source file."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "SRS.md").write_text(SAMPLE_SRS, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_sample.py").write_text(SAMPLE_TESTS, encoding="utf-8")
    source_dir = tmp_path / "backend" / "app" / "ingestion"
    source_dir.mkdir(parents=True)
    (source_dir / "validation.py").write_text(BACKEND_SOURCE, encoding="utf-8")
    return tmp_path


def write_junit(path: Path, cases: dict[str, str]) -> Path:
    """Write a minimal pytest-style JUnit XML file; ``cases`` maps name -> outcome."""
    body = []
    for name, outcome in cases.items():
        inner = {
            "passed": "",
            "failed": '<failure message="assert False">trace</failure>',
            "skipped": '<skipped message="later" />',
        }[outcome]
        classname = "tests.test_sample.TestGroup" if name == "test_in_class" else "tests.test_sample"
        body.append(f'<testcase classname="{classname}" name="{name}" time="0.01">{inner}</testcase>')
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest">'
        + "".join(body)
        + "</testsuite></testsuites>",
        encoding="utf-8",
    )
    return path


def rows_by_id(report: trace.Report) -> dict[str, trace.Row]:
    return {row.requirement.req_id: row for row in report.rows}


ALL_PASS = {
    "test_plausibility_hr_350": "passed",
    "test_two_requirements": "passed",
    "test_without_tag": "passed",
    "test_without_docstring": "passed",
    "test_in_class": "passed",
}


def test_srs_ids_priorities_and_risks_are_parsed(tmp_path):
    """TC-016 / REQ-016: requirement IDs, priorities and related risks are parsed from a sample SRS."""
    repo = make_repo(tmp_path)
    reqs = trace.parse_srs(repo / "docs" / "SRS.md")

    assert list(reqs) == ["REQ-001", "REQ-002", "REQ-014", "REQ-017", "REQ-021"]
    assert reqs["REQ-001"].priority == "Must"
    assert reqs["REQ-014"].priority == "Should"
    assert reqs["REQ-017"].priority == "Optional"
    assert reqs["REQ-021"].reserved
    assert reqs["REQ-002"].risks == ["RISK-002", "RISK-005"]
    assert reqs["REQ-001"].risks == []


def test_tags_are_read_from_test_docstrings_untagged_ignored(tmp_path):
    """TC-016 / REQ-016: TC/REQ tags come from the first docstring line; untagged tests are ignored."""
    repo = make_repo(tmp_path)
    tests = trace.scan_pytest_tests(repo)

    found = {t.name: (t.tc_id, t.req_ids) for t in tests}
    assert found == {
        "test_plausibility_hr_350": ("TC-002", ["REQ-002"]),
        "test_two_requirements": ("TC-002", ["REQ-002", "REQ-014"]),
        "TestGroup.test_in_class": ("TC-014", ["REQ-014"]),
    }
    assert {t.classname for t in tests} == {"tests.test_sample", "tests.test_sample.TestGroup"}


def test_implements_tags_are_collected_per_requirement(tmp_path):
    """TC-016 / REQ-016: '# Implements REQ-xxx' comments map requirements to source files."""
    repo = make_repo(tmp_path)

    assert trace.scan_implementations(repo) == {
        "REQ-002": ["backend/app/ingestion/validation.py"]
    }


def test_must_requirement_without_test_is_no_test(tmp_path):
    """TC-016 / REQ-016: a Must requirement that no test references is reported as NO TEST."""
    repo = make_repo(tmp_path)
    junit = write_junit(tmp_path / "report.xml", ALL_PASS)
    report = trace.build_report(repo, repo / "docs" / "SRS.md", junit)
    rows = rows_by_id(report)

    assert rows["REQ-001"].status == trace.STATUS_NO_TEST
    assert rows["REQ-017"].status == trace.STATUS_NO_TEST
    assert rows["REQ-002"].status == trace.STATUS_OK
    assert rows["REQ-014"].status == trace.STATUS_NOT_IMPLEMENTED
    assert "REQ-021" not in rows and report.reserved == ["REQ-021"]
    assert report.summary_lines()[0] == "1/2 Must requirements have a passing test"


def test_failing_test_in_junit_makes_requirement_failing(tmp_path):
    """TC-016 / REQ-016: one failing test in the JUnit file makes the requirement FAILING."""
    repo = make_repo(tmp_path)
    junit = write_junit(tmp_path / "report.xml", {**ALL_PASS, "test_two_requirements": "failed"})
    rows = rows_by_id(trace.build_report(repo, repo / "docs" / "SRS.md", junit))

    assert rows["REQ-002"].status == trace.STATUS_FAILING
    assert rows["REQ-014"].status == trace.STATUS_FAILING


def test_no_junit_or_skipped_test_is_never_reported_ok(tmp_path):
    """TC-016 / REQ-016: (RCM-010) without a real passing result a requirement is not shown as OK."""
    repo = make_repo(tmp_path)
    without_results = rows_by_id(trace.build_report(repo, repo / "docs" / "SRS.md"))
    junit = write_junit(tmp_path / "report.xml", {**ALL_PASS, "test_plausibility_hr_350": "skipped"})
    with_skip = rows_by_id(trace.build_report(repo, repo / "docs" / "SRS.md", junit))

    assert without_results["REQ-002"].status == trace.STATUS_NO_RESULT
    assert with_skip["REQ-002"].status == trace.STATUS_NO_RESULT


def test_parametrized_cases_are_merged_and_any_failure_wins(tmp_path):
    """TC-016 / REQ-016: parametrized JUnit cases test_x[a], test_x[b] count as one test; a failure wins."""
    junit = tmp_path / "report.xml"
    junit.write_text(
        "<testsuite>"
        '<testcase classname="tests.test_a" name="test_x[a]" />'
        '<testcase classname="tests.test_a" name="test_x[b]"><failure /></testcase>'
        '<testcase classname="tests.test_a" name="test_x[c]" />'
        '<testcase classname="tests.test_a" name="test_y"><error /></testcase>'
        "</testsuite>",
        encoding="utf-8",
    )

    assert trace.read_junit(junit) == {
        ("tests.test_a", "test_x"): trace.FAILED,
        ("tests.test_a", "test_y"): trace.FAILED,
    }
    assert trace.count_junit(junit) == {trace.PASSED: 2, trace.FAILED: 2}


def test_frontend_vitest_names_count_as_tests(tmp_path):
    """TC-016 / REQ-016: Vitest names 'TC-xxx / REQ-xxx: ...' are counted as frontend tests."""
    repo = make_repo(tmp_path)
    src = repo / "frontend" / "src"
    src.mkdir(parents=True)
    (src / "Chart.tsx").write_text("// Implements REQ-001\nexport const Chart = () => null;\n", encoding="utf-8")
    (src / "Chart.test.tsx").write_text(
        'describe("chart", () => {\n'
        '  it("TC-001 / REQ-001: renders one point per reading", () => {});\n'
        "  it('no tag here', () => {});\n"
        "});\n",
        encoding="utf-8",
    )
    rows = rows_by_id(trace.build_report(repo, repo / "docs" / "SRS.md"))

    assert [t.kind for t in rows["REQ-001"].tests] == ["vitest"]
    assert rows["REQ-001"].status == trace.STATUS_OK_FRONTEND


def test_markdown_output_and_cli_exit_code(tmp_path, capsys):
    """TC-016 / REQ-016: the CLI writes the matrix table, summary and timestamp and exits with 0."""
    repo = make_repo(tmp_path)
    junit = write_junit(tmp_path / "report.xml", ALL_PASS)
    out = repo / "docs" / "traceability.md"

    exit_code = trace.main(["--root", str(repo), "--junit", str(junit), "--out", str(out)])
    text = out.read_text(encoding="utf-8")

    assert exit_code == 0
    assert "| REQ | Priority | Risks | Implemented in | Tests | Status |" in text
    assert "| REQ-001 | Must | – | – | – | **NO TEST** |" in text
    assert "1/2 Must requirements have a passing test" in text
    assert "Generated: " in text and " UTC" in text
    assert "1/2 Must requirements have a passing test" in capsys.readouterr().out


def test_cli_exits_zero_even_when_srs_is_missing(tmp_path, capsys):
    """TC-016 / REQ-016: v0 never breaks CI; a missing SRS is reported but the exit code stays 0."""
    assert trace.main(["--root", str(tmp_path)]) == 0
    assert "SRS not found" in capsys.readouterr().out


def test_generation_time_is_utc(tmp_path):
    """TC-016 / REQ-016: the generation timestamp is written in UTC (shared convention)."""
    repo = make_repo(tmp_path)
    fixed = datetime(2026, 11, 14, 9, 30, tzinfo=UTC)
    report = trace.build_report(repo, repo / "docs" / "SRS.md", now=fixed)

    assert "Generated: 2026-11-14 09:30:00 UTC" in trace.render_markdown(report)
