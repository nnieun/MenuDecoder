"""Sanity checks on the committed RAG corpus itself (backend/rag/documents/*.json).

These read only the already-collected files on disk - no network calls -
so they run in CI like any other test. Re-collecting the corpus is a
separate, manually-run step (`python -m backend.rag.collect`).
"""
from backend.rag.chunking import CHUNK_SIZES, chunk_document
from backend.rag.sources import SOURCES
from backend.rag.stats import DOCS_DIR, load_documents


def test_manifest_lists_every_configured_source():
    docs = load_documents()
    assert {d.source_id for d in docs} == {s.source_id for s in SOURCES}


def test_at_least_five_independent_documents_with_both_formats():
    docs = load_documents()
    assert len(docs) >= 5
    assert {d.doc_type for d in docs} == {'html', 'pdf'}


def test_every_document_has_language_and_provenance():
    for doc in load_documents():
        assert doc.language
        assert doc.publisher
        assert doc.content_hash
        assert doc.sections, f'{doc.source_id} has no sections'


def test_pdf_sections_carry_page_index_html_sections_do_not():
    for doc in load_documents():
        for section in doc.sections:
            if doc.doc_type == 'pdf':
                assert section.page_index is not None
            else:
                assert section.page_index is None


def test_corpus_chunks_at_every_plan_chunk_size():
    docs = load_documents()
    for size in CHUNK_SIZES:
        total = sum(len(chunk_document(doc, chunk_size=size)) for doc in docs)
        assert total > 0


def test_documents_directory_has_a_manifest():
    assert (DOCS_DIR / 'manifest.json').exists()
