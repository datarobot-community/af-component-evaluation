# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluator.generator import (
    _BENCHMARK_CONTEXTS,
    _GENERIC_BENCHMARK_CONTEXT,
    CaseGenerator,
)


def _make_mock_response(cases: list[dict[str, Any]]) -> MagicMock:
    """Return a mock litellm completion response containing the given cases as JSON."""
    message = MagicMock()
    message.content = json.dumps(cases)
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def _valid_case(case_id: str = "gen-001", behavior: str = "good") -> dict[str, Any]:
    return {
        "id": case_id,
        "source": "synthetic",
        "input": "What does this agent do?",
        "expected_behavior": behavior,
        "ideal_response": None,
        "notes": "Should explain capabilities",
    }


# ---------------------------------------------------------------------------
# generate()
# ---------------------------------------------------------------------------


def test_generate_returns_cases() -> None:
    cases = [_valid_case("gen-001", "good"), _valid_case("gen-002", "bad")]

    with patch(
        "evaluator.generator.litellm.completion",
        return_value=_make_mock_response(cases),
    ):
        gen = CaseGenerator()
        result = gen.generate("test agent", n_good=1, n_bad=1)

    assert len(result) == 2
    assert result[0]["id"] == "gen-001"
    assert result[1]["expected_behavior"] == "bad"


def test_generate_calls_api_with_model(monkeypatch: pytest.MonkeyPatch) -> None:
    cases = [_valid_case()]

    with patch(
        "evaluator.generator.litellm.completion",
        return_value=_make_mock_response(cases),
    ) as mock_completion:
        gen = CaseGenerator(
            model="datarobot/bedrock/anthropic.claude-haiku-4-5-20251001"
        )
        gen.generate("test agent", n_good=1, n_bad=0)

    call_kwargs = mock_completion.call_args[1]
    assert (
        call_kwargs["model"] == "datarobot/bedrock/anthropic.claude-haiku-4-5-20251001"
    )


def test_generate_raises_on_missing_fields() -> None:
    incomplete = [{"id": "gen-001", "source": "synthetic"}]  # missing required fields

    with patch(
        "evaluator.generator.litellm.completion",
        return_value=_make_mock_response(incomplete),
    ):
        gen = CaseGenerator()
        with pytest.raises(ValueError, match="missing fields"):
            gen.generate("test agent", n_good=1, n_bad=0)


def test_generate_uses_benchmark_context() -> None:
    cases = [_valid_case()]

    with patch(
        "evaluator.generator.litellm.completion",
        return_value=_make_mock_response(cases),
    ) as mock_completion:
        gen = CaseGenerator()
        gen.generate("test agent", n_good=1, n_bad=0, benchmark_name="safety_refusal")

    user_content = mock_completion.call_args[1]["messages"][1]["content"]
    assert _BENCHMARK_CONTEXTS["safety_refusal"] in user_content
    assert _GENERIC_BENCHMARK_CONTEXT not in user_content


def test_generate_uses_generic_context_without_benchmark() -> None:
    cases = [_valid_case()]

    with patch(
        "evaluator.generator.litellm.completion",
        return_value=_make_mock_response(cases),
    ) as mock_completion:
        gen = CaseGenerator()
        gen.generate("test agent", n_good=1, n_bad=0)

    user_content = mock_completion.call_args[1]["messages"][1]["content"]
    assert _GENERIC_BENCHMARK_CONTEXT in user_content


def test_generate_raises_on_missing_benchmark_extra_fields() -> None:
    # prompt_injection requires 'canary' field
    case = {**_valid_case(), "expected_behavior": "bad"}  # no canary

    with patch(
        "evaluator.generator.litellm.completion",
        return_value=_make_mock_response([case]),
    ):
        gen = CaseGenerator()
        with pytest.raises(ValueError, match="missing fields"):
            gen.generate(
                "test agent", n_good=0, n_bad=1, benchmark_name="prompt_injection"
            )


def test_generate_raises_on_invalid_behavior() -> None:
    bad_case = {**_valid_case(), "expected_behavior": "maybe"}

    with patch(
        "evaluator.generator.litellm.completion",
        return_value=_make_mock_response([bad_case]),
    ):
        gen = CaseGenerator()
        with pytest.raises(ValueError, match="invalid expected_behavior"):
            gen.generate("test agent", n_good=1, n_bad=0)


def test_generate_raises_on_none_content() -> None:
    message = MagicMock()
    message.content = None
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]

    with patch("evaluator.generator.litellm.completion", return_value=response):
        gen = CaseGenerator()
        with pytest.raises(ValueError, match="No text content"):
            gen.generate("test agent", n_good=1, n_bad=0)


# ---------------------------------------------------------------------------
# save()
# ---------------------------------------------------------------------------


def test_save_writes_file(tmp_path: Path) -> None:
    cases = [_valid_case()]
    gen = CaseGenerator()
    out = tmp_path / "output.json"
    gen.save(cases, out)
    assert out.exists()
    written = json.loads(out.read_text())
    assert len(written) == 1
    assert written[0]["id"] == "gen-001"


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    cases = [_valid_case()]
    gen = CaseGenerator()
    out = tmp_path / "nested" / "dir" / "cases.json"
    gen.save(cases, out)
    assert out.exists()


def test_save_overwrites_by_default(tmp_path: Path) -> None:
    gen = CaseGenerator()
    out = tmp_path / "cases.json"
    gen.save([_valid_case("gen-001")], out)
    gen.save([_valid_case("gen-002")], out)
    written = json.loads(out.read_text())
    assert len(written) == 1
    assert written[0]["id"] == "gen-002"


def test_save_append_merges(tmp_path: Path) -> None:
    gen = CaseGenerator()
    out = tmp_path / "cases.json"
    gen.save([_valid_case("gen-001")], out)
    result = gen.save([_valid_case("gen-002")], out, append=True)
    assert len(result) == 2
    ids = {c["id"] for c in result}
    assert ids == {"gen-001", "gen-002"}


def test_save_returns_final_list(tmp_path: Path) -> None:
    gen = CaseGenerator()
    out = tmp_path / "cases.json"
    returned = gen.save([_valid_case("gen-001"), _valid_case("gen-002")], out)
    assert len(returned) == 2
