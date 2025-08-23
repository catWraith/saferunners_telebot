import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    PicklePersistence,
    filters,
)

from bot.config import TELEGRAM_TOKEN, PERSISTENCE_FILE
from bot.constants import ASK_LOCATION, ASK_TIME, ASK_CUSTOM_TIME
from bot.handlers.start import (
    start,
    tz_cmd,
    link_cmd,
    contacts_cmd,
    stopalerts_cmd,
    start_param_entry,
)
from bot.handlers.session import (
    begin_cmd,
    got_location,
    time_buttons,
    time_custom,
    button_handler,
    free_gps_during_session,
    free_text_during_session,
)


def build_app() -> Application:
    persistence = PicklePersistence(filepath=PERSISTENCE_FILE)

    app = Application.builder().token(TELEGRAM_TOKEN).persistence(persistence).build()

    # Deep-link /start with parameter *before* bare /start so it can catch the param variant
    app.add_handler(
        MessageHandler(
        filters.Regex(r"^/start\s+\S+"),  # only matches when a param exists
        start_param_entry,
        block=False,  # don't block other handlers
        )
    )
    # app.add_handler(MessageHandler(filters.Regex(r"^/start(\s+.+)?$"), start_param_entry))
    app.add_handler(CommandHandler("start", start))

    # Core commands
    app.add_handler(CommandHandler("tz", tz_cmd))
    app.add_handler(CommandHandler("link", link_cmd))
    app.add_handler(CommandHandler("contacts", contacts_cmd))
    app.add_handler(CommandHandler("stopalerts", stopalerts_cmd))

    # Exercise flow
    conv = ConversationHandler(
        entry_points=[CommandHandler("begin", begin_cmd)],
        states={
            ASK_LOCATION: [
                MessageHandler(filters.LOCATION, got_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_location),
            ],
            ASK_TIME: [
                CallbackQueryHandler(time_buttons),
            ],
            ASK_CUSTOM_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, time_custom),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(button_handler, pattern=r"^(complete|cancel)$"),
        ],
        name="exercise_flow",
        persistent=True,
    )
    app.add_handler(conv)

    # Allow completion/cancel outside the conv
    app.add_handler(CallbackQueryHandler(button_handler, pattern=r"^(complete|cancel)$"))

    # Mid-session location updates
    app.add_handler(MessageHandler(filters.LOCATION, free_gps_during_session))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_text_during_session))

    return app


def main():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.INFO,
    )
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "PUT-YOUR-TOKEN-HERE":
        raise SystemExit(
            "Missing bot token.\n"
            "Set BOT_TOKEN in your environment or .env file (or TELEGRAM_TOKEN for backward-compat).\n"
            "Example .env:\n"
            "  BOT_TOKEN=123456:ABC-DEF...\n"
        )
    app = build_app()

    # Guard: make sure JobQueue exists (installed with the extra)
    if app.job_queue is None:
        raise SystemExit(
            "JobQueue is not available. Install with:\n"
            '  pip install "python-telegram-bot[job-queue]==21.6"\n'
        )

    app.run_polling()


if __name__ == "__main__":
    main()
