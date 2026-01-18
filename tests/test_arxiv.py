from paper2exp.core.ingest.arxiv import parse_arxiv_id


def test_parse_arxiv_id_formats():
    assert parse_arxiv_id("https://arxiv.org/abs/2511.14460") == "2511.14460"
    assert parse_arxiv_id("https://arxiv.org/pdf/2511.14460.pdf") == "2511.14460"
    assert parse_arxiv_id("2511.14460") == "2511.14460"
    assert parse_arxiv_id("arxiv:2511.14460v2") == "2511.14460"
