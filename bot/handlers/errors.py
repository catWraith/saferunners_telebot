import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    # PTB recommends not raising; just log it
    logger.exception(
        "Unhandled exception while handling update=%r. error=%r",
        update,
        context.error,
    )
    # If you want to tell the user something (optional):
    if isinstance(update, Update) and update.effective_chat:
        try:
            await update.effective_chat.send_message(
                "⚠️ Something went wrong. The admins have been notified."
            )
        except Exception:
            pass
