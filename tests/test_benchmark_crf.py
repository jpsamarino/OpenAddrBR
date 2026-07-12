import pytest
import importlib

def test_benchmark_imports():
    mod = importlib.import_module("benchmarks.benchmark_address_cutter_crf")
    assert hasattr(mod, "run_benchmark")
