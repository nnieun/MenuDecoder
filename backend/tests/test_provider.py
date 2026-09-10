"""Unit tests for backend/provider.py that never hit the network or OpenAI.

Real end-to-end calls (extract/describe/images/answer against the live
OpenAI API) are not exercised here - they cost money and need
OPENAI_API_KEY in backend/.env. Those are verified manually; see
backend/rag/README.md's "다음 단계" note for how.
"""
from unittest.mock import patch

from backend.config import Settings
from backend.models import Analysis, ChatMessage, MenuItem
from backend.provider import (
    OpenAIProvider,
    _citation,
    _citations_from,
    _context_block,
    _looks_like_image,
)
from backend.rag.chunking import chunk_document
from backend.rag.models import Document, Section, now
from backend.rag.retriever import Retriever


def make_provider():
    settings = Settings(ai_provider='openai', openai_api_key='test-key-not-real')
    return OpenAIProvider(settings)


def make_retriever():
    doc = Document(
        source_id='doc-1', title='Test Doc', doc_type='html', url='https://example.com/a',
        language='en', publisher='Test', license_note='n', collected_at=now(), content_hash='h',
        sections=[Section(section_path='Test Doc > Intro', text='Ramen is a Japanese noodle soup with broth.')],
    )
    return Retriever([doc], chunk_size=256)


def test_citation_maps_chunk_and_document_fields():
    retriever = make_retriever()
    chunk = retriever.chunks[0]
    document = retriever.document_for(chunk.source_id)
    citation = _citation(chunk, document)
    assert citation.source_id == 'doc-1'
    assert citation.document_title == 'Test Doc'
    assert str(citation.source_url) == 'https://example.com/a'
    assert citation.chunk_id == chunk.chunk_id
    assert citation.section_path == chunk.section_path


def test_citations_from_drops_ids_the_model_invented():
    retriever = make_retriever()
    chunks = retriever.chunks
    real_id = chunks[0].chunk_id
    result = _citations_from([real_id, 'not-a-real-chunk-id'], chunks, retriever)
    assert len(result) == 1
    assert result[0].chunk_id == real_id


def test_citations_from_empty_when_nothing_valid():
    retriever = make_retriever()
    assert _citations_from(['bogus'], retriever.chunks, retriever) == []


def test_context_block_includes_document_title_and_text():
    retriever = make_retriever()
    block = _context_block(retriever.chunks, retriever)
    assert 'Test Doc' in block
    assert 'Ramen is a Japanese noodle soup' in block


def test_context_block_empty_when_no_chunks():
    retriever = make_retriever()
    assert '관련 문서를 찾지 못했' in _context_block([], retriever)


def test_looks_like_image_rejects_non_http_scheme():
    assert _looks_like_image('ftp://example.com/pic.jpg') is False


def test_looks_like_image_false_on_network_error():
    import httpx
    with patch('backend.provider.httpx.Client') as client_cls:
        client_cls.return_value.__enter__.side_effect = httpx.ConnectError('boom')
        assert _looks_like_image('https://example.com/pic.jpg') is False


def test_answer_disambiguates_without_calling_the_model():
    provider = make_provider()
    item_a = MenuItem(original_name='A', translated_name='가')
    item_b = MenuItem(original_name='B', translated_name='나')
    analysis = Analysis(mode='openai', items=[item_a, item_b])
    message = ChatMessage(role='user', content='그거 매워?', referenced_item_ids=[])
    with patch.object(provider, 'client') as client:
        result = provider.answer(analysis, message, charge=lambda: None)
    client.responses.parse.assert_not_called()
    assert '메뉴 이름을 알려' in result.content
    assert result.referenced_item_ids == []


def test_answer_defaults_to_single_item_without_asking():
    provider = make_provider()
    item_a = MenuItem(original_name='A', translated_name='가')
    analysis = Analysis(mode='openai', items=[item_a])
    message = ChatMessage(role='user', content='그거 매워?', referenced_item_ids=[])
    charged = []
    with patch.object(provider, 'client') as client:
        from backend.provider import AnswerOutput
        client.responses.parse.return_value.output_parsed = AnswerOutput(content='안 매워요.', supporting_chunk_ids=[])
        result = provider.answer(analysis, message, charge=lambda: charged.append(1))
    assert charged == [1]
    assert result.referenced_item_ids == [item_a.item_id]
    assert result.content == '안 매워요.'


def test_chunk_document_used_by_retriever_matches_chunking_module():
    # Sanity: Retriever's index is built from the same chunker the RAG
    # README documents, not a second parallel implementation.
    doc = Document(
        source_id='x', title='X', doc_type='html', url='https://example.com', language='en',
        publisher='p', license_note='n', collected_at=now(), content_hash='h',
        sections=[Section(section_path='X > S', text='Some text about yakitori skewers.')],
    )
    retriever = Retriever([doc], chunk_size=256)
    expected = chunk_document(doc, chunk_size=256)
    assert [c.chunk_id for c in retriever.chunks] == [c.chunk_id for c in expected]
