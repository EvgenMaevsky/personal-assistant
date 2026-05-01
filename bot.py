import logging
from telegram.ext import Application, MessageHandler, filters

import db
import handlers
import scheduler
from config import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ],
)


def main() -> None:
    db.init_db()
    app = Application.builder().token(config.bot_token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handlers.handle_voice))
    scheduler.register_jobs(app)
    logging.info("Bot started. Polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
