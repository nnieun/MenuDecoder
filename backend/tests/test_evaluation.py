import json
from unittest.mock import patch

from backend import evaluation
from backend.evaluation import metrics, cer, ndcg, run
from backend.rag.models import Document, Section, now


def make_document():
    return Document(
        source_id='doc-1', title='Test Doc', doc_type='html', url='https://example.com/a',
        language='en', publisher='Test', license_note='n', collected_at=now(), content_hash='h',
        sections=[Section(section_path='Test Doc > Intro', text='Ramen is a Japanese noodle soup with broth.')],
    )


def test_run_sweeps_bm25_only_and_skips_incompatible_modes(tmp_path):
    questions = [{'id': 'q1', 'query': 'ramen'}]
    output = tmp_path / 'report.json'
    with patch.object(evaluation, 'load_documents', return_value=[make_document()]):
        report = run(questions, str(output), models=['bm25'], modes=['bm25', 'hybrid'], sizes=[256], ks=[3])

    # 'hybrid' mode is not valid for the bm25 model, so only one (mode='bm25') combination should run.
    assert len(report['results']) == 1
    row = report['results'][0]
    assert row['question_id'] == 'q1'
    assert row['model'] == 'bm25'
    assert row['mode'] == 'bm25'
    assert row['chunk_size'] == 256
    assert row['top_k'] == 3
    assert row['human_grade'] is None
    assert report['status'] == 'retrieval_only_ungraded'
    assert report['corpus'] == {'doc-1': 'h'}

    written = json.loads(output.read_text(encoding='utf-8'))
    assert written == report


def test_ungraded_results_are_not_reported_as_zero_or_perfect():
    values = metrics([{'human_grade': None}])
    assert values['accuracy'] is None and values['faithfulness'] is None
    assert values['graded_count'] == 0


def test_separate_generation_metrics_and_empty_claims():
    values = metrics([{'human_grade': {'correct': True, 'supported_claims': 0, 'claims': 0, 'relevance': 1}}])
    assert values['accuracy'] == 100 and values['faithfulness'] is None and values['relevance'] == 50


def test_character_error_rate_and_ndcg():
    assert cer('abc', 'adc') == 1 / 3
    assert cer('', 'a') is None
    assert ndcg([2, 1, 0], [0, 2, 1], 3) == 1
    assert ndcg([0], [0], 1) is None
