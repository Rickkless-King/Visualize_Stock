"""Smoke test verifying package layout and pytest pythonpath."""

import core
import engine


def test_core_and_engine_packages_importable() -> None:
    assert core.__doc__ is not None
    assert engine.__doc__ is not None
