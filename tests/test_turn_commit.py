import asyncio
import sqlite3

import aiosqlite
import pytest

from services import db
from engine import main_engine
from ui.components import chat_logic


def test_commit_player_turn_saves_messages_and_character_state_atomically(tmp_path, monkeypatch):
    async def run_test():
        db_path = tmp_path / "turn.db"
        monkeypatch.setattr(db, "DB_NAME", str(db_path))

        async with aiosqlite.connect(db_path) as connection:
            await connection.executescript(
                """
                CREATE TABLE sessions (id INTEGER PRIMARY KEY);
                CREATE TABLE session_characters (
                    session_id INTEGER NOT NULL,
                    character_id TEXT NOT NULL,
                    character_status TEXT NOT NULL,
                    trust INTEGER,
                    respect INTEGER,
                    affection INTEGER,
                    annoyance INTEGER,
                    fear INTEGER,
                    jealousy INTEGER,
                    current_clothing TEXT
                );
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY,
                    session_id INTEGER NOT NULL,
                    sender TEXT NOT NULL,
                    text TEXT NOT NULL,
                    image_path TEXT,
                    character_id TEXT
                );
                INSERT INTO sessions (id) VALUES (1);
                INSERT INTO session_characters (
                    session_id, character_id, character_status, trust, respect,
                    affection, annoyance, fear, jealousy, current_clothing
                ) VALUES (1, 'char_1', 'inactive', 98, 0, 0, 0, 0, 0, 'uniform');
                """
            )

        await db.commit_player_turn(
            session_id=1,
            user_text="Иду к двери",
            narrator_text="Дверь открывается.",
            image_path="/outputs/scene.png",
            character_id="char_1",
            character_state={
                "deltas": {"trust": 5},
                "new_clothing": None,
                "leaves_scene": False,
            },
        )

        async with aiosqlite.connect(db_path) as connection:
            messages = await (await connection.execute(
                "SELECT sender, text, image_path FROM messages ORDER BY id"
            )).fetchall()
            character = await (await connection.execute(
                """
                SELECT character_status, trust, current_clothing
                FROM session_characters
                WHERE session_id = 1 AND character_id = 'char_1'
                """
            )).fetchone()

        assert messages == [
            ("user", "Иду к двери", None),
            ("assistant", "Дверь открывается.", "/outputs/scene.png"),
        ]
        assert character == ("active", 100, "uniform")

    asyncio.run(run_test())


def test_commit_player_turn_rolls_back_state_and_messages_if_message_insert_fails(tmp_path, monkeypatch):
    async def run_test():
        db_path = tmp_path / "turn.db"
        monkeypatch.setattr(db, "DB_NAME", str(db_path))

        async with aiosqlite.connect(db_path) as connection:
            await connection.executescript(
                """
                CREATE TABLE session_characters (
                    session_id INTEGER NOT NULL,
                    character_id TEXT NOT NULL,
                    character_status TEXT NOT NULL,
                    trust INTEGER,
                    respect INTEGER,
                    affection INTEGER,
                    annoyance INTEGER,
                    fear INTEGER,
                    jealousy INTEGER,
                    current_clothing TEXT
                );
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY,
                    session_id INTEGER NOT NULL,
                    sender TEXT NOT NULL,
                    text TEXT NOT NULL,
                    image_path TEXT,
                    character_id TEXT,
                    CHECK (sender != 'assistant' OR text != 'reject')
                );
                INSERT INTO session_characters (
                    session_id, character_id, character_status, trust, respect,
                    affection, annoyance, fear, jealousy, current_clothing
                ) VALUES (7, 'char_1', 'inactive', 40, 0, 0, 0, 0, 0, 'uniform');
                """
            )

        with pytest.raises(sqlite3.IntegrityError):
            await db.commit_player_turn(
                session_id=7,
                user_text="Иду к двери",
                narrator_text="reject",
                image_path="/outputs/scene.png",
                character_id="char_1",
                character_state={
                    "deltas": {"trust": 5},
                    "new_clothing": "new uniform",
                    "leaves_scene": True,
                },
            )

        async with aiosqlite.connect(db_path) as connection:
            message_count = (await (await connection.execute(
                "SELECT COUNT(*) FROM messages"
            )).fetchone())[0]
            character = await (await connection.execute(
                """
                SELECT character_status, trust, current_clothing
                FROM session_characters
                WHERE session_id = 7 AND character_id = 'char_1'
                """
            )).fetchone()

        assert message_count == 0
        assert character == ("inactive", 40, "uniform")

    asyncio.run(run_test())


def test_image_failure_does_not_commit_player_turn(monkeypatch):
    async def run_test():
        commit_called = False

        async def get_session_info(_session_id):
            return {
                "state": "in_progress",
                "adventure_id": "adventure",
                "llm_model": "model",
                "comfy_model": "checkpoint",
            }

        async def get_active_session_characters(_session_id):
            return []

        async def first_assistant_ask(**_kwargs):
            return None

        async def second_assistant_ask(**_kwargs):
            return "Сцена нарратора."

        async def third_assistant_ask(**_kwargs):
            return "scene prompt"

        async def generate_comfy_image(**_kwargs):
            return None

        async def commit_player_turn(**_kwargs):
            nonlocal commit_called
            commit_called = True

        monkeypatch.setattr(main_engine, "get_session_info", get_session_info)
        monkeypatch.setattr(main_engine, "get_active_session_characters", get_active_session_characters)
        monkeypatch.setattr(main_engine, "first_assistant_ask", first_assistant_ask)
        monkeypatch.setattr(main_engine, "second_assistant_ask", second_assistant_ask)
        monkeypatch.setattr(main_engine, "third_assistant_ask", third_assistant_ask)
        monkeypatch.setattr(main_engine, "generate_comfy_image", generate_comfy_image)
        monkeypatch.setattr(main_engine, "commit_player_turn", commit_player_turn)

        with pytest.raises(RuntimeError, match="ComfyUI"):
            await main_engine.process_player_turn(session_id=1, user_text="Действие игрока")

        assert not commit_called

    asyncio.run(run_test())


def test_turn_is_rendered_before_summarization(monkeypatch):
    async def run_test():
        events = []

        async def get_session_info(_session_id):
            return {
                "state": "in_progress",
                "adventure_id": "adventure",
                "llm_model": "model",
                "comfy_model": "checkpoint",
            }

        async def get_active_session_characters(_session_id):
            return []

        async def first_assistant_ask(**_kwargs):
            return None

        async def second_assistant_ask(**_kwargs):
            return "Сцена нарратора."

        async def third_assistant_ask(**_kwargs):
            return "scene prompt"

        async def generate_comfy_image(**_kwargs):
            return "/outputs/scene.png"

        async def commit_player_turn(**_kwargs):
            events.append("commit")

        async def on_turn_committed():
            events.append("render")

        async def get_unsummarized_messages(_session_id):
            return ["message"]

        async def fifth_assistant_ask(**_kwargs):
            events.append("summarize")

        monkeypatch.setattr(main_engine, "get_session_info", get_session_info)
        monkeypatch.setattr(main_engine, "get_active_session_characters", get_active_session_characters)
        monkeypatch.setattr(main_engine, "first_assistant_ask", first_assistant_ask)
        monkeypatch.setattr(main_engine, "second_assistant_ask", second_assistant_ask)
        monkeypatch.setattr(main_engine, "third_assistant_ask", third_assistant_ask)
        monkeypatch.setattr(main_engine, "generate_comfy_image", generate_comfy_image)
        monkeypatch.setattr(main_engine, "commit_player_turn", commit_player_turn)
        monkeypatch.setattr(main_engine, "get_unsummarized_messages", get_unsummarized_messages)
        monkeypatch.setattr(main_engine, "fifth_assistant_ask", fifth_assistant_ask)
        monkeypatch.setattr(main_engine, "MAX_MESSAGE_COUNT_BEFORE_SUMM", 1)

        await main_engine.process_player_turn(
            session_id=1,
            user_text="Действие игрока",
            on_turn_committed=on_turn_committed,
        )

        assert events == ["commit", "render", "summarize"]

    asyncio.run(run_test())


def test_chat_allows_drafting_but_not_sending_during_summarization(monkeypatch):
    class FakeInput:
        value = "Действие игрока"
        enabled = True

        def disable(self):
            self.enabled = False

        def enable(self):
            self.enabled = True

    class FakeButton:
        enabled = True

        def disable(self):
            self.enabled = False

        def enable(self):
            self.enabled = True

        def props(self, *_args, **_kwargs):
            return self

    async def run_test():
        user_input = FakeInput()
        send_button = FakeButton()
        observed_states = []

        async def render_messages(*_args):
            observed_states.append(("render", user_input.enabled, send_button.enabled))

        async def process_player_turn(**kwargs):
            await kwargs["on_turn_committed"]()
            observed_states.append(("summarizing", user_input.enabled, send_button.enabled))
            user_input.value = "Черновик следующего действия"

        monkeypatch.setattr(chat_logic, "render_messages", render_messages)
        monkeypatch.setattr(chat_logic, "process_player_turn", process_player_turn)
        monkeypatch.setattr(chat_logic.ui, "notify", lambda *_args, **_kwargs: None)

        await chat_logic.handle_send(
            session_id=987654,
            user_input=user_input,
            chat_container=None,
            chat_scroll=None,
            send_button=send_button,
        )

        assert observed_states == [
            ("render", False, False),
            ("summarizing", True, False),
        ]
        assert user_input.value == "Черновик следующего действия"
        assert user_input.enabled
        assert send_button.enabled

    asyncio.run(run_test())
