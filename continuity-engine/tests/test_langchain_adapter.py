"""Provider-agnostic LangChain adapter.

The adapter is duck-typed — it calls `.invoke` on whatever model it is given —
so these tests never import langchain. A fake stands in for any LangChain chat
model / Runnable, which is exactly the contract the adapter promises.
"""

from __future__ import annotations

from app.config import ProjectConfig
from app.engine import ContinuityEngine
from app.services.langchain_adapter import (
    LangChainAdapter,
    create_llm,
    create_llm_from_env,
    create_semantic_matcher,
)

from .conftest import find_issue, footage_scene, script_scene


class FakeMessage:
    """Mimics a LangChain AIMessage: text lives on `.content`."""

    def __init__(self, content):
        self.content = content


class FakeChatModel:
    """Returns an AIMessage-like object, like a real LangChain chat model."""

    def __init__(self, reply: str):
        self._reply = reply
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> FakeMessage:
        self.prompts.append(prompt)
        return FakeMessage(self._reply)


class FakeStringModel:
    """A Runnable that returns a bare string, like an LLM or a str output parser."""

    def invoke(self, prompt: str) -> str:
        return "  bare string reply  "


class BrokenModel:
    def invoke(self, prompt: str):
        raise RuntimeError("provider is down")


def test_extracts_text_from_chat_message():
    adapter = LangChainAdapter(FakeChatModel("polished explanation"))
    assert adapter("hello") == "polished explanation"
    assert adapter.is_available is True


def test_extracts_and_strips_bare_string():
    adapter = LangChainAdapter(FakeStringModel())
    assert adapter("hi") == "bare string reply"


def test_flattens_multipart_content():
    """Some chat models return content as a list of blocks."""
    message = FakeMessage([{"type": "text", "text": "part one "}, {"type": "text", "text": "part two"}])
    model = FakeChatModel("unused")

    def invoke(_prompt):
        return message

    model.invoke = invoke  # type: ignore[method-assign]
    assert LangChainAdapter(model)("x") == "part one part two"


def test_provider_failure_degrades_to_empty_string():
    """A raising model must not break the report — the engine keeps rule-based text."""
    adapter = LangChainAdapter(BrokenModel())
    assert adapter("prompt") == ""


def test_no_model_is_unavailable_and_silent():
    adapter = LangChainAdapter(None)
    assert adapter.is_available is False
    assert adapter("prompt") == ""


def test_create_llm_returns_none_without_a_model():
    assert create_llm(None) is None
    assert isinstance(create_llm(FakeChatModel("x")), LangChainAdapter)


def test_create_llm_from_env_is_none_when_unset(monkeypatch):
    monkeypatch.delenv("VERSE_LLM_MODEL", raising=False)
    assert create_llm_from_env() is None


def test_semantic_matcher_none_without_embeddings():
    assert create_semantic_matcher(None) is None


def test_semantic_matcher_scores_with_embeddings():
    class FakeEmbeddings:
        _vectors = {"sarah": [1.0, 0.0], "sara": [1.0, 0.0], "marcus": [0.0, 1.0]}

        def embed_query(self, text: str) -> list[float]:
            return self._vectors[text.lower()]

    match = create_semantic_matcher(FakeEmbeddings())
    assert match is not None
    assert match("Sarah", "Sara") == 1.0
    assert match("Sarah", "Marcus") == 0.0


def test_llm_polishes_explanation_end_to_end():
    """The wrapped model's text replaces the rule-based explanation."""
    model = FakeChatModel("Sarah's blazer changed with no scripted wardrobe cue.")
    engine = ContinuityEngine(config=ProjectConfig.from_dict({}), llm=LangChainAdapter(model))

    engine.ingest_script(script_scene("S1", 1, wears="blue blazer"))
    engine.ingest_footage(footage_scene("S1", 1, wears="red cardigan"))

    issue = find_issue(engine.analyse("S1"), "costume_mismatch")
    assert issue is not None
    assert issue.explanation == "Sarah's blazer changed with no scripted wardrobe cue."
    assert model.prompts, "the LLM should have been consulted"
