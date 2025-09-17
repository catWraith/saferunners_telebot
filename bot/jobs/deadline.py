import logging
from telegram.ext import ContextTypes
from bot.utils.contacts import list_contacts
from bot.constants import UD_ACTIVE, UD_JOB, BD_BLACKLIST

logger = logging.getLogger(__name__)

async def deadline_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    chat_id = job.chat_id
    payload = getattr(job, "data", None) or {}
    owner_id = payload.get("owner_id")

    # If the session was cancelled or completed, bail
    if payload.get("cancelled"):
        return

    # For friendliness, we still DM the runner (chat_id)
    try:
        await context.bot.send_message(
            chat_id,
            "⚠️ End time reached and no completion recorded. Notifying your contacts now.",
        )
    except Exception as e:
        logger.warning("deadline_job: failed to notify runner chat_id=%s: %s", chat_id, e)

    # Alert contacts (fetched live from bot_data so additions/removals since scheduling are reflected)
    if not owner_id:
        # fallback: try to resolve owner as chat_id (runner), which is typical
        owner_id = chat_id

    contacts = list_contacts(context.bot_data, owner_id)
    # Skip contacts who blacklisted this runner
    blmap = context.bot_data.get(BD_BLACKLIST, {})
    session = context.user_data.get(UD_ACTIVE, {})
    loc = payload.get("location") or session.get("location")

    if not contacts:
        try:
            await context.bot.send_message(chat_id, "No authorized contacts found. Use /link to add some.")
        except Exception:
            pass
        return

    # Compose + send
    who = "the user"
    try:
        chat_info = await context.bot.get_chat(owner_id)  # safe; just for name
        who = chat_info.full_name or "the user"
    except Exception:
        pass

    owner_identifier = owner_id

    alert_text = (
        f"⚠️ Safety alert for {who}, {owner_identifier}\n"
        "They did not check in as completed by their planned end time.\n"
    )

    for cid in contacts:
        bl = blmap.get(str(cid), [])
        if owner_identifier in bl:
            continue
        try:
            await context.bot.send_message(cid, alert_text)
            if loc:
                if loc.get("type") == "coords":
                    await context.bot.send_location(cid, latitude=loc["lat"], longitude=loc["lon"])
                elif loc.get("type") == "text":
                    await context.bot.send_message(cid, f"Last reported location: {loc['text']}")
        except Exception as e:
            # Common case: contact never pressed Start => 403; we ignore individual failures
            logger.info("deadline_job: failed DM to contact %s: %s", cid, e)

    # Tell runner how many we attempted
    try:
        await context.bot.send_message(chat_id, f"Attempted to notify {len(contacts)} contact(s).")
    except Exception:
        pass

    # Clear session state now that the deadline ran.
    context.user_data.pop(UD_ACTIVE, None)
    context.user_data.pop(UD_JOB, None)
