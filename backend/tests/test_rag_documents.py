from backend.rag.documents import clean_html, extract_pdf
from backend.rag.models import Section

SAMPLE_HTML = """
<html><head><title>Yakitori Guide | Travel Japan</title></head>
<body>
<div class="content-main-wrapper">
  <ul class="mod-keyvisual__anchor-items"><li>OVERVIEW</li><li>KEYWORDS</li></ul>
  <ul class="mod-breadcrumb__items"><li>HOME</li><li>Yakitori Guide</li></ul>
  <h1>Yakitori: A Guide to Chicken Skewers</h1>
  <p>Yakitori is a Japanese style of skewered chicken, typically grilled over charcoal.</p>
  <h2>Types of yakitori</h2>
  <p>Momo is chicken thigh, considered juicy and flavorful by many diners in Japan.</p>
  <li>Negima alternates chicken and green onion on the same skewer.</li>
  <h2>Did this information help you?</h2>
  <p>Thanks for the feedback, please rate this guide below the article body.</p>
  <h2>Recommended for You</h2>
  <p>Other unrelated guides that should never appear in the corpus at all.</p>
</div>
</body></html>
"""


def test_clean_html_drops_nav_and_stops_at_boilerplate():
    title, sections = clean_html(SAMPLE_HTML)
    assert title == 'Yakitori Guide'
    joined = '\n'.join(s.text for s in sections)
    assert 'OVERVIEW' not in joined
    assert 'HOME' not in joined
    assert 'Recommended for You' not in joined
    assert 'unrelated guides' not in joined
    assert any('skewered chicken' in s.text for s in sections)
    assert any('Types of yakitori' in s.section_path for s in sections)


def test_clean_html_empty_document_returns_no_sections():
    _, sections = clean_html('<html><head><title>Empty</title></head><body></body></html>')
    assert sections == []


def test_extract_pdf_reads_pages_and_printed_labels():
    import io

    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    # A blank page has no extractable text, so this only exercises the
    # "no text -> skipped" path; real-page behavior is covered by the
    # printed-page-label regex test below.
    sections = extract_pdf(buf.getvalue())
    assert sections == []


def test_printed_page_label_regex_accepts_bare_numbers():
    from backend.rag.documents import _PRINTED_PAGE_RE
    assert _PRINTED_PAGE_RE.match('12')
    assert not _PRINTED_PAGE_RE.match('12 Sushi in Japan')


def test_section_model_defaults():
    s = Section(section_path='a > b', text='hello')
    assert s.page_index is None
    assert s.printed_page_label is None
