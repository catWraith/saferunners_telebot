from datetime import timezone, datetime
from telegram.ext import ContextTypes

from bot.utils.contacts import list_contacts
from bot.constants import UD_ACTIVE, UD_JOB


async def deadline_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Notifies contacts if the user missed their completion deadline."""
    job = context.job
    chat_id = job.chat_id
    user = await context.bot.get_chat(chat_id)

    session = context.user_data.get(UD_ACTIVE)
    # If session was cleared already, nothing to do
    if not session or not session.get("end_dt_utc"):
        return

    # Mark session handled
    context.user_data[UD_ACTIVE] = None
    context.user_data[UD_JOB] = None

    try:
        await context.bot.send_message(
            chat_id,
            "⚠️ End time reached and no completion recorded. Notifying your contacts now.",
        )
    except Exception:
        pass

    contacts = list_contacts(context.bot_data, user.id)
    if not contacts:
        try:
            await context.bot.send_message(chat_id, "No authorized contacts found. Use /link to add some.")
        except Exception:
            pass
        return

    alert_text = (
        f"⚠️ Safety alert for {user.full_name or 'the user'}\n"
        "They did not check in as completed by their planned end time.\n"
    )

    loc = session.get("location")
    for cid in contacts:
        try:
            await context.bot.send_message(cid, alert_text)
            if loc:
                if loc.get("type") == "coords":
                    await context.bot.send_location(cid, latitude=loc["lat"], longitude=loc["lon"])
                elif loc.get("type") == "text":
                    await context.bot.send_message(cid, f"Last reported location: {loc['text']}")
        except Exception:
            # ignore individual DM failures
            pass

    try:
        await context.bot.send_message(chat_id, f"Attempted to notify {len(contacts)} contact(s).")
    except Exception:
        pass
