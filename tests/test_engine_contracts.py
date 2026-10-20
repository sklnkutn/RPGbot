import asyncio
import json

import pytest

from engine import first_assistant_ask, first_run, fourth_assistant_ask, third_assistant_ask


def test_build_chat_payload_includes_world_context(monkeypatch):
    monkeypatch.setattr(first_run, "load_prompt", lambda _name: "base prompt")
    monkeypatch.setattr(
        first_run,
        "get_adventure_world_info",
        lambda _adventure_id: {"genre": ["mystery", "survival"], "rules": "Stay on the island."},
    )

    payload = first_run.build_chat_payload("island", "test-model")

    assert payload["model"] == "test-model"
    assert payload["messages"][0]["content"] == (
        "base prompt\n\n# Контекст текущего мира\n"
        "- Жанр: mystery, survival\n"
        "- Правила и особенности мира:\nStay on the island."
    )
    assert payload["messages"][1]["role"] == "user"
    assert payload["stream"] is False


def test_first_assistant_ask_uses_single_session_character(monkeypatch):
    async def run_test():
        monkeypatch.setattr(
            first_assistant_ask,
            "get_adventure_world_info",
            lambda _adventure: {"genre": [], "rules": ""},
        )
        monkeypatch.setattr(first_assistant_ask, "get_session_characters_list", lambda _session: resolved(["char-a"]))
        monkeypatch.setattr(first_assistant_ask, "load_prompt_section", lambda *_args: "system prompt")
        monkeypatch.setattr(first_assistant_ask, "get_session_messages", lambda _session: resolved([]))
        monkeypatch.setattr(first_assistant_ask, "_get_last_messages", lambda _messages: (None, None))
        monkeypatch.setattr(
            first_assistant_ask,
            "send_http_post",
            lambda *_args, **_kwargs: resolved({"message": {"content": '{"need_new_character": true}'}}),
        )

        selected = await first_assistant_ask.first_assistant_ask(
            session_id=1,
            adventure_id="adventure",
            user_text="Иду дальше",
            model_name="model",
        )
        assert selected == "char-a"

    async def resolved(value):
        return value

    asyncio.run(run_test())


def test_first_assistant_ask_rejects_character_outside_session(monkeypatch):
    async def run_test():
        async def resolved(value):
            return value

        monkeypatch.setattr(
            first_assistant_ask,
            "get_adventure_world_info",
            lambda _adventure: {"genre": [], "rules": ""},
        )
        monkeypatch.setattr(
            first_assistant_ask,
            "get_session_characters_list",
            lambda _session: resolved(["char-a", "char-b"]),
        )
        monkeypatch.setattr(first_assistant_ask, "load_prompt_section", lambda *_args: "system prompt")
        monkeypatch.setattr(first_assistant_ask, "get_session_messages", lambda _session: resolved([]))
        monkeypatch.setattr(first_assistant_ask, "_get_last_messages", lambda _messages: (None, None))
        monkeypatch.setattr(
            first_assistant_ask,
            "send_http_post",
            lambda *_args, **_kwargs: resolved(
                {"message": {"content": json.dumps({"need_new_character": True, "characters_name": "outsider"})}}
            ),
        )

        with pytest.raises(ValueError, match="не входящего в сессию"):
            await first_assistant_ask.first_assistant_ask(1, "adventure", "text", "model")

    asyncio.run(run_test())


def test_fourth_assistant_scales_valid_relation_shifts(monkeypatch):
    async def run_test():
        async def resolved(value):
            return value

        model_reply = {
            "relation_shifts": {
                "trust": 1,
                "respect": -1,
                "affection": 0,
                "annoyance": 1,
                "fear": 0,
                "jealousy": -1,
            },
            "clothing_changed": True,
            "new_clothing": "  dark coat  ",
            "leaves_scene": True,
        }
        monkeypatch.setattr(fourth_assistant_ask, "load_prompt", lambda _name: "evaluate")
        monkeypatch.setattr(
            fourth_assistant_ask,
            "load_character_data",
            lambda _character: {"name": "Character", "bio": {"personality_traits": []}},
        )
        monkeypatch.setattr(
            fourth_assistant_ask,
            "get_character_full_state",
            lambda *_args: resolved({"current_clothing": "uniform"}),
        )
        monkeypatch.setattr(
            fourth_assistant_ask,
            "send_http_post",
            lambda *_args, **_kwargs: resolved(
                {"message": {"content": json.dumps(model_reply)}}
            ),
        )

        result = await fourth_assistant_ask.fourth_assistant_ask(
            1, "char-a", "The scene", "visual prompt", "model"
        )

        assert result == {
            "deltas": {
                "trust": fourth_assistant_ask.RELATION_STEP,
                "respect": -fourth_assistant_ask.RELATION_STEP,
                "affection": 0,
                "annoyance": fourth_assistant_ask.RELATION_STEP,
                "fear": 0,
                "jealousy": -fourth_assistant_ask.RELATION_STEP,
            },
            "new_clothing": "dark coat",
            "leaves_scene": True,
        }

    asyncio.run(run_test())


@pytest.mark.parametrize(
    "invalid_reply",
    [
        {"relation_shifts": {}, "clothing_changed": False, "new_clothing": None, "leaves_scene": False},
        {
            "relation_shifts": {
                "trust": True,
                "respect": 0,
                "affection": 0,
                "annoyance": 0,
                "fear": 0,
                "jealousy": 0,
            },
            "clothing_changed": False,
            "new_clothing": None,
            "leaves_scene": False,
        },
        {
            "relation_shifts": {
                "trust": 0,
                "respect": 0,
                "affection": 0,
                "annoyance": 0,
                "fear": 0,
                "jealousy": 0,
            },
            "clothing_changed": True,
            "new_clothing": None,
            "leaves_scene": False,
        },
    ],
)
def test_fourth_assistant_rejects_invalid_evaluator_output(monkeypatch, invalid_reply):
    async def run_test():
        async def resolved(value):
            return value

        monkeypatch.setattr(fourth_assistant_ask, "load_prompt", lambda _name: "evaluate")
        monkeypatch.setattr(
            fourth_assistant_ask,
            "load_character_data",
            lambda _character: {"name": "Character", "bio": {"personality_traits": []}},
        )
        monkeypatch.setattr(
            fourth_assistant_ask,
            "get_character_full_state",
            lambda *_args: resolved({"current_clothing": "uniform"}),
        )
        monkeypatch.setattr(
            fourth_assistant_ask,
            "send_http_post",
            lambda *_args, **_kwargs: resolved({"message": {"content": json.dumps(invalid_reply)}}),
        )

        with pytest.raises(ValueError):
            await fourth_assistant_ask.fourth_assistant_ask(
                1, "char-a", "The scene", "visual prompt", "model"
            )

    asyncio.run(run_test())


def test_third_assistant_uses_fallback_for_empty_visual_prompt(monkeypatch):
    async def run_test():
        async def resolved(value):
            return value

        payloads = []

        async def send_http_post(_url, payload, **_kwargs):
            payloads.append(payload)
            return {"message": {"content": "   "}}

        monkeypatch.setattr(
            third_assistant_ask,
            "get_session_info",
            lambda _session: resolved({"comfy_model": "checkpoint"}),
        )
        monkeypatch.setattr(third_assistant_ask, "load_prompt_section", lambda *_args: "visual system")
        monkeypatch.setattr(
            third_assistant_ask,
            "load_character_data",
            lambda _character: {
                "name": "Character",
                "visual": {"base_prompt": "character tags", "default_clothing": "uniform"},
            },
        )
        monkeypatch.setattr(
            third_assistant_ask,
            "get_character_full_state",
            lambda *_args: resolved({"current_clothing": "uniform"}),
        )
        monkeypatch.setattr(
            third_assistant_ask,
            "send_http_post",
            send_http_post,
        )

        prompt = await third_assistant_ask.third_assistant_ask(1, None, "Narrator scene", "model")
        await third_assistant_ask.third_assistant_ask(1, "char-a", "Narrator scene", "model")

        assert prompt == "masterpiece, best quality, cinematic lighting, atmospheric"
        assert payloads[0]["think"] is False
        assert payloads[0]["keep_alive"] == 0
        assert payloads[1]["think"] is False
        assert "keep_alive" not in payloads[1]

    asyncio.run(run_test())
