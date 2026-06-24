import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

import db
from scraper.skill_map import SKILL_MAP, resolve_slug

logger = logging.getLogger(__name__)

WAITING_SEARCH = 1
PAGE_SIZE = 8


# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await db.upsert_user(chat_id)
    await update.message.reply_text(
        "سلام! من یه ربات پیگیری پروژه‌های Freelancer.com هستم.\n\n"
        "دستورات:\n"
        "/addskill — افزودن مهارت از لیست\n"
        "/removeskill — حذف مهارت\n"
        "/skills — لیست مهارت‌های فعلی\n"
        "/interval 5 — تنظیم فاصله بررسی (دقیقه)\n"
        "/status — وضعیت بات"
    )


# ── /addskill conversation ────────────────────────────────────────────────────

async def cmd_addskill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await db.upsert_user(update.effective_chat.id)
    await update.message.reply_text(
        "نام مهارت را بنویس تا لیست نشان داده شود:\n"
        "(مثال: python  یا  react  یا  machine)\n\n"
        "/cancel برای انصراف"
    )
    return WAITING_SEARCH


async def search_skill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.message.text.strip().lower()
    matches = [
        (name, slug)
        for name, slug in sorted(SKILL_MAP.items())
        if query in name or query in slug
    ]

    if not matches:
        slug = query.replace(" ", "-")
        keyboard = [
            [InlineKeyboardButton(f"{query} (custom)", callback_data=f"add:{query}:{slug}")],
            [InlineKeyboardButton("انصراف ❌", callback_data="add:cancel")],
        ]
        await update.message.reply_text(
            f"«{query}» در لیست پیش‌فرض نیست.\n"
            "می‌تونی همین را اضافه کنی یا جستجو را تغییر بدی:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return WAITING_SEARCH

    keyboard = _build_skill_keyboard(matches[:PAGE_SIZE], prefix="add")
    keyboard.append([InlineKeyboardButton("انصراف ❌", callback_data="add:cancel")])

    msg = f"نتایج جستجو برای «{query}» ({len(matches)} مورد):"
    if len(matches) > PAGE_SIZE:
        msg += f"\n(فقط {PAGE_SIZE} مورد اول نمایش داده شده — جستجو را دقیق‌تر کن)"

    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    return WAITING_SEARCH


async def callback_add_skill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "add:cancel":
        await query.edit_message_text("عملیات لغو شد.")
        return ConversationHandler.END

    _, name, slug = query.data.split(":", 2)
    chat_id = query.message.chat_id

    inserted = await db.add_skill(chat_id, name, slug)
    if inserted:
        await query.edit_message_text(f"مهارت «{name}» با موفقیت اضافه شد.")
    else:
        await query.edit_message_text(f"مهارت «{name}» قبلاً در لیست شما بود.")

    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("عملیات لغو شد.")
    return ConversationHandler.END


def build_addskill_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("addskill", cmd_addskill)],
        states={
            WAITING_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_skill),
                CallbackQueryHandler(callback_add_skill, pattern=r"^add:"),
            ]
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        per_message=False,
    )


# ── /removeskill ──────────────────────────────────────────────────────────────

async def cmd_removeskill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    skills = await db.get_skills(chat_id)

    if not skills:
        await update.message.reply_text("لیست مهارت‌های شما خالی است.")
        return

    keyboard = _build_skill_keyboard(skills, prefix="rm")
    keyboard.append([InlineKeyboardButton("انصراف ❌", callback_data="rm:cancel")])
    await update.message.reply_text(
        "کدام مهارت را حذف کنم؟",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def callback_remove_skill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "rm:cancel":
        await query.edit_message_text("عملیات لغو شد.")
        return

    _, name, slug = query.data.split(":", 2)
    chat_id = query.message.chat_id

    deleted = await db.remove_skill(chat_id, name)
    if deleted:
        await query.edit_message_text(f"مهارت «{name}» حذف شد.")
    else:
        await query.edit_message_text(f"مهارت «{name}» پیدا نشد.")


# ── /skills ───────────────────────────────────────────────────────────────────

async def cmd_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    skills = await db.get_skills(chat_id)

    if not skills:
        await update.message.reply_text(
            "هیچ مهارتی ثبت نشده. از /addskill استفاده کن."
        )
        return

    lines = [f"• {name}" for name, _ in skills]
    await update.message.reply_text("مهارت‌های فعلی:\n" + "\n".join(lines))


# ── /interval ─────────────────────────────────────────────────────────────────

async def cmd_interval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("استفاده: /interval عدد_دقیقه\nمثال: /interval 5")
        return

    minutes = int(context.args[0])
    if minutes < 1 or minutes > 1440:
        await update.message.reply_text("فاصله باید بین ۱ تا ۱۴۴۰ دقیقه باشد.")
        return

    await db.upsert_user(chat_id, interval=minutes)
    await update.message.reply_text(f"فاصله بررسی به {minutes} دقیقه تنظیم شد.")


# ── /status ───────────────────────────────────────────────────────────────────

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    skills = await db.get_skills(chat_id)
    interval = await db.get_interval(chat_id)

    await update.message.reply_text(
        f"وضعیت بات:\n"
        f"• مهارت‌ها: {len(skills)} عدد\n"
        f"• فاصله بررسی: هر {interval} دقیقه\n"
        f"• وضعیت: فعال"
    )


# ── helpers ───────────────────────────────────────────────────────────────────

def _build_skill_keyboard(
    skills: list[tuple[str, str]], prefix: str
) -> list[list[InlineKeyboardButton]]:
    """Two columns of skill buttons."""
    buttons = [
        InlineKeyboardButton(name.title(), callback_data=f"{prefix}:{name}:{slug}")
        for name, slug in skills
    ]
    # Pair into rows of 2
    return [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
