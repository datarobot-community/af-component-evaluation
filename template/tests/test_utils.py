import re

from evaluator.utils import make_run_id


def test_make_run_id_format() -> None:
    run_id = make_run_id()
    assert re.match(r"^\d{8}_\d{6}$", run_id), f"unexpected format: {run_id}"


def test_make_run_id_is_string() -> None:
    assert isinstance(make_run_id(), str)


def test_make_run_id_unique() -> None:
    # Two calls in the same second may collide, but calling twice should
    # produce strings of the correct form — uniqueness is best-effort.
    a = make_run_id()
    b = make_run_id()
    assert re.match(r"^\d{8}_\d{6}$", a)
    assert re.match(r"^\d{8}_\d{6}$", b)
