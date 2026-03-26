"""Shared performance-audit utilities."""

from .bench import (
    BenchmarkCase,
    BenchmarkStats,
    benchmark_async,
    benchmark_sync,
    format_table,
    get_collected_cases,
    now_stamp,
    reset_collected_cases,
    summarize_samples,
    write_json,
)
from .fixtures import (
    AUDIT_WIKITEXT_FULL_ENTRY,
    AUDIT_WIKITEXT_SAMPLE,
    CORPUS_SIZES,
    WIKITEXT_CORRECTNESS_CASES,
    build_corpus_fixture,
    build_multi_version_payloads,
    build_search_fixture,
    build_semantic_fixture,
    fake_encode_texts,
    install_fake_semantic_encoder,
)

__all__ = [
    "AUDIT_WIKITEXT_FULL_ENTRY",
    "AUDIT_WIKITEXT_SAMPLE",
    "BenchmarkCase",
    "BenchmarkStats",
    "CORPUS_SIZES",
    "WIKITEXT_CORRECTNESS_CASES",
    "benchmark_async",
    "benchmark_sync",
    "format_table",
    "get_collected_cases",
    "reset_collected_cases",
    "build_corpus_fixture",
    "build_multi_version_payloads",
    "build_search_fixture",
    "build_semantic_fixture",
    "fake_encode_texts",
    "install_fake_semantic_encoder",
    "now_stamp",
    "summarize_samples",
    "write_json",
]
