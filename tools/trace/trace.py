"""Compliance Reporter v0 (ARC-009) — generates the REQ traceability matrix.

Usage (from the repository root)::

    pytest -q --junitxml=report.xml                    # optional, gives test results
    python -m tools.trace.trace [--out docs/traceability.md] [--junit report.xml]

Standard library only (no SOUP). The tool runs in CI, never at runtime (design decision 5).
Exit code is always 0 in v0 so that CI is not broken yet; the summary is printed to stdout.

Expected input formats
----------------------
1. ``docs/SRS.md`` — one block per requirement::

       ### REQ-002 — Plausibility check
       | Attribute | Value |
       | --- | --- |
       | Priority | Must |                      <- Must / Should / Optional / Reserved
       | Related risks | RISK-002, RISK-005 |     <- every RISK-xxx in this cell, or "–"

   A block starts at a level-3 heading ``### REQ-xxx`` and ends at the next heading of
   level 1–3. Other mentions of REQ IDs in the SRS are ignored. ``Priority | Reserved``
   marks an unused ID (e.g. REQ-021); it is listed but not evaluated.
2. pytest tests — ``tests/**/*.py``, read with ``ast``: module-level ``test*`` functions
   and ``test*`` methods of ``Test*`` classes. The first docstring line must start with
   ``TC-xxx / REQ-xxx[, REQ-yyy]:``. Tests without this tag are ignored.
3. Vitest tests — ``frontend/src/**/*.test.ts(x)``: ``it("TC-xxx / REQ-xxx: ...")`` or
   ``test(...)``. Their pass/fail status is not in the JUnit file in v0.
4. Implementation tags — a comment line ``# Implements REQ-xxx[, REQ-yyy]`` in
   ``backend/**/*.py``, ``simulator/**/*.py`` and ``tools/**/*.py`` (and
   ``// Implements REQ-xxx`` in non-test ``frontend/src/**/*.ts(x)`` files).
5. Optional JUnit XML from ``pytest --junitxml=report.xml``.

Status of a requirement (first matching rule wins)
--------------------------------------------------
- ``NO TEST``          no test references the requirement;
- ``FAILING``          at least one of its pytest tests failed or errored in the JUnit file;
- ``NOT IMPLEMENTED``  tests exist but no ``Implements`` tag references the requirement;
- ``OK``               all of its pytest tests passed in the JUnit file;
- ``OK (frontend, not in JUnit)``  only Vitest tests reference it;
- ``NO RESULT``        pytest tests exist but no passing result is available (no ``--junit``,
                       test missing from the JUnit file, or skipped). RCM-010: a requirement is
                       never reported as verified without a real test result.
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

REQ_HEADING = re.compile(r"^###\s+(REQ-\d{3})\b")
ANY_HEADING = re.compile(r"^#{1,3}\s")
PRIORITY_ROW = re.compile(r"^\|\s*Priority\s*\|\s*([^|]*?)\s*\|")
RISKS_ROW = re.compile(r"^\|\s*Related risks\s*\|([^|]*)\|")
RISK_ID = re.compile(r"RISK-\d{3}")
REQ_ID = re.compile(r"REQ-\d{3}")
REQ_LIST = r"REQ-\d{3}(?:\s*,\s*REQ-\d{3})*"
TEST_TAG = re.compile(rf"^\s*(TC-\d{{3}})\s*/\s*({REQ_LIST})\s*:")
PY_IMPLEMENTS = re.compile(rf"^\s*#\s*Implements\s+({REQ_LIST})")
TS_IMPLEMENTS = re.compile(rf"^\s*//\s*Implements\s+({REQ_LIST})")
VITEST_CALL = re.compile(
    rf"""\b(?:it|test)(?:\.\w+)*\s*\(\s*['"`]\s*(TC-\d{{3}})\s*/\s*({REQ_LIST})\s*:"""
)
PRIORITIES = ("Must", "Should", "Optional", "Reserved")

PASSED, FAILED, SKIPPED = "passed", "failed", "skipped"
STATUS_OK = "OK"
STATUS_OK_FRONTEND = "OK (frontend, not in JUnit)"
STATUS_FAILING = "FAILING"
STATUS_NO_TEST = "NO TEST"
STATUS_NOT_IMPLEMENTED = "NOT IMPLEMENTED"
STATUS_NO_RESULT = "NO RESULT"
STATUS_ORDER = (
    STATUS_OK,
    STATUS_OK_FRONTEND,
    STATUS_FAILING,
    STATUS_NO_TEST,
    STATUS_NOT_IMPLEMENTED,
    STATUS_NO_RESULT,
)


@dataclass
class Requirement:
    """One ``### REQ-xxx`` block of the SRS."""

    req_id: str
    priority: str = "Unknown"
    risks: list[str] = field(default_factory=list)

    @property
    def reserved(self) -> bool:
        """True for an intentionally unused ID such as REQ-021."""
        return self.priority == "Reserved"


@dataclass
class TestCase:
    """A tagged test function (pytest) or test name (Vitest)."""

    tc_id: str
    req_ids: list[str]
    path: str  # repository-relative, POSIX separators
    name: str  # function name, ``Class.method`` or the Vitest title
    kind: str = "pytest"  # "pytest" or "vitest"
    classname: str | None = None  # JUnit classname expected for pytest tests
    outcome: str | None = None  # passed / failed / skipped / None (no result)


@dataclass
class Row:
    """One line of the traceability matrix."""

    requirement: Requirement
    implemented_in: list[str]
    tests: list[TestCase]
    status: str


@dataclass
class Report:
    """Everything needed to render ``docs/traceability.md``."""

    rows: list[Row]
    reserved: list[str]
    warnings: list[str]
    junit_path: str | None
    junit_counts: Counter
    generated_at: datetime
    commit: str | None = None

    def must_rows(self) -> list[Row]:
        """Rows of Must requirements."""
        return [r for r in self.rows if r.requirement.priority == "Must"]

    def summary_lines(self) -> list[str]:
        """Human-readable summary, ASCII only (safe for any console encoding)."""
        must = self.must_rows()
        must_ok = sum(1 for r in must if r.status.startswith(STATUS_OK))
        counts = Counter(r.status for r in self.rows)
        status_part = ", ".join(f"{s}: {counts[s]}" for s in STATUS_ORDER if counts[s])
        lines = [
            f"{must_ok}/{len(must)} Must requirements have a passing test",
            f"{len(self.rows)} requirements evaluated ({status_part})",
        ]
        if self.junit_path:
            c = self.junit_counts
            lines.append(
                f"Test results from {self.junit_path}: {c[PASSED]} passed, "
                f"{c[FAILED]} failed, {c[SKIPPED]} skipped"
            )
        else:
            lines.append("No JUnit file given: pytest results unknown (status NO RESULT)")
        return lines


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _ids(text: str, pattern: re.Pattern[str] = REQ_ID) -> list[str]:
    """Unique IDs in order of appearance."""
    return list(dict.fromkeys(pattern.findall(text)))


def _rel(path: Path, root: Path) -> str:
    """Repository-relative POSIX path."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:  # outside the repository: never leak a local absolute path
        return path.name


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_srs(srs_path: Path) -> dict[str, Requirement]:
    """Collect requirement IDs with priority and related risks from the SRS."""
    requirements: dict[str, Requirement] = {}
    current: Requirement | None = None
    for line in _read(srs_path).splitlines():
        heading = REQ_HEADING.match(line)
        if heading:
            req_id = heading.group(1)
            current = requirements.setdefault(req_id, Requirement(req_id))
            continue
        if ANY_HEADING.match(line):
            current = None
            continue
        if current is None:
            continue
        priority = PRIORITY_ROW.match(line)
        if priority:
            value = priority.group(1).strip()
            current.priority = next(
                (p for p in PRIORITIES if value.lower().startswith(p.lower())), "Unknown"
            )
            continue
        risks = RISKS_ROW.match(line)
        if risks:
            current.risks = _ids(risks.group(1), RISK_ID)
    return dict(sorted(requirements.items()))


def _tag(docstring: str | None) -> tuple[str, list[str]] | None:
    if not docstring:
        return None
    first_line = docstring.strip().splitlines()[0]
    match = TEST_TAG.match(first_line)
    if not match:
        return None
    return match.group(1), _ids(match.group(2))


def _is_test_function(node: ast.AST) -> bool:
    return isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith(
        "test"
    )


def scan_pytest_tests(root: Path, warnings: list[str] | None = None) -> list[TestCase]:
    """Read ``TC-xxx / REQ-xxx`` tags from the docstrings of pytest tests in ``tests/``."""
    tests: list[TestCase] = []
    tests_dir = root / "tests"
    if not tests_dir.is_dir():
        return tests
    for path in sorted(tests_dir.rglob("*.py")):
        rel = _rel(path, root)
        try:
            tree = ast.parse(_read(path), filename=rel)
        except SyntaxError as exc:
            if warnings is not None:
                warnings.append(f"{rel}: not parsed ({exc.msg}, line {exc.lineno})")
            continue
        module = rel.removesuffix(".py").replace("/", ".")
        candidates: list[tuple[str | None, ast.AST]] = []
        for node in tree.body:
            if _is_test_function(node):
                candidates.append((None, node))
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                candidates.extend((node.name, item) for item in node.body if _is_test_function(item))
        for class_name, func in candidates:
            tag = _tag(ast.get_docstring(func))  # type: ignore[arg-type]
            if tag is None:
                continue
            tc_id, req_ids = tag
            tests.append(
                TestCase(
                    tc_id=tc_id,
                    req_ids=req_ids,
                    path=rel,
                    name=f"{class_name}.{func.name}" if class_name else func.name,  # type: ignore[attr-defined]
                    kind="pytest",
                    classname=f"{module}.{class_name}" if class_name else module,
                )
            )
    return tests


def scan_vitest_tests(root: Path) -> list[TestCase]:
    """Find Vitest tests whose name starts with ``TC-xxx / REQ-xxx:`` in ``frontend/src``."""
    tests: list[TestCase] = []
    src = root / "frontend" / "src"
    if not src.is_dir():
        return tests
    files = sorted({*src.rglob("*.test.ts"), *src.rglob("*.test.tsx")})
    for path in files:
        rel = _rel(path, root)
        for match in VITEST_CALL.finditer(_read(path)):
            tests.append(
                TestCase(
                    tc_id=match.group(1),
                    req_ids=_ids(match.group(2)),
                    path=rel,
                    name=f"{match.group(1)} / {match.group(2)}",
                    kind="vitest",
                )
            )
    return tests


def scan_implementations(root: Path) -> dict[str, list[str]]:
    """Map each REQ ID to the files that carry an ``Implements REQ-xxx`` comment."""
    found: dict[str, set[str]] = {}
    sources: list[tuple[Path, re.Pattern[str]]] = []
    for folder in ("backend", "simulator", "tools"):
        base = root / folder
        if base.is_dir():
            sources += [(p, PY_IMPLEMENTS) for p in base.rglob("*.py")]
    frontend = root / "frontend" / "src"
    if frontend.is_dir():
        for pattern in ("*.ts", "*.tsx"):
            sources += [
                (p, TS_IMPLEMENTS) for p in frontend.rglob(pattern) if ".test." not in p.name
            ]
    for path, pattern in sources:
        rel = _rel(path, root)
        for line in _read(path).splitlines():
            match = pattern.match(line)
            if match:
                for req_id in _ids(match.group(1)):
                    found.setdefault(req_id, set()).add(rel)
    return {req_id: sorted(paths) for req_id, paths in sorted(found.items())}


def _outcome(case: ET.Element) -> str:
    if case.find("failure") is not None or case.find("error") is not None:
        return FAILED
    if case.find("skipped") is not None:
        return SKIPPED
    return PASSED


def count_junit(junit_path: Path) -> Counter:
    """Number of passed / failed / skipped test cases as pytest reports them."""
    return Counter(_outcome(c) for c in ET.parse(junit_path).getroot().iter("testcase"))


def read_junit(junit_path: Path) -> dict[tuple[str, str], str]:
    """Read a pytest JUnit XML file: ``(classname, test name) -> outcome``.

    Parametrized cases (``test_x[a]``, ``test_x[b]``) are merged under ``test_x``:
    any failure makes the test failed, otherwise any pass makes it passed.
    """
    results: dict[tuple[str, str], str] = {}
    for case in ET.parse(junit_path).getroot().iter("testcase"):
        classname = case.get("classname", "")
        name = case.get("name", "").split("[", 1)[0]
        outcome = _outcome(case)
        key = (classname, name)
        previous = results.get(key)
        if previous == FAILED or (previous == PASSED and outcome == SKIPPED):
            continue
        results[key] = outcome
    return results


def apply_junit(tests: list[TestCase], results: dict[tuple[str, str], str]) -> None:
    """Set ``outcome`` of each pytest test from the JUnit results (unmatched stay ``None``)."""
    for test in tests:
        if test.kind != "pytest" or test.classname is None:
            continue
        func = test.name.rsplit(".", 1)[-1]
        outcome = results.get((test.classname, func))
        if outcome is None:  # e.g. pytest run with a different rootdir
            suffix = "." + test.classname
            outcome = next(
                (o for (cls, name), o in results.items() if name == func and cls.endswith(suffix)),
                None,
            )
        test.outcome = outcome


# ---------------------------------------------------------------------------
# Evaluation and output
# ---------------------------------------------------------------------------


# Implements REQ-016
# Controls RISK-010
def evaluate(tests: list[TestCase], implemented_in: list[str]) -> str:
    """Status of one requirement from its tests and implementation files (see module doc)."""
    if not tests:
        return STATUS_NO_TEST
    backend = [t for t in tests if t.kind == "pytest"]
    if any(t.outcome == FAILED for t in backend):
        return STATUS_FAILING
    if not implemented_in:
        return STATUS_NOT_IMPLEMENTED
    if not backend:
        return STATUS_OK_FRONTEND
    if all(t.outcome == PASSED for t in backend):
        return STATUS_OK
    return STATUS_NO_RESULT


# Implements REQ-016
def build_report(
    root: Path,
    srs_path: Path,
    junit_path: Path | None = None,
    now: datetime | None = None,
) -> Report:
    """Parse all inputs and evaluate every requirement of the SRS."""
    warnings: list[str] = []
    requirements = parse_srs(srs_path)
    tests = scan_pytest_tests(root, warnings) + scan_vitest_tests(root)
    implementations = scan_implementations(root)

    junit_counts: Counter = Counter()
    if junit_path is not None:
        results = read_junit(junit_path)
        junit_counts = count_junit(junit_path)
        apply_junit(tests, results)
        for test in tests:
            if test.kind == "pytest" and test.outcome is None:
                warnings.append(f"{test.path}::{test.name}: not found in the JUnit file")

    for test in tests:
        unknown = [r for r in test.req_ids if r not in requirements]
        if unknown:
            warnings.append(f"{test.path}::{test.name}: unknown {', '.join(unknown)}")
        if test.tc_id.replace("TC-", "REQ-") not in test.req_ids:
            warnings.append(
                f"{test.path}::{test.name}: {test.tc_id} does not verify a REQ with the same number"
            )
    for req_id, paths in implementations.items():
        if req_id not in requirements:
            warnings.append(f"Implements tag for unknown {req_id} in {', '.join(paths)}")
    for req in requirements.values():
        if not req.reserved and req.priority == "Unknown":
            warnings.append(f"{req.req_id}: no valid Priority row in the SRS")

    rows: list[Row] = []
    reserved: list[str] = []
    for req in requirements.values():
        if req.reserved:
            reserved.append(req.req_id)
            continue
        req_tests = [t for t in tests if req.req_id in t.req_ids]
        impl = implementations.get(req.req_id, [])
        rows.append(Row(req, impl, req_tests, evaluate(req_tests, impl)))

    return Report(
        rows=rows,
        reserved=reserved,
        warnings=warnings,
        junit_path=_rel(junit_path, root) if junit_path else None,
        junit_counts=junit_counts,
        generated_at=now or datetime.now(UTC),
        commit=_git_commit(root),
    )


def _git_commit(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _tests_cell(tests: list[TestCase]) -> str:
    if not tests:
        return "–"
    per_tc = Counter(t.tc_id for t in tests)
    parts = [f"{tc} ×{n}" for tc, n in sorted(per_tc.items())]
    backend = [t for t in tests if t.kind == "pytest"]
    outcomes = Counter(t.outcome or "no result" for t in backend)
    detail = [f"{outcomes[o]} {o}" for o in (PASSED, FAILED, SKIPPED, "no result") if outcomes[o]]
    frontend = len(tests) - len(backend)
    if frontend:
        detail.append(f"{frontend} frontend")
    return f"{', '.join(parts)} ({', '.join(detail)})"


# Implements REQ-016
def render_markdown(report: Report) -> str:
    """Render the traceability matrix as Markdown."""
    stamp = report.generated_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    out = [
        "# MediTrace — Traceability matrix",
        "",
        "> **Generated file — do not edit by hand.** Produced by the Compliance Reporter "
        "(ARC-009, REQ-016) with `python -m tools.trace.trace`. Sources: `docs/SRS.md`, "
        "`# Implements REQ-xxx` tags, `TC-xxx / REQ-xxx` test tags and the pytest JUnit result.",
        "",
        f"- Generated: {stamp}",
        f"- Source commit: `{report.commit}`" if report.commit else "- Source commit: unknown",
        f"- Test results: `{report.junit_path}`"
        if report.junit_path
        else "- Test results: none given (pytest status shown as NO RESULT)",
        "",
        "## Summary",
        "",
        *[f"- {line}" for line in report.summary_lines()],
        "",
        "## Matrix",
        "",
        "| REQ | Priority | Risks | Implemented in | Tests | Status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report.rows:
        req = row.requirement
        risks = ", ".join(req.risks) or "–"
        impl = "<br>".join(f"`{p}`" for p in row.implemented_in) or "–"
        status = row.status if row.status.startswith(STATUS_OK) else f"**{row.status}**"
        out.append(
            f"| {req.req_id} | {req.priority} | {_cell(risks)} | {impl} | "
            f"{_cell(_tests_cell(row.tests))} | {status} |"
        )
    if report.reserved:
        out += ["", f"Reserved IDs (not evaluated): {', '.join(report.reserved)}."]
    out += [
        "",
        "## Status legend",
        "",
        "| Status | Meaning |",
        "| --- | --- |",
        "| OK | At least one test, all pytest tests passed in the given JUnit result |",
        "| OK (frontend, not in JUnit) | Only Vitest tests reference the requirement; "
        "their result is not in the JUnit file in v0 |",
        "| FAILING | At least one test failed or errored |",
        "| NO TEST | No test references the requirement |",
        "| NOT IMPLEMENTED | Tests exist but no `Implements REQ-xxx` tag in the code |",
        "| NO RESULT | Tests exist but no passing result is available "
        "(not run, skipped or missing from the JUnit file) — RCM-010 |",
        "",
        "## Tagged tests",
        "",
    ]
    tagged = [r for r in report.rows if r.tests]
    all_tests = sorted(
        {id(t): t for r in tagged for t in r.tests}.values(), key=lambda t: (t.path, t.name)
    )
    if all_tests:
        out += ["| Test | Tag | Result |", "| --- | --- | --- |"]
        for t in all_tests:
            result = t.outcome or ("frontend, not in JUnit" if t.kind == "vitest" else "no result")
            out.append(
                f"| `{_cell(t.path)}::{_cell(t.name)}` | {t.tc_id} / {', '.join(t.req_ids)} | {result} |"
            )
    else:
        out.append("No tagged tests found.")
    if report.warnings:
        out += ["", "## Warnings", "", *[f"- {_cell(w)}" for w in report.warnings]]
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Always returns 0 in v0."""
    default_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="MediTrace Compliance Reporter v0 (ARC-009)")
    parser.add_argument("--root", type=Path, default=default_root, help="repository root")
    parser.add_argument("--srs", type=Path, default=None, help="SRS file (default docs/SRS.md)")
    parser.add_argument("--out", type=Path, default=None, help="output (default docs/traceability.md)")
    parser.add_argument("--junit", type=Path, default=None, help="pytest JUnit XML result file")
    args = parser.parse_args(argv)

    root: Path = args.root
    srs = args.srs or root / "docs" / "SRS.md"
    out = args.out or root / "docs" / "traceability.md"
    try:
        if not srs.is_file():
            print(f"ERROR: SRS not found: {srs}")
            return 0
        junit = args.junit
        if junit is not None and not junit.is_file():
            print(f"WARNING: JUnit file not found, continuing without results: {junit}")
            junit = None
        report = build_report(root, srs, junit)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_markdown(report), encoding="utf-8", newline="\n")
    except Exception as exc:  # noqa: BLE001 - v0 must never break CI
        print(f"ERROR: compliance reporter failed: {exc!r}")
        return 0
    for line in report.summary_lines():
        print(line)
    if report.warnings:
        print(f"{len(report.warnings)} warning(s), see {_rel(out, root)}")
    print(f"Written: {_rel(out, root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
