from telegram import Update
from telegram.ext import ContextTypes
from bot.config import DEFAULT_TZ, ALERT_WHEN_ADDED
from bot.utils.time_utils import is_valid_tz
from bot.utils.contacts import (
    add_contact, list_contacts, remove_contact_everywhere,
    remove_contact, blacklist_add, blacklist_remove, blacklist_list
)
from bot.utils.links import build_deep_link, build_contact_offer_link, build_bundle_link
from bot.constants import UD_TZ


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    tz = context.user_data.get(UD_TZ, DEFAULT_TZ)
    msg = (
        f"Hi {user.first_name or 'there'}! I’ll monitor your exercise sessions.\n\n"
        "• Use /link to generate your invite link to share with people you want alerted.\n"
        "They must open your link and press Start so I can DM them if needed.\n"
        "• Use /contactlink to generate your invite link to share with people whom you want to alert you.\n"
        "• Use /begin to start a session: send your location (GPS or text) and your planned end time.\n"
        "• Tap <b>Complete ✅</b> when you’re done. If you don’t, I’ll notify your contacts at the deadline.\n\n"
        f"Current timezone: {tz} (change with /tz <code>IANA_tz</code>, e.g. /tz Asia/Singapore)"
    )
    await update.effective_chat.send_message(msg)


async def tz_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_chat.send_message(
            f"Usage: /tz <code>IANA_timezone</code>\nExample: /tz Asia/Singapore\n"
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

async def contactlink_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    For a CONTACT to share with runners.
    Any runner who taps this link will add THIS contact to their alert list.
    """
    contact_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    deep_link = build_contact_offer_link(bot_username, contact_id)
    await update.effective_chat.send_message(
        "Share this with runners who want you as their alert contact:\n"
        f"{deep_link}\n\n"
        "They must press Start once. You’ll be added to their alert list automatically."
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
    if param and param.startswith("link_"):
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
        return

    if param and param.startswith("contact_"):
        try:
            contact_id = int(param.split("_", 1)[1])
        except Exception:
            await update.effective_chat.send_message("Invalid contact link.")
            return

        runner_id = update.effective_user.id
        # Add the contact to THIS runner’s contact list
        add_contact(context.bot_data, runner_id, contact_id)

        # Try to fetch contact's display name (may fail if Telegram restricts)
        try:
            contact_chat = await context.bot.get_chat(contact_id)
            contact_name = contact_chat.full_name or "this contact"
        except Exception:
            contact_name = "this contact"

        await update.effective_chat.send_message(
            f"Added {contact_name} to your alert list. "
            "Use /contacts to see how many are authorized."
        )

        # (Optional) Let the contact know they were added by someone (best-effort)
        if ALERT_WHEN_ADDED:
            try:
                runner = update.effective_user
                await context.bot.send_message(
                    contact_id,
                    f"Heads up: {runner.full_name or 'A runner'} added you as an alert contact."
                )
            except Exception:
                pass
            return
    
    if param and param.startswith("bundle_"):
        payload = param.split("_", 1)[1]
        # allow comma- or underscore-separated, keep commas preferred (shorter)
        parts = [p for p in payload.replace("_", ",").split(",") if p]
        contact_ids = []
        for p in parts:
            try:
                contact_ids.append(int(p))
            except Exception:
                pass
        if not contact_ids:
            await update.effective_chat.send_message("Invalid bundle link.")
            return
        runner_id = update.effective_user.id
        added = 0
        for cid in dict.fromkeys(contact_ids):  # de-dupe while preserving order
            add_contact(context.bot_data, runner_id, cid)
            added += 1
            # Optional courtesy ping to contact
            if ALERT_WHEN_ADDED:
                try:
                    runner = update.effective_user
                    await context.bot.send_message(
                        cid,
                        f"Heads up: {runner.full_name or 'A runner'} added you as an alert contact (bundle)."
                    )
                except Exception:
                    pass
        await update.effective_chat.send_message(f"Added {added} contact(s) from bundle link. Use /contactlist to view.")
        return
        
async def unlink_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Runner removes a specific contact id from their alert list."""
    if not context.args:
        await update.effective_chat.send_message("Usage: /unlink <contact_id>")
        return
    try:
        cid = int(context.args[0])
    except Exception:
        await update.effective_chat.send_message("Please provide a numeric contact ID.")
        return
    owner_id = update.effective_user.id
    ok = remove_contact(context.bot_data, owner_id, cid)
    if ok:
        await update.effective_chat.send_message(f"Removed {cid} from your contacts.")
    else:
        await update.effective_chat.send_message(f"{cid} wasn’t in your contacts.")

async def contactlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show your contacts with best-effort names."""
    owner_id = update.effective_user.id
    ids = list_contacts(context.bot_data, owner_id)
    if not ids:
        await update.effective_chat.send_message("You have no contacts yet. Use /link or tap someone’s /contactlink.")
        return
    lines = []
    for cid in ids:
        try:
            chat = await context.bot.get_chat(cid)
            name = chat.full_name or str(cid)
        except Exception:
            name = str(cid)
        lines.append(f"• {name} (ID {cid})")
    await update.effective_chat.send_message("Your contacts:\n" + "\n".join(lines))

async def blacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Contacts control which runner IDs they will NOT receive alerts from.
    Usage:
      /blacklist list
      /blacklist add <runner_id>
      /blacklist remove <runner_id>
    """
    user_id = update.effective_user.id
    if not context.args:
        await update.effective_chat.send_message(
            "Usage:\n"
            "/blacklist list\n"
            "/blacklist add <runner_id>\n"
            "/blacklist remove <runner_id>\n\n"
            "Replace <runner_id> with the numeric ID of the runner you want to block."
        )
        return
    sub = context.args[0].lower()
    if sub == "list":
        bl = blacklist_list(context.bot_data, user_id)
        if not bl:
            await update.effective_chat.send_message("Your blacklist is empty.")
        else:
            await update.effective_chat.send_message("Blacklisted runner IDs:\n" + ", ".join(map(str, bl)))
        return
    if sub in ("add", "remove"):
        if len(context.args) < 2:
            await update.effective_chat.send_message(f"Usage: /blacklist {sub} <runner_id>")
            return
        try:
            rid = int(context.args[1])
        except Exception:
            await update.effective_chat.send_message("runner_id must be numeric.")
            return
        if sub == "add":
            blacklist_add(context.bot_data, user_id, rid)
            await update.effective_chat.send_message(f"Added {rid} to your blacklist.")
        else:
            ok = blacklist_remove(context.bot_data, user_id, rid)
            if ok:
                await update.effective_chat.send_message(f"Removed {rid} from your blacklist.")
            else:
                await update.effective_chat.send_message(f"{rid} wasn’t in your blacklist.")
        return
    await update.effective_chat.send_message("Unknown subcommand. Use: list, add, remove.")

async def bundle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Create one link that adds MULTIPLE contacts to a runner when clicked.
    Usage: /bundle <id1> <id2> ... [me]
    Tip: Keep it short (Telegram start param is limited). Aim ≤ 5 IDs.
    """
    args = context.args or []
    if not args:
        await update.effective_chat.send_message("Usage: /bundle <id1> <id2> ... [me]")
        return
    contact_ids = []
    for a in args:
        if a.lower() == "me":
            contact_ids.append(update.effective_user.id)
        else:
            try:
                contact_ids.append(int(a))
            except Exception:
                await update.effective_chat.send_message(f"Ignore non-numeric argument: {a}")
    # de-dupe & trim if too many
    contact_ids = sorted(set(contact_ids))
    if not contact_ids:
        await update.effective_chat.send_message("No valid contact IDs provided.")
        return
    if len(contact_ids) > 6:
        await update.effective_chat.send_message(
            "That’s a lot—Telegram limits deep-link length. I’ll include the first 6."
        )
        contact_ids = contact_ids[:6]
    bot_username = (await context.bot.get_me()).username
    link = build_bundle_link(bot_username, contact_ids)
    listed = ", ".join(map(str, contact_ids))
    await update.effective_chat.send_message(
        "Share this link with the runner. When they tap it, they’ll add ALL of these contacts:\n"
        f"IDs: {listed}\n{link}"
    )