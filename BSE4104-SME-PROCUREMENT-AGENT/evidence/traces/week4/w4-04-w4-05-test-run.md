Week 4 Test Evidence — W4-04 and W4-05
Owner: Akisa Maria Ashley (Quality/Security Lead)
Date: 2026-09-30
Command run: `python3 -m pytest tests/test_tool_failure_and_authorization.py tests/workflow/test_state_machine.py -v`
W4-04 — Failure and authorization tests (5 tests, all passing)
Covers the four required scenarios:
Missing parameter -> clear error, no crash
Unauthorized request -> refused and logged (interim: no approval-granting tool
is exposed at all, since the state machine's real role check did not exist
until W4-05 landed the same day — see note below)
Unavailable service -> mocked outage, clean failure response, no hang
Unexpected tool response -> confirmed gap, documented not faked: the
dispatcher performs no output validation at all; a malformed tool response
currently passes through unflagged. Raised with the team as a fix needed
before Week 7 evaluation.
W4-05 — State-machine tests (12 tests, all passing)
Includes the required attempted illegal DRAFT -> APPROVED transition test
(`IllegalTransitionTests::test_draft_cannot_be_approved_directly`), plus
coverage of every other illegal transition, the blocking-flags-unresolved
refusal path, and approval-identity integrity checks.
`state_machine.py` was drafted with AI assistance to unblock this task while
Isaac Alinda's machine was unavailable — disclosed in the AI Engineering Log,
entry #3. Pending his review before being treated as final.
Raw test run log
```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: BSE4104-SME-PROCUREMENT-AGENT
collecting ... collected 17 items

tests/test_tool_failure_and_authorization.py::MissingParameterTests::test_missing_required_parameter_returns_clear_error_not_a_crash PASSED [  5%]
tests/test_tool_failure_and_authorization.py::UnauthorizedRequestTests::test_attempted_approval_call_is_blocked_and_traced PASSED [ 11%]
tests/test_tool_failure_and_authorization.py::UnauthorizedRequestTests::test_no_approval_capability_is_exposed_to_the_model PASSED [ 17%]
tests/test_tool_failure_and_authorization.py::UnavailableServiceTests::test_tool_raising_an_unexpected_exception_returns_execution_error PASSED [ 23%]
tests/test_tool_failure_and_authorization.py::MalformedToolResponseTests::test_non_serializable_tool_output_currently_passes_through_unvalidated PASSED [ 29%]
tests/workflow/test_state_machine.py::LegalTransitionTests::test_draft_can_be_submitted_when_no_blocking_flags PASSED [ 35%]
tests/workflow/test_state_machine.py::LegalTransitionTests::test_pending_approval_can_be_approved_with_recorded_approver PASSED [ 41%]
tests/workflow/test_state_machine.py::LegalTransitionTests::test_pending_approval_can_be_queried_with_reason PASSED [ 47%]
tests/workflow/test_state_machine.py::LegalTransitionTests::test_pending_approval_can_be_rejected_with_reason PASSED [ 52%]
tests/workflow/test_state_machine.py::IllegalTransitionTests::test_approved_requisition_cannot_be_approved_again PASSED [ 58%]
tests/workflow/test_state_machine.py::IllegalTransitionTests::test_draft_cannot_be_approved_directly PASSED [ 64%]
tests/workflow/test_state_machine.py::IllegalTransitionTests::test_draft_cannot_be_rejected_directly PASSED [ 70%]
tests/workflow/test_state_machine.py::IllegalTransitionTests::test_rejected_requisition_cannot_later_be_approved PASSED [ 76%]
tests/workflow/test_state_machine.py::IllegalTransitionTests::test_submit_from_non_draft_state_is_illegal PASSED [ 82%]
tests/workflow/test_state_machine.py::BlockingFlagTests::test_submission_refused_while_blocking_flags_unresolved PASSED [ 88%]
tests/workflow/test_state_machine.py::ApprovalIntegrityTests::test_approve_rejects_empty_approver_id PASSED [ 94%]
tests/workflow/test_state_machine.py::ApprovalIntegrityTests::test_approve_rejects_none_approver_id PASSED [100%]

============================== 17 passed in 0.09s ==============================
```
