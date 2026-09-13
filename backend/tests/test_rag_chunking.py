import math

import pytest

from backend.rag.chunking import CHUNK_SIZES, _tokenizer, chunk_document, overlap_for
from backend.rag.models import Document, Section, now


def make_document(text: str, section_path: str = 'Title > Section') -> Document:
    return Document(
        source_id='test-doc',
        title='Title',
        doc_type='html',
        url='https://example.com/doc',
        language='en',
        publisher='Test Publisher',
        license_note='test',
        collected_at=now(),
        content_hash='deadbeef',
        sections=[Section(section_path=section_path, text=text)],
    )


def test_overlap_matches_plan_formula():
    assert overlap_for(256) == 25
    assert overlap_for(512) == 51
    assert overlap_for(1024) == 102


def test_rejects_unlisted_chunk_size():
    doc = make_document('short text')
    with pytest.raises(ValueError):
        chunk_document(doc, chunk_size=300)


def test_short_section_produces_a_single_chunk_with_heading():
    doc = make_document('A short sentence about ramen broth.')
    chunks = chunk_document(doc, chunk_size=256)
    assert len(chunks) == 1
    assert chunks[0].section_path == 'Title > Section'
    assert chunks[0].text.startswith('Title > Section')
    assert 'ramen broth' in chunks[0].text
    assert chunks[0].chunk_size == 256
    assert chunks[0].overlap == 25


def test_chunk_token_count_matches_real_tokenizer():
    doc = make_document('Ramen is a noodle soup dish. ' * 5)
    chunks = chunk_document(doc, chunk_size=256)
    enc = _tokenizer()
    for c in chunks:
        assert c.token_count == len(enc.encode(c.text))
        assert c.token_count <= 256


def test_long_section_splits_with_overlap_and_stays_within_budget():
    # Build body text long enough to require multiple 256-token chunks.
    body = ' '.join(f'word{i}' for i in range(2000))
    doc = make_document(body)
    chunks = chunk_document(doc, chunk_size=256)
    assert len(chunks) > 1
    for c in chunks:
        assert c.token_count <= 256
    # chunk_ids are unique and encode section/chunk-size/span for citation stability
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert all(cid.startswith('test-doc:256:0:') for cid in ids)
    # Consecutive spans repeat some of the same source words (the overlap
    # window), so the tail of one chunk and the head of the next share words.
    overlap = overlap_for(256)
    tail_words = set(chunks[0].text.split()[-overlap:])
    head_words = set(chunks[1].text.split()[:overlap])
    assert tail_words & head_words or overlap == 0


def test_all_plan_chunk_sizes_are_supported():
    doc = make_document('Sentence. ' * 300)
    for size in CHUNK_SIZES:
        chunks = chunk_document(doc, chunk_size=size)
        assert len(chunks) >= 1
        assert all(c.chunk_size == size for c in chunks)
        assert all(c.overlap == math.floor(size * 0.1) for c in chunks)


def test_section_boundaries_are_not_merged():
    doc = Document(
        source_id='multi', title='T', doc_type='html', url='https://example.com',
        language='en', publisher='p', license_note='n', collected_at=now(), content_hash='h',
        sections=[
            Section(section_path='T > A', text='Content about sushi rice.'),
            Section(section_path='T > B', text='Content about ramen broth.'),
        ],
    )
    chunks = chunk_document(doc, chunk_size=256)
    assert len(chunks) == 2
    assert chunks[0].section_index == 0 and chunks[1].section_index == 1
    assert 'ramen' not in chunks[0].text
    assert 'sushi' not in chunks[1].text
