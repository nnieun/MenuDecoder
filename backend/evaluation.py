"""Offline evaluation runner. Scores require explicit human annotations, never invented labels."""
import argparse
import itertools
import json
import math
import platform
import time
from pathlib import Path

from .config import Settings
from .rag.retriever import Retriever
from .rag.stats import load_documents
from .rag.vector import VectorRetriever


def percentage(numerator, denominator):
    return 100 * numerator / denominator if denominator else None


def metrics(rows):
    scored = [r for r in rows if r.get('human_grade') is not None]
    return {
        'accuracy': percentage(sum(r['human_grade']['correct'] for r in scored), len(scored)),
        'faithfulness': percentage(sum(r['human_grade']['supported_claims'] for r in scored), sum(r['human_grade']['claims'] for r in scored)),
        'relevance': percentage(sum(r['human_grade']['relevance'] for r in scored), 2 * len(scored)),
        'graded_count': len(scored), 'total_count': len(rows),
    }


def ndcg(grades, ideal, k):
    def dcg(values):
        return sum((2 ** grade - 1) / math.log2(index + 2) for index, grade in enumerate(values[:k]))
    denominator = dcg(sorted(ideal, reverse=True))
    return dcg(grades) / denominator if denominator else None


def cer(expected, actual):
    if not expected:
        return None
    previous = list(range(len(actual) + 1))
    for i, left in enumerate(expected, 1):
        current = [i]
        for j, right in enumerate(actual, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j-1] + (left != right)))
        previous = current
    return previous[-1] / len(expected)


def run(questions, output, models, modes, sizes, ks):
    documents = load_documents()
    settings = Settings()
    results = []
    for model, size in itertools.product(models, sizes):
        index = Retriever(documents, size) if model == 'bm25' else VectorRetriever(documents, settings.model_copy(update={'embedding_model': model}), size)
        # Indexes must be built explicitly beforehand; evaluation never silently changes the corpus.
        for mode, k, question in itertools.product(modes, ks, questions):
            if model == 'bm25' and mode != 'bm25':
                continue
            started = time.perf_counter()
            chunks = index.search(question['query'], k) if model == 'bm25' else index.search(question['query'], k, mode=mode)
            results.append({'question_id': question['id'], 'model': model, 'mode': mode,
                            'chunk_size': size, 'top_k': k, 'elapsed_ms': (time.perf_counter()-started)*1000,
                            'results': [c.model_dump() for c in chunks], 'human_grade': None})
    report = {'runtime': platform.platform(), 'corpus': {d.source_id: d.content_hash for d in documents},
              'status': 'retrieval_only_ungraded', 'results': results, 'metrics': metrics(results)}
    Path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('questions', help='JSON array with id and query; keep dev/test splits separate')
    parser.add_argument('--output', required=True)
    parser.add_argument('--models', nargs='+', default=['bm25'])
    parser.add_argument('--modes', nargs='+', default=['bm25'])
    args = parser.parse_args()
    questions = json.loads(Path(args.questions).read_text(encoding='utf-8'))
    run(questions, args.output, args.models, args.modes, [256, 512, 1024], [3, 5, 10])


if __name__ == '__main__':
    main()
