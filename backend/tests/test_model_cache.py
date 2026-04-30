"""Smoke tests for the lazy model cache. Real models are NOT loaded here —
we just verify the cache is empty initially and resets correctly."""
from app.services import _model_cache


def test_caches_start_unloaded():
    _model_cache.reset()
    assert _model_cache._paddle_singleton is None
    assert _model_cache._whisper_singleton is None


def test_reset_clears_existing(monkeypatch):
    _model_cache._paddle_singleton = "fake-paddle"
    _model_cache._whisper_singleton = "fake-whisper"
    _model_cache.reset()
    assert _model_cache._paddle_singleton is None
    assert _model_cache._whisper_singleton is None
