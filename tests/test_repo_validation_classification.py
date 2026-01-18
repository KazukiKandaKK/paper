from paper2exp.core.repo.validate import classify_git_error


def test_classify_not_found():
    assert classify_git_error(128, "Repository not found") == "not_found"


def test_classify_auth():
    assert classify_git_error(128, "Permission denied") == "auth_or_permission"
    assert classify_git_error(128, "fatal: could not read Username for 'https://github.com'") == "auth_or_permission"


def test_classify_network():
    assert classify_git_error(128, "Could not resolve host") == "network_error"
