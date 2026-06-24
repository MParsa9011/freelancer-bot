import asyncio
import logging
import signal

from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from config import TELEGRAM_TOKEN
import db
from bot.handlers import (
    cmd_start,
    cmd_removeskill,
    cmd_skills,
    cmd_interval,
    cmd_status,
    callback_remove_skill,
    build_addskill_handler,
)
from scraper.client import close_browser
from scheduler import run_scheduler

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await db.init_db()

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(build_addskill_handler())
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("removeskill", cmd_removeskill))
    app.add_handler(CommandHandler("skills", cmd_skills))
    app.add_handler(CommandHandler("interval", cmd_interval))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CallbackQueryHandler(callback_remove_skill, pattern=r"^rm:"))

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    logger.info("Bot started. Running scheduler...")
    scheduler_task = asyncio.create_task(run_scheduler(app.bot))

    stop_event = asyncio.Event()

    def _handle_signal():
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    await stop_event.wait()

    logger.info("Shutting down...")
    scheduler_task.cancel()
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    await close_browser()


if __name__ == "__main__":
    asyncio.run(main())
