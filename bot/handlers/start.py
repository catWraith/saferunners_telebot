from telegram import Update
from telegram.ext import ContextTypes
from bot.config import DEFAULT_TZ
from bot.utils.time_utils import is_valid_tz
from bot.utils.contacts import add_contact, list_contacts, remove_contact_everywhere
from bot.utils.links import build_deep_link
from bot.constants import UD_TZ


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    tz = context.user_data.get(UD_TZ, DEFAULT_TZ)
    msg = (
        f"Hi {user.first_name or 'there'}! I’ll watch your exercise sessions.\n\n"
        "• Use /link to generate your personal invite link. Share it with people you want alerted.\n"
        "  They must open your link and press Start so I can DM them if needed.\n"
        "• Use /begin to start a session: send your location (GPS or text) and your planned end time.\n"
        "• Tap **Complete ✅** when you’re done. If you don’t, I’ll notify your contacts at the deadline.\n\n"
        f"Current timezone: {tz} (change with /tz <IANA_tz>, e.g. /tz Asia/Singapore)"
    )
    await update.effective_chat.send_message(msg)


async def tz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_chat.send_message(
            f"Usage: /tz <IANA_timezone>\nExample: /tz Asia/Singapore\n"
            f"Current: {context.user_data.get(UD_TZ, DEFAULT_TZ)}"
        )
        return
    tzname = " ".join(context.args).strip()
    if not is_valid_tz(tzname):
        await update.effective_chat.send_message("Sorry, that timezone is not recognized.")
        return
    context.user_data[UD_TZ] = tzname
    await update.effective_chat.send_message(f"Timezone set to {tzname}.")


async def link_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    owner_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    deep_link = build_deep_link(bot_username, owner_id)
    cnt = len(list_contacts(context.bot_data, owner_id))
    await update.effective_chat.send_message(
        f"Share this link with people you want alerted:\n{deep_link}\n\n"
        f"They must open it and press Start. Currently authorized contacts: {cnt}\n"
        f"You can check again with /contacts"
    )


async def contacts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    owner_id = update.effective_user.id
    ids = list_contacts(context.bot_data, owner_id)
    if not ids:
        await update.effective_chat.send_message("No authorized contacts yet. Share /link.")
        return
    await update.effective_chat.send_message(f"Authorized contacts: {len(ids)}")


async def stopalerts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    removed = remove_contact_everywhere(context.bot_data, chat_id)
    if removed:
        await update.effective_chat.send_message("You’ll no longer receive alerts.")
    else:
        await update.effective_chat.send_message("You weren’t subscribed to any alerts.")


async def start_param_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle deep-link parameter for contact authorization: /start link_<owner_id>"""
    message = update.message or update.edited_message
    if not message or not message.text:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return
    param = parts[1].strip()
    if not param.startswith("link_"):
        return

    try:
        owner_id = int(param.split("_", 1)[1])
    except Exception:
        await update.effective_chat.send_message("Invalid link parameter.")
        return

    add_contact(context.bot_data, owner_id, update.effective_chat.id)
    await update.effective_chat.send_message(
        "You’re now authorized to receive alert messages if this user misses their exercise check-in. "
        "You can /stopalerts later to opt out."
    )
