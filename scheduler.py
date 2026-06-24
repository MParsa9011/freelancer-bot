import asyncio
import logging
from telegram import Bot
from telegram.error import TelegramError

import db
from scraper.client import get_projects, get_project_detail
from bot.notifications import format_project
from translator import translate_to_fa

logger = logging.getLogger(__name__)

# Seconds between polling runs per user (pulled from DB each cycle)
_DEFAULT_POLL_SECONDS = 300


async def poll_once(bot: Bot) -> None:
    """One full poll cycle: check all users and their skills."""
    users = await db.get_all_users()
    for chat_id in users:
        try:
            await _check_user(bot, chat_id)
        except Exception as e:
            logger.error("Error checking user %d: %s", chat_id, e)


async def _check_user(bot: Bot, chat_id: int) -> None:
    skills = await db.get_skills(chat_id)
    if not skills:
        return

    for skill_name, slug in skills:
        logger.info("Checking slug '%s' for user %d", slug, chat_id)
        projects = await get_projects(slug)

        for project in projects:
            if await db.is_seen(chat_id, project.project_id):
                continue

            # Fetch full details if description is short or avg_bid missing
            if len(project.description) < 100 or project.avg_bid is None:
                detail = await get_project_detail(project.url)
                if detail.get("description"):
                    project.description = detail["description"]
                if detail.get("avg_bid") is not None:
                    project.avg_bid = detail["avg_bid"]
                if detail.get("bid_count") is not None and project.bid_count == 0:
                    project.bid_count = detail["bid_count"]

            persian_desc = await asyncio.get_event_loop().run_in_executor(
                None, translate_to_fa, project.description
            )

            message = format_project(project, persian_desc)
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="MarkdownV2",
                    disable_web_page_preview=True,
                )
            except TelegramError as e:
                logger.error("Failed to send message to %d: %s", chat_id, e)

            await db.mark_seen(chat_id, project.project_id)
            await asyncio.sleep(1)  # avoid flooding Telegram


async def run_scheduler(bot: Bot) -> None:
    """Continuous polling loop. Each user's interval is checked each cycle."""
    user_last_poll: dict[int, float] = {}

    while True:
        users = await db.get_all_users()
        now = asyncio.get_event_loop().time()

        for chat_id in users:
            interval_minutes = await db.get_interval(chat_id)
            interval_seconds = interval_minutes * 60
            last = user_last_poll.get(chat_id, 0)

            if now - last >= interval_seconds:
                logger.info("Polling for user %d (interval=%dm)", chat_id, interval_minutes)
                try:
                    await _check_user(bot, chat_id)
                except Exception as e:
                    logger.error("Poll error for user %d: %s", chat_id, e)
                user_last_poll[chat_id] = asyncio.get_event_loop().time()

        await asyncio.sleep(30)  # recheck every 30s which users are due
