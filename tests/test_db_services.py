import asyncio

import aiosqlite
import pytest

from services import db


def test_init_db_adds_secondary_model_to_existing_sessions_table(tmp_path, monkeypatch):
    async def run_test():
        monkeypatch.setattr(db, "DB_NAME", str(tmp_path / "existing.db"))
        async with aiosqlite.connect(db.DB_NAME) as connection:
            await connection.execute("""
                CREATE TABLE sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    state TEXT NOT NULL DEFAULT 'in_progress',
                    adventure_id TEXT NOT NULL,
                    llm_model TEXT NOT NULL,
                    comfy_model TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await connection.execute(
                """
                INSERT INTO sessions (adventure_id, llm_model, comfy_model)
                VALUES ('adventure', 'legacy-model', 'checkpoint')
                """
            )
            await connection.commit()

        await db.init_db()

        assert await db.get_session_info(1) == {
            "adventure_id": "adventure",
            "llm_model": "legacy-model",
            "secondary_llm_model": "legacy-model",
            "comfy_model": "checkpoint",
            "state": "in_progress",
        }

    asyncio.run(run_test())


def test_session_messages_character_state_and_summaries_round_trip(tmp_path, monkeypatch):
    async def run_test():
        monkeypatch.setattr(db, "DB_NAME", str(tmp_path / "session.db"))
        await db.init_db()

        session_id = await db.create_session(
            adventure_id="deserted_island",
            llm_model="llama3",
            secondary_llm_model="llama3",
            comfy_model="checkpoint",
            character_ids=["char_black_widow"],
        )
        assert (await db.get_session_info(session_id)) == {
            "adventure_id": "deserted_island",
            "llm_model": "llama3",
            "secondary_llm_model": "llama3",
            "comfy_model": "checkpoint",
            "state": "in_progress",
        }
        assert await db.get_session_info(session_id + 1) == {}
        assert await db.get_session_characters_list(session_id) == ["char_black_widow"]
        assert await db.get_active_session_characters(session_id) == []

        initial_state = await db.get_character_full_state(session_id, "char_black_widow")
        assert initial_state["current_clothing"] == "cleavage, black bodysuit, belt"
        assert initial_state["about_player"] == []

        await db.save_message(session_id, "user", "Проверяю берег")
        await db.save_message(session_id, "assistant", "На песке видны следы.")
        await db.save_message(session_id, "user", "Иду по следам")

        messages = await db.get_session_messages(session_id)
        assert [message["text"] for message in messages] == [
            "Проверяю берег",
            "На песке видны следы.",
            "Иду по следам",
        ]
        assert await db.get_recent_session_messages(session_id, limit=2) == [
            {"sender": "assistant", "text": "На песке видны следы."},
            {"sender": "user", "text": "Иду по следам"},
        ]
        assert db._get_last_messages(messages) == ("На песке видны следы.", "Иду по следам")

        await db.update_character_status(session_id, "char_black_widow", "active")
        assert await db.get_active_session_characters(session_id) == ["char_black_widow"]
        await db.update_character_turn_state(
            session_id,
            "char_black_widow",
            {"trust": 120, "fear": -120},
            "  field jacket  ",
            leaves_scene=True,
        )
        updated_state = await db.get_character_full_state(session_id, "char_black_widow")
        assert updated_state["trust"] == 100
        assert updated_state["fear"] == -100
        assert updated_state["current_clothing"] == "field jacket"
        assert updated_state["character_status"] == "inactive"

        await db.append_character_memories(
            session_id,
            "char_black_widow",
            {
                "about_player": ["Игрок изучает следы"],
                "about_world": ["На берегу обнаружены следы"],
                "about_self": ["Я должна проверить берег"],
            },
        )
        await db.append_character_memories(
            session_id,
            "char_black_widow",
            {"about_player": ["Игрок изучает следы", "Игрок действует осторожно"]},
        )
        assert (await db.get_character_full_state(session_id, "char_black_widow"))["about_player"] == [
            "Игрок изучает следы",
            "Игрок действует осторожно",
        ]

        chunk = await db.get_chunk_for_summarization(session_id, chunk_size=2)
        assert [message["text"] for message in chunk] == ["Проверяю берег", "На песке видны следы."]
        assert len(await db.get_unsummarized_messages(session_id)) == 3
        await db.mark_messages_as_summarized([message["id"] for message in chunk])
        await db.save_session_summary_chunk(
            session_id,
            chunk[0]["id"],
            chunk[-1]["id"],
            "Игрок обнаружил следы на берегу.",
        )
        assert await db.get_unsummarized_messages(session_id) == [
            {"id": chunk[-1]["id"] + 1, "sender": "user", "text": "Иду по следам"}
        ]
        assert await db.get_session_summaries(session_id) == [
            {"chunk_order": 1, "summary_text": "Игрок обнаружил следы на берегу."}
        ]

        await db.mark_messages_as_summarized([])
        assert await db.get_session_messages(session_id)

    asyncio.run(run_test())


def test_create_session_persists_character_initial_facts(tmp_path, monkeypatch):
    async def run_test():
        monkeypatch.setattr(db, "DB_NAME", str(tmp_path / "session.db"))
        await db.init_db()

        session_id = await db.create_session(
            adventure_id="infinity_train",
            llm_model="model",
            secondary_llm_model="secondary-model",
            comfy_model="checkpoint",
            character_ids=["char_mavis_dracula"],
        )
        state = await db.get_character_full_state(session_id, "char_mavis_dracula")

        assert state["current_clothing"] == "striped clothes, vampire, black nails, nail polish, lipstick"
        assert state["character_status"] == "inactive"
        assert state["about_player"] == []
        assert state["about_world"] == []

    asyncio.run(run_test())


def test_get_all_active_sessions_returns_empty_list_when_no_sessions(tmp_path, monkeypatch):
    async def run_test():
        monkeypatch.setattr(db, "DB_NAME", str(tmp_path / "sessions.db"))
        await db.init_db()

        assert await db.get_all_active_sessions() == []

    asyncio.run(run_test())


def test_get_all_active_sessions_filters_states_and_returns_newest_first(tmp_path, monkeypatch):
    async def run_test():
        monkeypatch.setattr(db, "DB_NAME", str(tmp_path / "sessions.db"))
        await db.init_db()

        first_session = await db.create_session(
            "deserted_island", "model-a", "secondary-a", "checkpoint-a", []
        )
        paused_session = await db.create_session(
            "infinity_train", "model-b", "secondary-b", "checkpoint-b", []
        )
        ended_session = await db.create_session(
            "deserted_island", "model-ended", "secondary-ended", "checkpoint-ended", []
        )
        newest_session = await db.create_session(
            "adv_road_777", "model-c", "secondary-c", "checkpoint-c", []
        )

        async with aiosqlite.connect(db.DB_NAME) as connection:
            await connection.executemany(
                "UPDATE sessions SET state = ? WHERE id = ?",
                [
                    (db.GameStates.ON_HOLD.value, paused_session),
                    (db.GameStates.END.value, ended_session),
                ],
            )
            await connection.commit()

        sessions = await db.get_all_active_sessions()

        assert [session["id"] for session in sessions] == [newest_session, first_session]
        assert sessions[0]["adventure_id"] == "adv_road_777"
        assert sessions[0]["llm_model"] == "model-c"
        assert sessions[0]["secondary_llm_model"] == "secondary-c"
        assert sessions[0]["comfy_model"] == "checkpoint-c"
        assert sessions[0]["state"] == db.GameStates.IN_PROGRESS.value
        assert sessions[0]["created_at"]

    asyncio.run(run_test())


@pytest.mark.parametrize("bad_character_state", [None, {}])
def test_commit_player_turn_rejects_missing_or_incomplete_character_state(
    tmp_path, monkeypatch, bad_character_state
):
    async def run_test():
        monkeypatch.setattr(db, "DB_NAME", str(tmp_path / "session.db"))
        await db.init_db()
        session_id = await db.create_session(
            "deserted_island", "model", "secondary-model", "checkpoint", ["char_black_widow"]
        )

        with pytest.raises((ValueError, KeyError)):
            await db.commit_player_turn(
                session_id=session_id,
                user_text="Действие",
                narrator_text="Ответ",
                image_path="/outputs/image.png",
                character_id="char_black_widow",
                character_state=bad_character_state,
            )

        assert await db.get_session_messages(session_id) == []

    asyncio.run(run_test())
