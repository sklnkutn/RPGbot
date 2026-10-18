import asyncio

import pytest

from debug.mode_local import generate_smart_ollama_response
from services import loaders, server_request, utils


def test_loaders_resolve_existing_catalog_and_prompt_data():
    characters = loaders.load_characters()
    adventures = loaders.load_adventures()

    assert {character["id"] for character in characters} == {
        "char_gwen_stacy",
        "char_mavis_dracula",
        "char_black_widow",
    }
    assert {adventure["id"] for adventure in adventures} == {
        "deserted_island",
        "infinity_train",
        "adv_road_777",
    }
    assert all(character["visual"]["resolved_image_path"].startswith("/assets/") for character in characters)
    assert all(adventure["resolved_image_path"].startswith("/assets/") for adventure in adventures)

    widow = loaders.load_character_data("char_black_widow")
    assert widow["name"] == "Наталья Романова"
    assert widow["visual"]["default_clothing"] == "cleavage, black bodysuit, belt"
    assert loaders.load_character_data("missing-character") == {}

    world = loaders.get_adventure_world_info("deserted_island")
    assert world["genre"]
    assert "остров" in world["rules"].lower()
    assert loaders.get_adventure_world_info("missing-adventure") == {"genre": [], "rules": ""}

    assert loaders.load_prompt("first_run_prompt.yaml")
    assert loaders.load_prompt_section("narrator_prompt.yaml", "prompt_without_char")
    assert loaders._load_workflow_template()["9"]["class_type"] == "SaveImage"


def test_prompt_loaders_report_missing_or_invalid_sections(tmp_path, monkeypatch):
    monkeypatch.setattr(loaders, "PROMPTS_DIR", tmp_path)

    with pytest.raises(FileNotFoundError):
        loaders.load_prompt("missing.yaml")

    (tmp_path / "invalid.yaml").write_text("other: value\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Prompt"):
        loaders.load_prompt("invalid.yaml")
    with pytest.raises(ValueError, match="absent|отсутствует"):
        loaders.load_prompt_section("invalid.yaml", "missing")


def test_selection_validation_and_limit(monkeypatch):
    assert utils.validate_game_start([], []) == "Пожалуйста, выберите сюжет истории"
    assert utils.validate_game_start(["adventure"], []) == (
        "Пожалуйста, выберите как минимум одного персонажа (до 3-х)"
    )
    assert utils.validate_game_start(["adventure"], ["character"]) is None

    notifications = []
    monkeypatch.setattr(utils.ui, "notify", lambda *args, **kwargs: notifications.append((args, kwargs)))

    class Checkbox:
        value = True

    class Card:
        def __init__(self):
            self.changes = []

        def classes(self, **kwargs):
            self.changes.append(kwargs)

    selected = ["one", "two", "three"]
    checkbox = Checkbox()
    card = Card()
    utils.handle_selection_toggle("four", checkbox, card, selected, max_limit=3)

    assert checkbox.value is False
    assert selected == ["one", "two", "three"]
    assert notifications

    checkbox.value = False
    utils.handle_selection_toggle("two", checkbox, card, selected, max_limit=3)
    assert selected == ["one", "three"]
    assert card.changes == [{"remove": "bg-blue-50"}]


def test_server_url_and_model_response_parsing(monkeypatch):
    monkeypatch.setattr(server_request, "OLLAMA_PORT", "11435")
    monkeypatch.setattr(server_request, "COMFY_PORT", "8189")

    assert server_request.get_server_url("OLLAMA", "/api/tags") == "http://localhost:11435/api/tags"
    assert server_request.get_server_url("comfy") == "http://localhost:8189"
    with pytest.raises(ValueError, match="unknown|Неизвестный"):
        server_request.get_server_url("unknown")

    responses = [
        {"models": [{"name": "llama3"}, {"name": ""}, {"other": "ignored"}]},
        {"models": []},
        {"models": ["checkpoint-a", "checkpoint-b"]},
    ]

    async def fake_get(url, server, timeout_seconds):
        return responses.pop(0)

    monkeypatch.setattr(server_request, "send_http_get", fake_get)
    assert asyncio.run(server_request.get_ollama_models()) == ["llama3"]
    assert asyncio.run(server_request.get_ollama_models()) == ["модели не обнаружены"]
    assert asyncio.run(server_request.get_comfy_models()) == ["checkpoint-a", "checkpoint-b"]


def test_model_request_retries_until_response_can_be_parsed(monkeypatch):
    results = iter(["offline", {"models": ["model-a"]}])
    calls = []

    async def fake_get(url, server, timeout_seconds):
        calls.append((url, server, timeout_seconds))
        return next(results)

    async def no_wait(_delay):
        return None

    monkeypatch.setattr(server_request, "send_http_get", fake_get)
    monkeypatch.setattr(server_request.asyncio, "sleep", no_wait)

    assert asyncio.run(server_request.get_comfy_models(retry=True, max_attempts=2, delay=0)) == ["model-a"]
    assert len(calls) == 2


@pytest.mark.parametrize(
    ("properties", "user_text", "expected_fragment"),
    [
        ({"relation_shifts": {}}, "scene", '"relation_shifts"'),
        ({}, "[СИСТЕМНОЕ СОБЫТИЕ]", "Холодный прибой"),
    ],
)
def test_local_llm_mock_selects_response_by_request_contract(properties, user_text, expected_fragment):
    payload = {
        "model": "test-model",
        "format": {"properties": properties},
        "messages": [{"role": "user", "content": user_text}],
    }

    response = generate_smart_ollama_response(payload)

    assert response["model"] == "test-model"
    assert response["done"] is True
    assert expected_fragment in response["message"]["content"]
