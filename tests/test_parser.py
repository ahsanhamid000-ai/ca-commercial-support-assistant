from utils.cleaner import clean_text, chunk_text


def test_clean_text_removes_extra_spaces():
    raw = "Hello   world\n\n\nThis is   test"
    cleaned = clean_text(raw)
    assert "  " not in cleaned


def test_chunk_text_returns_list():
    text = "A" * 4000
    chunks = chunk_text(text, chunk_size=1000, overlap=100)
    assert isinstance(chunks, list)
    assert len(chunks) > 1
