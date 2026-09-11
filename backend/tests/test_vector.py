from backend.rag.vector import rrf, mmr, VectorRetriever
from backend.config import Settings
from backend.rag.models import Document, Section


def test_rrf_combines_rankings_without_duplicate_votes():
    assert rrf([['a', 'a', 'b'], ['b', 'c']])[0] == 'b'


def test_mmr_avoids_nearly_identical_candidates():
    result = mmr([1, 0], [[1, 0], [.999, .001], [.5, .866]], 2, weight=.2)
    assert result == [0, 2]


def test_chroma_explicit_vectors_survive_reopen(tmp_path):
    class FixedEmbeddings:
        model = 'test-fixture-not-real-model'
        def encode(self, texts, charge=lambda: None):
            return [[1., 0.] if 'ramen' in t.lower() else [0., 1.] for t in texts]
    docs = [Document(source_id='test', title='Food', doc_type='html', url='https://example.com',
                     language='en', publisher='test', license_note='fixture', content_hash='fixture',
                     sections=[Section(section_path='Ramen', text='Ramen noodles in broth.'),
                               Section(section_path='Sushi', text='Sushi rice and fish.')])]
    settings = Settings(data_dir=tmp_path, retrieval_mode='similarity')
    first = VectorRetriever(docs, settings, embedder=FixedEmbeddings())
    assert first.build()['count'] == 2
    reopened = VectorRetriever(docs, settings, embedder=FixedEmbeddings())
    assert 'Ramen' in reopened.search('ramen', 1)[0].section_path
    assert reopened.name == first.name
