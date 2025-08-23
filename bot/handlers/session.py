from datetime import datetime, timedelta
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

from bot.constants import ASK_LOCATION, ASK_TIME, ASK_CUSTOM_TIME, UD_ACTIVE, UD_JOB
from bot.utils.time_utils import get_user_tz, parse_hhmm, local_hhmm_to_future_dt, to_utc, delay_seconds_from_utc_deadline
from bot.jobs.deadline import deadline_job
from bot.utils.session_utils import format_location_summary


def clear_active_session(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.user_data.pop(UD_JOB, None)
    if job:
        try:
            job.schedule_removal()
        except Exception:
            pass
    context.user_data.pop(UD_ACTIVE, None)


async def begin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    clear_active_session(context)
    context.user_data[UD_ACTIVE] = {"location": None, "end_dt_utc": None}

    kb = [[KeyboardButton(text="Send current location 📍", request_location=True)]]
    await update.effective_chat.send_message(
        "Let’s begin. First, share your location (send a GPS pin with the button below), "
        "or type an address/description.",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=True),
    )
    return ASK_LOCATION


async def got_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    session = context.user_data.get(UD_ACTIVE, {})
    if update.message and update.message.location:
        loc = update.message.location
        session["location"] = {"type": "coords", "lat": loc.latitude, "lon": loc.longitude}
    else:
        text = (update.message.text or "").strip()
        if not text:
            await update.effective_chat.send_message("Please send a location pin or type a location.")
            return ASK_LOCATION
        session["location"] = {"type": "text", "text": text}

    context.user_data[UD_ACTIVE] = session
    tz = get_user_tz(context)
    now_local = datetime.now(tz).strftime("%H:%M")

    ikb = InlineKeyboardMarkup([
        [InlineKeyboardButton("+1 min", callback_data="mins:1"),],
        [InlineKeyboardButton("+15 min", callback_data="mins:15"),
         InlineKeyboardButton("+30 min", callback_data="mins:30")],
        [InlineKeyboardButton("+45 min", callback_data="mins:45"),
         InlineKeyboardButton("+60 min", callback_data="mins:60")],
        [InlineKeyboardButton("Custom HH:MM", callback_data="custom")],
    ])
    await update.effective_chat.send_message(
        f"Great. What’s your planned <b>end time</b>? (Local time now: {now_local})",
        reply_markup=ikb,
    )
    await update.effective_chat.send_message("You can also type a location update anytime.", reply_markup=ReplyKeyboardRemove())
    return ASK_TIME


async def time_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "custom":
        await query.edit_message_text("Send the end time in 24h format HH:MM (e.g., 18:45).")
        return ASK_CUSTOM_TIME

    if data.startswith("mins:"):
        try:
            mins = int(data.split(":")[1])
        except Exception:
            await query.edit_message_text("Sorry, something went wrong. Try /begin again.")
            return ConversationHandler.END
        tz = get_user_tz(context)
        end_local = datetime.now(tz) + timedelta(minutes=mins)
        return await confirm_and_schedule(update, context, end_local)

    await query.edit_message_text("Sorry, invalid option.")
    return ConversationHandler.END


async def time_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    txt = (update.message.text or "").strip()
    hhmm = parse_hhmm(txt)
    if not hhmm:
        await update.effective_chat.send_message("Please use HH:MM in 24-hour time (e.g., 07:30 or 19:05).")
        return ASK_CUSTOM_TIME

    h, m = hhmm
    tz = get_user_tz(context)
    end_local = local_hhmm_to_future_dt(h, m, tz)
    return await confirm_and_schedule(update, context, end_local)


async def confirm_and_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE, end_local_dt) -> int:
    session = context.user_data.get(UD_ACTIVE, {})
    end_dt_utc = to_utc(end_local_dt)
    session["end_dt_utc"] = end_dt_utc.isoformat()
    context.user_data[UD_ACTIVE] = session

    ikb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Complete", callback_data="complete")],
        [InlineKeyboardButton("❌ Cancel session", callback_data="cancel")],
    ])

    loc_summary = format_location_summary(session.get("location"))

    tz = get_user_tz(context)
    end_str = end_local_dt.strftime("%Y-%m-%d %H:%M (%Z)")

    await update.effective_chat.send_message(
        f"Session armed.\n{loc_summary}\nPlanned end: {end_str}\n\n"
        "Press <b>Complete</b> when you finish.",
        reply_markup=ikb,
    )

    delay = delay_seconds_from_utc_deadline(end_dt_utc)
    delay = max(delay, 1.0)

    if context.job_queue is None:
        await update.effective_chat.send_message(
            "⚠️ Scheduling unavailable (JobQueue missing). Ask the admin to install "
            "python-telegram-bot[job-queue]. I won’t be able to alert contacts."
        )
        return ConversationHandler.END

    job = context.job_queue.run_once(
        deadline_job,
        delay,
        chat_id=update.effective_chat.id,
        user_id=update.effective_user.id,
        name=f"deadline_{update.effective_user.id}",
        data={
            "location": session.get("location"),
            "owner_id": update.effective_user.id,
            "deadline_iso": end_dt_utc.isoformat(),  
        },
    )
    context.user_data[UD_JOB] = job
    return ConversationHandler.END


async def button_handler(update, context):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data in ("complete", "cancel"):
        job = context.user_data.pop(UD_JOB, None)
        # mark for clarity (not required)
        try:
            if job and job.data is not None:
                job.data["cancelled"] = True
        except Exception:
            pass
        if job:
            try:
                job.schedule_removal()
            except Exception:
                pass
        context.user_data.pop(UD_ACTIVE, None)

        if data == "complete":
            await query.edit_message_text("Nice work! Session marked complete. No alerts will be sent.")
        else:
            await query.edit_message_text("Session cancelled.")
        return


async def free_text_during_session(update, context):
    if UD_ACTIVE not in context.user_data or not context.user_data[UD_ACTIVE]:
        return
    text = (update.message.text or "").strip()
    if text:
        # Update session view (optional)
        context.user_data[UD_ACTIVE]["location"] = {"type": "text", "text": text}
        # Also update the scheduled job payload so the deadline uses latest location
        job = context.user_data.get(UD_JOB)
        if job and job.data is not None:
            job.data["location"] = {"type": "text", "text": text}
        await update.effective_chat.send_message("Location updated.")


async def free_gps_during_session(update, context):
    if UD_ACTIVE not in context.user_data or not context.user_data[UD_ACTIVE]:
        return
    if update.message and update.message.location:
        loc = update.message.location
        coords = {"type": "coords", "lat": loc.latitude, "lon": loc.longitude}
        context.user_data[UD_ACTIVE]["location"] = coords
        job = context.user_data.get(UD_JOB)
        if job and job.data is not None:
            job.data["location"] = coords
        await update.effective_chat.send_message("Location updated.")
