import types
import pytest

from bot.jobs.deadline import deadline_job
from bot.constants import UD_ACTIVE, UD_JOB, BD_CONTACTS


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
