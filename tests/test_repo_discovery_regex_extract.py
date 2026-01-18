from paper2exp.core.repo.discovery import extract_candidates_from_text


def test_repo_discovery_regex_extract():
    text = "Code: https://github.com/foo/bar/tree/main and https://github.com/foo/bar/blob/main/README.md"
    candidates = extract_candidates_from_text(text, source="paper_text")
    assert candidates
    assert candidates[0].normalized_url == "https://github.com/foo/bar"
