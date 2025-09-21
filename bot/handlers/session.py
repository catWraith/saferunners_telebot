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
from bot.utils.time_utils import (
    get_user_tz,
    parse_hhmm,
    local_hhmm_to_future_dt,
    to_utc,
    delay_seconds_from_utc_deadline,
)
from bot.jobs.deadline import deadline_job
from bot.utils.session_utils import format_location_summary


def _session_action_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Complete", callback_data="complete")],
            [
                InlineKeyboardButton("Extend +15 min", callback_data="extend:15"),
                InlineKeyboardButton("Extend +30 min", callback_data="extend:30"),
            ],
            [InlineKeyboardButton("❌ Cancel session", callback_data="cancel")],
        ]
    )


def _format_session_message(session, end_local_dt) -> str:
    loc_summary = format_location_summary(session.get("location"))
    end_str = end_local_dt.strftime("%Y-%m-%d %H:%M (%Z)")
    return (
        f"Session armed.\n{loc_summary}\nPlanned end: {end_str}\n\n"
        "Press <b>Complete</b> when you finish."
    )


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

    await update.effective_chat.send_message(
        _format_session_message(session, end_local_dt),
        reply_markup=_session_action_keyboard(),
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

    if data.startswith("extend:"):
        try:
            minutes = int(data.split(":", 1)[1])
        except Exception:
            await update.effective_chat.send_message("Sorry, I couldn't understand that extension request.")
            return

        session = context.user_data.get(UD_ACTIVE)
        if not session or not session.get("end_dt_utc"):
            await update.effective_chat.send_message("No active session to extend.")
            return

        try:
            current_deadline = datetime.fromisoformat(session["end_dt_utc"])
        except Exception:
            await update.effective_chat.send_message(
                "Sorry, I couldn't parse the existing deadline. Please start a new session with /begin."
            )
            return

        new_deadline_utc = current_deadline + timedelta(minutes=minutes)
        session["end_dt_utc"] = new_deadline_utc.isoformat()
        context.user_data[UD_ACTIVE] = session

        job = context.user_data.get(UD_JOB)
        if job and getattr(job, "data", None) is not None:
            job.data["deadline_iso"] = new_deadline_utc.isoformat()
            job.data["location"] = session.get("location")
            if update.effective_user is not None:
                job.data["owner_id"] = update.effective_user.id

        if job:
            try:
                job.schedule_removal()
            except Exception:
                pass

        if context.job_queue is None:
            await update.effective_chat.send_message(
                "⚠️ Scheduling unavailable (JobQueue missing). Ask the admin to install python-telegram-bot[job-queue]."
            )
            return

        delay = delay_seconds_from_utc_deadline(new_deadline_utc)
        delay = max(delay, 1.0)
        effective_user = update.effective_user
        user_id = effective_user.id if effective_user is not None else None
        chat = update.effective_chat
        new_job = context.job_queue.run_once(
            deadline_job,
            delay,
            chat_id=chat.id if chat else None,
            user_id=user_id,
            name=f"deadline_{user_id}" if user_id is not None else "deadline_unknown",
            data={
                "location": session.get("location"),
                "owner_id": user_id,
                "deadline_iso": new_deadline_utc.isoformat(),
            },
        )
        context.user_data[UD_JOB] = new_job

        tz = get_user_tz(context)
        new_end_local = new_deadline_utc.astimezone(tz)
        await query.edit_message_text(
            _format_session_message(session, new_end_local),
            reply_markup=_session_action_keyboard(),
        )
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
