# Freelancer.com Telegram Bot

یک ربات تلگرام که پروژه‌های جدید Freelancer.com را رصد می‌کند و بر اساس مهارت‌های انتخابی شما، اعلان‌های فارسی ارسال می‌کند.

A Telegram bot that monitors Freelancer.com for new projects and sends Persian-translated notifications based on your chosen skills.

---

## ویژگی‌ها / Features

- **رصد خودکار** — پروژه‌های جدید هر چند دقیقه یک‌بار چک می‌شوند
- **فیلتر مهارت** — هر کاربر مهارت‌های مورد نظرش را انتخاب می‌کند
- **ترجمه فارسی** — توضیحات پروژه به فارسی ترجمه می‌شود
- **بودجه و آمار** — بودجه، میانگین bid و تعداد bid نمایش داده می‌شود
- **فاصله قابل تنظیم** — هر کاربر می‌تواند فاصله بررسی خود را تنظیم کند (۱ تا ۱۴۴۰ دقیقه)
- **چند کاربر** — همه کاربران به‌صورت مستقل پشتیبانی می‌شوند

---

## پیش‌نیازها / Prerequisites

- Python 3.11+
- [Playwright](https://playwright.dev/python/) (Chromium)
- یک Telegram Bot Token از [@BotFather](https://t.me/BotFather)

---

## نصب / Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/freelancer-bot.git
cd freelancer-bot

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browser
playwright install chromium

# 5. Configure environment variables
cp .env.example .env
# Edit .env and set your TELEGRAM_TOKEN
```

---

## پیکربندی / Configuration

فایل `.env` را ویرایش کنید:

```env
TELEGRAM_TOKEN=your_telegram_bot_token_here
DEFAULT_INTERVAL=5   # default polling interval in minutes
```

---

## اجرا / Running

```bash
python main.py
```

---

## دستورات ربات / Bot Commands

| دستور | توضیح |
|-------|-------|
| `/start` | شروع و راهنما |
| `/addskill` | افزودن مهارت از لیست (با جستجوی تعاملی) |
| `/removeskill` | حذف مهارت |
| `/skills` | نمایش مهارت‌های فعلی |
| `/interval <دقیقه>` | تنظیم فاصله بررسی (مثلاً `/interval 10`) |
| `/status` | نمایش وضعیت ربات |

---

## ساختار پروژه / Project Structure

```
freelancer-bot/
├── main.py              # Entry point — starts the bot and scheduler
├── config.py            # Loads environment variables
├── db.py                # SQLite database (users, skills, seen projects)
├── scheduler.py         # Polling loop — checks for new projects per user
├── translator.py        # Persian translation via deep-translator
├── bot/
│   ├── handlers.py      # Telegram command and conversation handlers
│   └── notifications.py # Message formatting with MarkdownV2
└── scraper/
    ├── client.py        # Playwright-based Freelancer.com scraper
    ├── parser.py        # Data models and text cleaning utilities
    └── skill_map.py     # Skill name → Freelancer.com slug mapping
```

---

## نحوه کار / How It Works

1. کاربر با `/addskill` مهارت‌هایش را انتخاب می‌کند (مثلاً Python، React، Machine Learning)
2. ربات هر چند دقیقه (بر اساس interval هر کاربر) صفحه مربوط به آن مهارت در Freelancer.com را اسکن می‌کند
3. پروژه‌های جدید (که قبلاً دیده نشده‌اند) استخراج می‌شوند
4. توضیحات به فارسی ترجمه شده و همراه بودجه و آمار bid به کاربر ارسال می‌شوند

---

## تکنولوژی‌ها / Tech Stack

| ابزار | کاربرد |
|-------|--------|
| `python-telegram-bot` | Telegram Bot API |
| `Playwright` | Headless browser scraping |
| `aiosqlite` | Async SQLite database |
| `APScheduler` / `asyncio` | Polling scheduler |
| `deep-translator` | Google Translate → Persian |
| `python-dotenv` | Environment variable management |

---

## نکات / Notes

- پروژه‌ای که یک‌بار به کاربر نشان داده شده دوباره ارسال نمی‌شود (deduplication با SQLite)
- Playwright در حالت headless اجرا می‌شود و نیازی به نمایشگر ندارد
- برای اجرا روی سرور (مثلاً VPS)، از `--no-sandbox` به‌صورت خودکار استفاده می‌شود

---

## مجوز / License

MIT
