from scraper.parser import Project


def format_project(project: Project, persian_desc: str) -> str:
    budget = _fmt_budget(project.budget_min, project.budget_max)
    avg = f"${project.avg_bid:,.0f}" if project.avg_bid else "N/A"
    bids = str(project.bid_count) if project.bid_count else "0"

    en_desc = project.description[:600].strip()
    fa_desc = persian_desc[:600].strip() if persian_desc else "ترجمه موجود نیست"

    return (
        f"*پروژه جدید پیدا شد!*\n\n"
        f"*{_esc(project.title)}*\n\n"
        f"💰 بودجه: {budget}\n"
        f"📊 میانگین bid: {avg}\n"
        f"👥 تعداد bid: {bids}\n\n"
        f"*Description \\(EN\\):*\n{_esc(en_desc)}\n\n"
        f"*توضیحات \\(FA\\):*\n{_esc(fa_desc)}\n\n"
        f"[مشاهده پروژه]({project.url})"
    )


def _fmt_budget(b_min: float | None, b_max: float | None) -> str:
    if b_min is None and b_max is None:
        return "نامشخص"
    if b_min == b_max or b_max is None:
        return f"${b_min:,.0f}"
    return f"${b_min:,.0f} – ${b_max:,.0f}"


def _esc(text: str) -> str:
    """Escape Telegram MarkdownV2 special chars."""
    for ch in r"\_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text
