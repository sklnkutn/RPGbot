import asyncio
import json
import sys
from pathlib import Path

import pytest

DEBUG_DIR = Path(__file__).resolve().parents[1] / "debug"
sys.path.insert(0, str(DEBUG_DIR))
import main_debug


class FakeRequest:
    def __init__(self, *, payload=None, prompt_id=None, query=None):
        self.payload = payload
        self.match_info = {"prompt_id": prompt_id} if prompt_id else {}
        self.query = query or {}

    async def json(self):
        return self.payload


@pytest.fixture
def debug_bridge(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()

    def save_request(endpoint, payload):
        request_file = output_dir / f"20261019_120000_001_{endpoint}.json"
        request_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return str(request_file)

    monkeypatch.setattr(main_debug, "INPUT_DIR", input_dir)
    monkeypatch.setattr(main_debug, "save_request_json", save_request)
    monkeypatch.setitem(main_debug.debug_state, "mode", "local")
    monkeypatch.setattr(main_debug, "COMFY_TASKS", {})
    monkeypatch.setattr(main_debug, "COMFY_IMAGES", {})
    monkeypatch.setattr(main_debug, "MODEL_LIST_CACHE", {})
    monkeypatch.setattr(main_debug, "MODEL_LIST_TASKS", {})
    monkeypatch.setattr(main_debug, "pending_tasks", [])
    return input_dir, output_dir


def run(coroutine):
    return asyncio.run(coroutine)


def test_local_mode_returns_mock_model_lists(debug_bridge):
    async def exercise():
        ollama = await main_debug.handle_ollama_tags(FakeRequest())
        comfy = await main_debug.handle_comfy_models(FakeRequest())

        assert ollama.status == 200
        assert json.loads(ollama.text) == main_debug.get_local_ollama_models()
        assert comfy.status == 200
        assert json.loads(comfy.text) == main_debug.get_local_comfy_models()

    run(exercise())


def test_local_mode_mocks_ollama_chat_and_comfy_generation(debug_bridge):
    async def exercise():
        payload = {
            "model": "test-model",
            "messages": [
                {"role": "system", "content": "Initialize the game"},
                {"role": "user", "content": "start"},
            ],
        }
        ollama = await main_debug.handle_ollama_chat(FakeRequest(payload=payload))
        ollama_data = json.loads(ollama.text)

        assert ollama.status == 200
        assert ollama_data["message"]["content"]
        assert main_debug.pending_tasks[-1]["status"] == "auto_mocked"

        queued = await main_debug.handle_comfy_prompt(FakeRequest(payload={"prompt": {"1": {}}}))
        prompt_id = json.loads(queued.text)["prompt_id"]
        history = await main_debug.handle_comfy_history(FakeRequest(prompt_id=prompt_id))

        assert queued.status == 200
        assert json.loads(history.text)[prompt_id]["status"]["status_str"] == "success"
        assert json.loads(history.text)[prompt_id]["outputs"]["9"]["images"][0]["filename"] == "in_prog.png"

    run(exercise())


@pytest.mark.parametrize(
    ("handler_name", "endpoint", "response_data"),
    [
        (
            "handle_ollama_tags",
            "ollama_tags",
            {"models": [{"name": "llama3.1:8b"}, {"name": "qwen2.5:7b"}]},
        ),
        (
            "handle_comfy_models",
            "comfy_models_checkpoints",
            ["checkpoint-a.safetensors", "checkpoint-b.safetensors"],
        ),
    ],
)
def test_bridge_model_get_waits_for_real_response_then_caches(
    debug_bridge, handler_name, endpoint, response_data
):
    input_dir, output_dir = debug_bridge
    main_debug.debug_state["mode"] = "bridge"
    handler = getattr(main_debug, handler_name)

    async def exercise():
        first = await handler(FakeRequest())
        request_file = output_dir / f"20261019_120000_001_{endpoint}.json"
        assert first.status == 503
        assert json.loads(first.text)["status"] == "pending"
        request_payload = json.loads(request_file.read_text(encoding="utf-8"))
        assert request_payload["bridge_type"] == "model_list"

        returned_file = input_dir / request_file.name
        returned_file.write_text(json.dumps(response_data), encoding="utf-8")

        second = await handler(FakeRequest())
        assert second.status == 200
        assert json.loads(second.text) == response_data
        assert not returned_file.exists()

        third = await handler(FakeRequest())
        assert third.status == 200
        assert json.loads(third.text) == response_data
        assert len(main_debug.pending_tasks) == 1

    run(exercise())


def test_bridge_model_get_rejects_invalid_response_without_caching(debug_bridge):
    input_dir, output_dir = debug_bridge
    main_debug.debug_state["mode"] = "bridge"
    request_file = output_dir / "20261019_120000_001_ollama_tags.json"

    async def exercise():
        first = await main_debug.handle_ollama_tags(FakeRequest())
        assert first.status == 503
        (input_dir / request_file.name).write_text(json.dumps({"models": ["not-an-object"]}), encoding="utf-8")

        invalid = await main_debug.handle_ollama_tags(FakeRequest())
        assert invalid.status == 502
        assert "ollama:/api/tags" not in main_debug.MODEL_LIST_CACHE

        (input_dir / request_file.name).write_text(
            json.dumps({"models": [{"name": "actual-model"}]}),
            encoding="utf-8",
        )
        valid = await main_debug.handle_ollama_tags(FakeRequest())
        assert valid.status == 200
        assert json.loads(valid.text) == {"models": [{"name": "actual-model"}]}

    run(exercise())


def test_bridge_ollama_post_returns_matching_input_file(debug_bridge):
    input_dir, output_dir = debug_bridge
    main_debug.debug_state["mode"] = "bridge"
    request_payload = {
        "model": "llama3.1:8b",
        "messages": [{"role": "user", "content": "test"}],
    }

    async def exercise():
        async def deliver_response():
            await asyncio.sleep(0.05)
            input_file = output_dir / "20261019_120000_001_api_chat.json"
            (input_dir / input_file.name).write_text(
                json.dumps({"model": "llama3.1:8b", "message": {"role": "assistant", "content": "ok"}}),
                encoding="utf-8",
            )

        delivery = asyncio.create_task(deliver_response())
        response = await main_debug.handle_ollama_chat(FakeRequest(payload=request_payload))
        await delivery

        assert response.status == 200
        assert json.loads(response.text)["message"]["content"] == "ok"
        assert not (input_dir / "20261019_120000_001_api_chat.json").exists()
        assert main_debug.pending_tasks[-1]["status"] == "completed"

    run(exercise())


def test_bridge_comfy_post_waits_for_response_and_serves_real_image(debug_bridge):
    input_dir, _ = debug_bridge
    main_debug.debug_state["mode"] = "bridge"

    async def exercise():
        queued = await main_debug.handle_comfy_prompt(FakeRequest(payload={"prompt": {"1": {}}}))
        prompt_id = json.loads(queued.text)["prompt_id"]

        waiting = await main_debug.handle_comfy_history(FakeRequest(prompt_id=prompt_id))
        assert json.loads(waiting.text)[prompt_id]["status"]["completed"] is False

        response_name = "20261019_120000_001_comfy_prompt.json"
        image_name = "20261019_120000_001_comfy_prompt.png"
        (input_dir / image_name).write_bytes(b"generated-image")
        (input_dir / response_name).write_text(
            json.dumps({"status": "completed", "image_filename": image_name}),
            encoding="utf-8",
        )

        completed = await main_debug.handle_comfy_history(FakeRequest(prompt_id=prompt_id))
        completed_data = json.loads(completed.text)[prompt_id]
        assert completed_data["status"]["status_str"] == "success"
        assert completed_data["outputs"]["9"]["images"][0]["filename"] == image_name

        image_response = await main_debug.handle_comfy_view(FakeRequest(query={"filename": image_name}))
        assert image_response.status == 200
        assert image_response.headers["Content-Type"] == "image/png"

    run(exercise())
