import pytest
from pydantic import ValidationError

from app.document_agent.agent import (
    AgentRunError,
    build_agent_messages,
    parse_tool_arguments,
)
from app.document_agent.chunking import chunk_text
from app.document_agent.retrieval import (
    SearchResult,
    build_grounded_answer,
    meaningful_terms,
    select_excerpt,
)
from app.document_agent.synthesis import (
    ABSTENTION_ANSWER,
    OpenRouterSynthesisError,
    SynthesizedPayload,
    build_validated_outcome,
    extract_json_object,
)
from app.document_agent.tools import (
    SearchDocumentsInput,
    TOOL_DEFINITIONS,
)


def test_short_document_produces_one_chunk() -> None:
    assert chunk_text("Short synthetic document.") == [
        "Short synthetic document."
    ]


def test_chunker_stops_after_real_document_end() -> None:
    text = " ".join(f"sentence-{index}." for index in range(500))
    chunks = chunk_text(text, chunk_size=300, overlap=40)

    assert len(chunks) > 1
    assert chunks[-1] != chunks[-2]
    assert all(chunks)


def test_grounded_answer_contains_citations() -> None:
    result = SearchResult(
        chunk_id=1,
        document_id="doc-1",
        filename="careflow.md",
        page_number=None,
        content="CareFlow uses synthetic Synthea patient data for research.",
        rank=0.8,
    )

    answer, citations = build_grounded_answer(
        "What data does CareFlow use?",
        [result],
    )

    assert "[1]" in answer
    assert citations[0]["filename"] == "careflow.md"
    assert "Synthea" in citations[0]["excerpt"]


def test_grounded_answer_abstains_without_evidence() -> None:
    answer, citations = build_grounded_answer("Unknown question", [])

    assert "could not find supporting evidence" in answer
    assert citations == []


def test_meaningful_terms_remove_generic_document_question_words() -> None:
    assert meaningful_terms(
        "What does the uploaded document say about xenobiotic calibration?"
    ) == ["xenobiotic", "calibration"]


def test_excerpt_prefers_query_terms() -> None:
    excerpt = select_excerpt(
        "Unrelated introduction. Synthetic patients come from Synthea.",
        "Where do synthetic patients come from?",
    )

    assert "Synthea" in excerpt


def test_excerpt_uses_whole_words_and_joins_wrapped_lines() -> None:
    excerpt = select_excerpt(
        "The data intake downloads Synthea and\n"
        "imports the patient timeline.\n\n"
        "Database counts are available.",
        "Where does the patient data come from?",
    )

    assert "Synthea" in excerpt
    assert "patient timeline" in excerpt


def test_extract_json_object_accepts_fenced_model_output() -> None:
    payload = extract_json_object(
        '```json\n{"answer":"Supported [chunk:7]",'
        '"citation_chunk_ids":[7],"grounded":true}\n```'
    )

    assert payload["citation_chunk_ids"] == [7]


def test_synthesis_replaces_validated_chunk_markers() -> None:
    result = SearchResult(
        chunk_id=7,
        document_id="doc-1",
        filename="careflow.md",
        page_number=2,
        content="Synthea provides synthetic patient records.",
        rank=0.7,
    )
    payload = SynthesizedPayload(
        answer="CareFlow uses Synthea records. [chunk:7]",
        citation_chunk_ids=[7],
        grounded=True,
    )

    outcome = build_validated_outcome(
        "What records are used?",
        [result],
        payload,
        "nemotron-test",
    )

    assert outcome.answer.endswith("[1]")
    assert outcome.citations[0]["chunk_id"] == 7
    assert outcome.model == "nemotron-test"


def test_synthesis_rejects_unknown_chunk_ids() -> None:
    payload = SynthesizedPayload(
        answer="Unsupported claim. [chunk:99]",
        citation_chunk_ids=[99],
        grounded=True,
    )

    with pytest.raises(OpenRouterSynthesisError):
        build_validated_outcome("Question?", [], payload, "nemotron-test")


def test_synthesis_honors_model_abstention() -> None:
    payload = SynthesizedPayload(
        answer="I am unsure.",
        citation_chunk_ids=[],
        grounded=False,
    )

    outcome = build_validated_outcome(
        "Unknown?",
        [],
        payload,
        "nemotron-test",
    )

    assert outcome.answer == ABSTENTION_ANSWER
    assert outcome.grounded is False
    assert outcome.citations == []


def test_agent_prompt_requires_retrieval_before_answering() -> None:
    messages = build_agent_messages("What is CareFlow?", 1)

    assert "must call search_documents" in messages[0]["content"]
    assert "selected 1 documents" in messages[1]["content"]


def test_agent_tool_arguments_require_a_json_object() -> None:
    assert parse_tool_arguments('{"query":"Synthea","limit":3}') == {
        "query": "Synthea",
        "limit": 3,
    }

    with pytest.raises(AgentRunError):
        parse_tool_arguments('["Synthea"]')


def test_search_tool_rejects_extra_or_unbounded_inputs() -> None:
    with pytest.raises(ValidationError):
        SearchDocumentsInput.model_validate(
            {"query": "Synthea", "limit": 8, "unknown": True}
        )


def test_agent_tool_schemas_are_strict_and_descriptive() -> None:
    assert {tool["function"]["name"] for tool in TOOL_DEFINITIONS} == {
        "list_documents",
        "search_documents",
    }
    for tool in TOOL_DEFINITIONS:
        function = tool["function"]
        assert len(function["description"]) > 100
        assert function["parameters"]["additionalProperties"] is False
