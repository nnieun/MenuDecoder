import pytest
from backend.rag.retriever import default_retriever, _tokenize

@pytest.mark.parametrize('query,source', [
    ('라멘', 'jnto-ramen'), ('味噌ラーメン', 'jnto-ramen'),
    ('야키토리', 'jnto-yakitori'), ('焼き鳥', 'jnto-yakitori'),
    ('초밥', 'jnto-sushi'), ('寿司', 'jnto-sushi'),
])
def test_actual_corpus_multilingual_queries(query, source):
    results = default_retriever().search(query)
    assert results
    assert source in {c.source_id for c in results}

def test_unicode_terms_are_preserved():
    assert '김치' in _tokenize('김치')
    assert 'ramen' in _tokenize('ＲＡＭＥＮ')
    assert _tokenize('お好み焼き')
