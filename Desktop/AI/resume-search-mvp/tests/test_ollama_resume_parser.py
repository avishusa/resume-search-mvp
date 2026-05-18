import json

import httpx

from app.parsing.ollama import OllamaResumeParserProvider
from app.parsing.rule_based import RuleBasedResumeParserProvider
from app.services.candidate_profile_service import CandidateProfileService


class FakeOllamaResponse:
    def __init__(self, body: dict | None = None, error: Exception | None = None) -> None:
        self._body = body or {}
        self._error = error

    def raise_for_status(self) -> None:
        if self._error:
            raise self._error

    def json(self) -> dict:
        return self._body


class FakeOllamaClient:
    def __init__(self, response: FakeOllamaResponse) -> None:
        self._response = response
        self.last_url: str | None = None
        self.last_payload: dict | None = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def post(self, url: str, json: dict) -> FakeOllamaResponse:
        self.last_url = url
        self.last_payload = json
        return self._response


class SequentialFakeOllamaClient:
    def __init__(self, responses: list[FakeOllamaResponse], payloads: list[dict]) -> None:
        self._responses = responses
        self._payloads = payloads

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def post(self, url: str, json: dict) -> FakeOllamaResponse:
        self._payloads.append(json)
        return self._responses.pop(0)


def _service_with_fake_ollama(monkeypatch, response: FakeOllamaResponse) -> CandidateProfileService:
    monkeypatch.setattr(
        "app.parsing.ollama.httpx.Client",
        lambda timeout: FakeOllamaClient(response),
    )
    return CandidateProfileService(
        primary_parser=OllamaResumeParserProvider(
            base_url="http://localhost:11434",
            model="llama3.1:8b",
            timeout_seconds=1,
        ),
        fallback_parser=RuleBasedResumeParserProvider(skill_catalog=["Python"]),
    )


def test_ollama_provider_posts_to_generate_and_parses_response_field(monkeypatch) -> None:
    fake_client = FakeOllamaClient(
        FakeOllamaResponse(
            {
                "response": json.dumps(
                    {
                        "candidate_name": "Jane Candidate",
                        "email": None,
                        "phone": None,
                        "current_title": "AI Engineer",
                        "skills": ["Python"],
                        "total_experience_years": None,
                        "companies": [],
                        "education": [],
                        "resume_summary": "AI Engineer with Python.",
                        "confidence_score": 0.8,
                    }
                ),
                "model": "llama3.1:8b",
            }
        )
    )
    monkeypatch.setattr(
        "app.parsing.ollama.httpx.Client",
        lambda timeout: fake_client,
    )
    provider = OllamaResumeParserProvider(
        base_url="http://localhost:11434",
        model="llama3.1:8b",
        timeout_seconds=3,
    )

    profile = provider.parse("AI Engineer\nPython")

    assert fake_client.last_url == "http://localhost:11434/api/generate"
    assert fake_client.last_payload["model"] == "llama3.1:8b"
    assert fake_client.last_payload["stream"] is False
    assert fake_client.last_payload["format"] == "json"
    assert set(fake_client.last_payload) == {"model", "prompt", "stream", "format"}
    assert profile.parser_used == "ollama"
    assert profile.current_title == "AI Engineer"


def test_successful_mocked_ollama_response_returns_ollama_parser(monkeypatch) -> None:
    service = _service_with_fake_ollama(
        monkeypatch,
        FakeOllamaResponse(
            {
                "response": json.dumps(
                    {
                        "candidate_name": "Jane Candidate",
                        "email": "jane@example.com",
                        "phone": "312-555-1212",
                        "current_title": "AI Engineer",
                        "skills": ["Python"],
                        "total_experience_years": 5,
                        "companies": ["Acme"],
                        "education": ["BS Computer Science"],
                        "resume_summary": "AI Engineer with Python experience.",
                        "confidence_score": 0.91,
                    }
                )
            }
        ),
    )

    profile = service.parse("AI Engineer\njane@example.com\nPython")

    assert profile.parser_used == "ollama"
    assert profile.parsing_status == "parsed"
    assert profile.candidate_name == "Jane Candidate"
    assert profile.current_title == "AI Engineer"
    assert profile.skills == ["Python"]


def test_ollama_string_confidence_score_still_returns_ollama(monkeypatch) -> None:
    service = _service_with_fake_ollama(
        monkeypatch,
        FakeOllamaResponse(
            {
                "response": json.dumps(
                    {
                        "candidate_name": "Jane Candidate",
                        "email": "jane@example.com",
                        "phone": None,
                        "current_title": "AI Engineer",
                        "skills": ["Python", "python"],
                        "total_experience_years": None,
                        "companies": [],
                        "education": [],
                        "resume_summary": "AI Engineer with Python.",
                        "confidence_score": "0.85",
                    }
                )
            }
        ),
    )

    result = service.parse_with_metadata("AI Engineer\njane@example.com\nPython")

    assert result.profile.parser_used == "ollama"
    assert result.profile.confidence_score == 0.85
    assert result.profile.skills == ["Python"]


def test_ollama_null_confidence_score_still_returns_ollama(monkeypatch) -> None:
    service = _service_with_fake_ollama(
        monkeypatch,
        FakeOllamaResponse(
            {
                "response": json.dumps(
                    {
                        "candidate_name": "Jane Candidate",
                        "email": "jane@example.com",
                        "phone": None,
                        "current_title": "AI Engineer",
                        "skills": ["Python"],
                        "total_experience_years": None,
                        "companies": [],
                        "education": [],
                        "resume_summary": "AI Engineer with Python.",
                        "confidence_score": None,
                    }
                )
            }
        ),
    )

    result = service.parse_with_metadata("AI Engineer\njane@example.com\nPython")

    assert result.profile.parser_used == "ollama"
    assert result.profile.confidence_score > 0
    assert result.parsing_error is None


def test_ollama_text_confidence_score_still_returns_ollama_with_calculated_score(
    monkeypatch,
) -> None:
    service = _service_with_fake_ollama(
        monkeypatch,
        FakeOllamaResponse(
            {
                "response": json.dumps(
                    {
                        "candidate_name": "Jane Candidate",
                        "email": "jane@example.com",
                        "phone": "312-555-1212",
                        "current_title": "AI Engineer",
                        "skills": ["Python"],
                        "total_experience_years": None,
                        "companies": [],
                        "education": [],
                        "resume_summary": "AI Engineer with Python.",
                        "confidence_score": "high",
                    }
                )
            }
        ),
    )

    result = service.parse_with_metadata("AI Engineer\njane@example.com\nPython")

    assert result.profile.parser_used == "ollama"
    assert 0 < result.profile.confidence_score <= 1
    assert result.parsing_error is None


def test_ollama_email_list_is_normalized_without_fallback(monkeypatch) -> None:
    service = _service_with_fake_ollama(
        monkeypatch,
        FakeOllamaResponse(
            {
                "response": json.dumps(
                    {
                        "candidate_name": "Jane Candidate",
                        "email": ["test@example.com"],
                        "phone": None,
                        "current_title": "AI Engineer",
                        "skills": ["Python"],
                        "total_experience_years": None,
                        "companies": [],
                        "education": [],
                        "resume_summary": "AI Engineer with Python.",
                        "confidence_score": 0.8,
                    }
                )
            }
        ),
    )

    result = service.parse_with_metadata("Jane Candidate\nAI Engineer\nPython")

    assert result.profile.parser_used == "ollama"
    assert result.profile.email == "test@example.com"
    assert result.parsing_error is None


def test_ollama_phone_list_uses_first_non_empty_value(monkeypatch) -> None:
    service = _service_with_fake_ollama(
        monkeypatch,
        FakeOllamaResponse(
            {
                "response": json.dumps(
                    {
                        "candidate_name": "Jane Candidate",
                        "email": "test@example.com",
                        "phone": ["", "+92-321-1174167", "+92-321-1179584"],
                        "current_title": "AI Engineer",
                        "skills": ["Python"],
                        "total_experience_years": None,
                        "companies": [],
                        "education": [],
                        "resume_summary": "AI Engineer with Python.",
                        "confidence_score": 0.8,
                    }
                )
            }
        ),
    )

    result = service.parse_with_metadata("Jane Candidate\nAI Engineer\nPython")

    assert result.profile.parser_used == "ollama"
    assert result.profile.phone == "+92-321-1174167"
    assert result.parsing_error is None


def test_ollama_current_title_list_is_normalized_to_string(monkeypatch) -> None:
    service = _service_with_fake_ollama(
        monkeypatch,
        FakeOllamaResponse(
            {
                "response": json.dumps(
                    {
                        "candidate_name": "Jane Candidate",
                        "email": "test@example.com",
                        "phone": None,
                        "current_title": ["Senior Data Scientist"],
                        "skills": "Python, Machine Learning",
                        "total_experience_years": None,
                        "companies": None,
                        "education": None,
                        "resume_summary": ["Senior Data Scientist with Python."],
                        "confidence_score": None,
                    }
                )
            }
        ),
    )

    result = service.parse_with_metadata("Jane Candidate\nSenior Data Scientist\nPython")

    assert result.profile.parser_used == "ollama"
    assert result.profile.current_title == "Senior Data Scientist"
    assert result.profile.skills == ["Python", "Machine Learning"]
    assert result.profile.companies == []
    assert result.profile.education == []
    assert result.parsing_error is None


def test_ollama_jillani_like_response_does_not_fallback(monkeypatch) -> None:
    service = _service_with_fake_ollama(
        monkeypatch,
        FakeOllamaResponse(
            {
                "response": json.dumps(
                    {
                        "candidate_name": "Muhammad G. Jillani",
                        "email": ["m.g.jillani123@gmail.com"],
                        "phone": ["+92-321-1174167", "+92-321-1179584"],
                        "current_title": (
                            "Senior Data Scientist & Machine Learning Software "
                            "Engineer (Generative AI) PURELOGICS"
                        ),
                        "skills": ["Python", "Machine Learning", "Generative AI"],
                        "total_experience_years": "5",
                        "companies": ["PURELOGICS"],
                        "education": [],
                        "resume_summary": "Senior Data Scientist at PURELOGICS.",
                        "confidence_score": "0.87",
                    }
                )
            }
        ),
    )

    result = service.parse_with_metadata(
        "Muhammad G. Jillani\n"
        "Senior Data Scientist & Machine Learning Software Engineer "
        "(Generative AI) PURELOGICS\n"
        "m.g.jillani123@gmail.com\nPython"
    )

    assert result.profile.parser_used == "ollama"
    assert result.profile.email == "m.g.jillani123@gmail.com"
    assert result.profile.phone == "+92-321-1174167"
    assert (
        result.profile.current_title
        == "Senior Data Scientist & Machine Learning Software Engineer (Generative AI) PURELOGICS"
    )
    assert result.profile.total_experience_years == 5.0
    assert result.parsing_error is None


def test_invalid_ollama_json_triggers_rule_based_fallback(monkeypatch) -> None:
    service = _service_with_fake_ollama(
        monkeypatch,
        FakeOllamaResponse({"response": "{not valid json"}),
    )

    profile = service.parse("AI Engineer\njane@example.com\nPython")

    assert profile.parser_used == "rule_based"
    assert profile.email == "jane@example.com"
    assert profile.current_title == "AI Engineer"


def test_invalid_ollama_json_records_ollama_error(monkeypatch) -> None:
    service = _service_with_fake_ollama(
        monkeypatch,
        FakeOllamaResponse({"response": "{not valid json"}),
    )

    result = service.parse_with_metadata("AI Engineer\njane@example.com\nPython")

    assert result.profile.parser_used == "rule_based"
    assert result.ollama_error is not None
    assert "Ollama resume parsing failed" in result.ollama_error
    assert result.ollama_raw_response_preview == "{not valid json"


def test_ollama_error_triggers_rule_based_fallback(monkeypatch) -> None:
    service = _service_with_fake_ollama(
        monkeypatch,
        FakeOllamaResponse(error=httpx.TimeoutException("timeout")),
    )

    profile = service.parse("AI Engineer\njane@example.com\nPython")

    assert profile.parser_used == "rule_based"
    assert profile.email == "jane@example.com"


def _http_500_error(message: str = "model overloaded") -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "http://localhost:11434/api/generate")
    response = httpx.Response(500, text=message, request=request)
    return httpx.HTTPStatusError(
        "Server error '500 Internal Server Error'",
        request=request,
        response=response,
    )


def test_ollama_500_retries_once_with_shorter_text_and_returns_ollama(monkeypatch) -> None:
    payloads: list[dict] = []
    responses = [
        FakeOllamaResponse(error=_http_500_error("too much input")),
        FakeOllamaResponse(
            {
                "response": json.dumps(
                    {
                        "candidate_name": "Bhavesh Wadhwani",
                        "email": "bhavesh@example.com",
                        "phone": None,
                        "current_title": "Data Scientist",
                        "skills": ["Python"],
                        "total_experience_years": 4.5,
                        "companies": [],
                        "education": [],
                        "resume_summary": "Data Scientist with Python.",
                        "confidence_score": 0.86,
                    }
                )
            }
        ),
    ]
    monkeypatch.setattr(
        "app.parsing.ollama.httpx.Client",
        lambda timeout: SequentialFakeOllamaClient(responses, payloads),
    )
    provider = OllamaResumeParserProvider(
        base_url="http://localhost:11434",
        model="llama3.1:8b",
        timeout_seconds=1,
        max_resume_chars=12000,
    )

    profile = provider.parse("Bhavesh Wadhwani\nData Scientist\nPython\n" + ("x" * 9000))

    assert profile.parser_used == "ollama"
    assert profile.candidate_name == "Bhavesh Wadhwani"
    assert len(payloads) == 2
    assert len(payloads[1]["prompt"]) < len(payloads[0]["prompt"])


def test_ollama_500_retry_failure_falls_back_and_records_both_errors(monkeypatch) -> None:
    payloads: list[dict] = []
    responses = [
        FakeOllamaResponse(error=_http_500_error("first failure")),
        FakeOllamaResponse(error=_http_500_error("retry failure")),
    ]
    monkeypatch.setattr(
        "app.parsing.ollama.httpx.Client",
        lambda timeout: SequentialFakeOllamaClient(responses, payloads),
    )
    service = CandidateProfileService(
        primary_parser=OllamaResumeParserProvider(
            base_url="http://localhost:11434",
            model="llama3.1:8b",
            timeout_seconds=1,
            max_resume_chars=12000,
        ),
        fallback_parser=RuleBasedResumeParserProvider(skill_catalog=["Python"]),
    )

    result = service.parse_with_metadata(
        "Bhavesh Wadhwani\nData Scientist\nbhavesh@example.com\nPython\n" + ("x" * 9000)
    )

    assert result.profile.parser_used == "rule_based"
    assert result.ollama_error is not None
    assert "first failure" in result.ollama_error
    assert "retry failure" in result.ollama_error
    assert "cleaned_text_chars" in result.ollama_error
    assert result.ollama_raw_response_preview == "retry failure"
