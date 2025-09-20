import types
from datetime import datetime, timedelta, timezone

import pytest

from bot.jobs.deadline import deadline_job
from bot.constants import UD_ACTIVE, UD_JOB, BD_CONTACTS
from bot.handlers.session import button_handler


class FakeBot:
    def __init__(self):
        self.outbox = []

    async def get_chat(self, chat_id):
        # Return minimal object with .full_name
        return types.SimpleNamespace(full_name="Owner Name")

    async def send_message(self, chat_id, text):
        self.outbox.append(("message", chat_id, text))

    async def send_location(self, chat_id, latitude, longitude):
        self.outbox.append(("location", chat_id, latitude, longitude))


class FakeJob:
    def __init__(self, chat_id):
        self.chat_id = chat_id


class FakeContext:
    def __init__(self, owner_chat_id, contacts):
        self.bot = FakeBot()
        self.job = FakeJob(owner_chat_id)
        # Preload user_data with an active session
        self.user_data = {
            UD_ACTIVE: {
                "end_dt_utc": "2099-01-01T00:00:00+00:00",  # presence triggers alert path
                "location": {"type": "coords", "lat": 1.3000, "lon": 103.8000},
            },
            UD_JOB: None,
        }
        self.bot_data = {
            BD_CONTACTS: {str(owner_chat_id): contacts[:]},
        }


@pytest.mark.asyncio
async def test_deadline_notifies_all_contacts_and_owner_ack():
    owner = 999
    contacts = [11, 22]
    ctx = FakeContext(owner, contacts)

    # Run the job
    await deadline_job(ctx)

    # Owner should get two messages: "time reached" + "attempted to notify X"
    owner_msgs = [o for o in ctx.bot.outbox if o[1] == owner and o[0] == "message"]
    assert any("Notifying your contacts" in o[2] for o in owner_msgs)
    assert any("Attempted to notify 2" in o[2] for o in owner_msgs)

    # Contacts should receive an alert and a location
    for cid in contacts:
        assert any(o[0] == "message" and o[1] == cid for o in ctx.bot.outbox)
        assert any(o[0] == "location" and o[1] == cid for o in ctx.bot.outbox)

    # Session should be cleared
    assert ctx.user_data.get(UD_ACTIVE) is None


class DummyJob:
    def __init__(self, data=None):
        self.data = data or {}
        self.removed = False

    def schedule_removal(self):
        self.removed = True


class DummyJobQueue:
    def __init__(self):
        self.calls = []

    def run_once(self, callback, delay, chat_id=None, user_id=None, name=None, data=None):
        job = DummyJob(data)
        job.delay = delay
        self.calls.append(
            types.SimpleNamespace(
                callback=callback,
                delay=delay,
                chat_id=chat_id,
                user_id=user_id,
                name=name,
                data=data,
            )
        )
        return job


class DummyChat:
    def __init__(self, chat_id):
        self.id = chat_id
        self.messages = []

    async def send_message(self, text, reply_markup=None):
        self.messages.append((text, reply_markup))


class DummyQuery:
    def __init__(self, chat_id):
        self.data = "extend:15"
        self.message = types.SimpleNamespace(chat=types.SimpleNamespace(id=chat_id))
        self.answered = False
        self.edited_text = None
        self.reply_markup = None

    async def answer(self):
        self.answered = True

    async def edit_message_text(self, text, reply_markup=None):
        self.edited_text = text
        self.reply_markup = reply_markup


@pytest.mark.asyncio
async def test_button_handler_extend_reschedules_job():
    owner_id = 123
    old_deadline = datetime(2099, 1, 1, tzinfo=timezone.utc)
    old_iso = old_deadline.isoformat()
    expected_iso = (old_deadline + timedelta(minutes=15)).isoformat()

    chat = DummyChat(owner_id)
    query = DummyQuery(owner_id)
    update = types.SimpleNamespace(
        callback_query=query,
        effective_chat=chat,
        effective_user=types.SimpleNamespace(id=owner_id),
    )

    job_queue = DummyJobQueue()
    existing_job = DummyJob({"deadline_iso": old_iso})

    context = types.SimpleNamespace(
        user_data={
            UD_ACTIVE: {"end_dt_utc": old_iso, "location": {"type": "text", "text": "Trail"}},
            UD_JOB: existing_job,
        },
        job_queue=job_queue,
    )

    await button_handler(update, context)

    assert existing_job.removed is True
    assert context.user_data[UD_ACTIVE]["end_dt_utc"] == expected_iso
    new_job = context.user_data[UD_JOB]
    assert new_job is not existing_job
    assert new_job.data["deadline_iso"] == expected_iso
    assert job_queue.calls, "run_once should be invoked"
    assert job_queue.calls[0].callback is deadline_job
    assert job_queue.calls[0].delay > 0

    assert query.edited_text is not None
    assert "08:15" in query.edited_text
    assert query.reply_markup is not None
    # Ensure extend buttons remain available
    extend_callbacks = [
        btn.callback_data
        for row in query.reply_markup.inline_keyboard
        for btn in row
        if hasattr(btn, "callback_data")
    ]
    assert "extend:15" in extend_callbacks
    assert "extend:30" in extend_callbacks
