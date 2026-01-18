from paper2exp.core.repo.discovery import RepoCandidate, RepoEvidence
from paper2exp.core.repo.select import select_repo
from paper2exp.core.repo.validate import ValidationResult


def test_repo_selection_prefers_user():
    candidates = [
        RepoCandidate(
            url="https://github.com/user/repo",
            normalized_url="https://github.com/user/repo",
            source="user_input",
            priority_rank=0,
            evidence=RepoEvidence(locator="user_input", quote="https://github.com/user/repo"),
        ),
        RepoCandidate(
            url="https://github.com/paper/repo",
            normalized_url="https://github.com/paper/repo",
            source="paper_text",
            priority_rank=1,
            evidence=RepoEvidence(locator="chunk:C1", quote="https://github.com/paper/repo"),
        ),
    ]
    validation = [
        ValidationResult(
            url="https://github.com/user/repo",
            status="ok",
            stdout_tail="",
            stderr_tail="",
        )
    ]
    selected = select_repo(candidates, validation, "prefer_user_then_paper")
    assert selected.selected_url == "https://github.com/user/repo"


def test_repo_selection_none_when_no_ok():
    candidates = [
        RepoCandidate(
            url="https://github.com/paper/repo",
            normalized_url="https://github.com/paper/repo",
            source="paper_text",
            priority_rank=0,
            evidence=RepoEvidence(locator="chunk:C1", quote="https://github.com/paper/repo"),
        )
    ]
    validation = [
        ValidationResult(
            url="https://github.com/paper/repo",
            status="not_found",
            stdout_tail="",
            stderr_tail="Repository not found",
        )
    ]
    selected = select_repo(candidates, validation, "prefer_user_then_paper")
    assert selected.selected_url is None
