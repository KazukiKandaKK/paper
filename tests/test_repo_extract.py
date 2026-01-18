from paper2exp.core.understand.heuristics import extract_github_links


def test_repo_link_extraction():
    text = "Code: https://github.com/example/project and also https://github.com/other/repo"
    links = extract_github_links(text)
    assert links[0] == "https://github.com/example/project"
    assert links[1] == "https://github.com/other/repo"
