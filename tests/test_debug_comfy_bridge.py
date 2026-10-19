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
def bridge_state(tmp_path, monkeypatch):
    monkeypatch.setitem(main_debug.debug_state, "mode", "bridge")
    monkeypatch.setattr(main_debug, "INPUT_DIR", tmp_path / "input")
    main_debug.INPUT_DIR.mkdir()
    monkeypatch.setattr(
        main_debug,
        "save_request_json",
        lambda _endpoint, _payload: str(tmp_path / "output" / "20261019_120000_001_comfy_prompt.json"),
    )
    main_debug.COMFY_TASKS.clear()
    main_debug.COMFY_IMAGES.clear()
    main_debug.pending_tasks.clear()
    yield tmp_path
    main_debug.COMFY_TASKS.clear()
    main_debug.COMFY_IMAGES.clear()
    main_debug.pending_tasks.clear()


def test_comfy_bridge_waits_for_kaggle_json_and_image(bridge_state):
    async def run_test():
        post_response = await main_debug.handle_comfy_prompt(FakeRequest(payload={"prompt": {"1": {}}}))
        prompt_id = json.loads(post_response.text)["prompt_id"]

        pending_response = await main_debug.handle_comfy_history(FakeRequest(prompt_id=prompt_id))
        pending = json.loads(pending_response.text)[prompt_id]
        assert pending["status"]["completed"] is False
        assert pending["outputs"] == {}

        response_filename = "20261019_120000_001_comfy_prompt.json"
        image_filename = "20261019_120000_001_comfy_prompt.png"
        image_path = main_debug.INPUT_DIR / image_filename
        image_path.write_bytes(b"real-image-bytes")
        (main_debug.INPUT_DIR / response_filename).write_text(
            json.dumps({"status": "completed", "image_filename": image_filename}),
            encoding="utf-8",
        )

        completed_response = await main_debug.handle_comfy_history(FakeRequest(prompt_id=prompt_id))
        completed = json.loads(completed_response.text)[prompt_id]
        assert completed["status"]["status_str"] == "success"
        assert completed["outputs"]["9"]["images"][0]["filename"] == image_filename
        assert main_debug.COMFY_TASKS[prompt_id]["task_info"]["status"] == "completed"

        view_response = await main_debug.handle_comfy_view(
            FakeRequest(query={"filename": image_filename, "subfolder": "", "type": "output"})
        )
        assert view_response.status == 200
        assert view_response.headers["Content-Type"] == "image/png"

    asyncio.run(run_test())


def test_comfy_bridge_reports_kaggle_generation_errors(bridge_state):
    async def run_test():
        post_response = await main_debug.handle_comfy_prompt(FakeRequest(payload={"prompt": {}}))
        prompt_id = json.loads(post_response.text)["prompt_id"]
        response_filename = "20261019_120000_001_comfy_prompt.json"
        (main_debug.INPUT_DIR / response_filename).write_text(
            json.dumps({"status": "error", "error": "checkpoint missing"}),
            encoding="utf-8",
        )

        error_response = await main_debug.handle_comfy_history(FakeRequest(prompt_id=prompt_id))
        error = json.loads(error_response.text)[prompt_id]
        assert error["status"]["status_str"] == "error"
        assert "checkpoint missing" in error["status"]["messages"]

        missing_image_response = await main_debug.handle_comfy_view(
            FakeRequest(query={"filename": "..\\outside.png"})
        )
        assert missing_image_response.status == 404

    asyncio.run(run_test())
