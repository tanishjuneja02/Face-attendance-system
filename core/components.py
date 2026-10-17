"""HTML and CSS building blocks for the home page.

These are plain functions that return strings (no Streamlit import), so they can be
tested. Anything that comes from the database is escaped before going into HTML.
"""
from html import escape

CSS = """
<style>
.fa-hero{background:linear-gradient(135deg,#4f46e5 0%,#0ea5e9 60%,#14b8a6 100%);color:#fff;padding:28px 32px;border-radius:18px;margin-bottom:18px;box-shadow:0 8px 24px rgba(79,70,229,.25);}
.fa-title{font-size:2.2rem;font-weight:800;line-height:1.15;color:#fff;}
.fa-sub{margin-top:6px;font-size:1.05rem;opacity:.92;color:#fff;}
.fa-chip{display:inline-block;margin-top:14px;padding:4px 14px;border-radius:999px;background:rgba(255,255,255,.2);font-size:.85rem;color:#fff;}
.fa-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:18px;}
.fa-stat{border:1px solid rgba(128,128,128,.25);border-radius:14px;padding:14px 18px;background:rgba(128,128,128,.07);}
.fa-stat-v{font-size:1.9rem;font-weight:700;line-height:1.1;}
.fa-stat-l{font-size:.85rem;opacity:.7;margin-top:2px;}
.fa-banner{border-radius:14px;padding:14px 20px;margin:6px 0 14px 0;color:#fff;font-weight:600;font-size:1.05rem;}
.fa-banner small{display:block;font-weight:400;opacity:.92;margin-top:2px;font-size:.88rem;}
.fa-ok{background:linear-gradient(135deg,#059669,#10b981);}
.fa-info{background:linear-gradient(135deg,#2563eb,#38bdf8);}
.fa-warn{background:linear-gradient(135deg,#d97706,#f59e0b);}
.fa-err{background:linear-gradient(135deg,#dc2626,#f43f5e);}
.fa-result{border:1px solid rgba(128,128,128,.25);border-radius:16px;padding:20px 24px;background:rgba(128,128,128,.07);}
.fa-name{font-size:1.7rem;font-weight:800;line-height:1.2;}
.fa-badge{display:inline-block;margin:8px 8px 0 0;padding:3px 12px;border-radius:999px;background:rgba(99,102,241,.18);font-size:.85rem;}
.fa-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:18px;}
.fa-l{font-size:.78rem;opacity:.65;text-transform:uppercase;letter-spacing:.04em;}
.fa-v{font-size:1.1rem;font-weight:600;}
.fa-recent{display:flex;justify-content:space-between;align-items:center;padding:10px 16px;margin-bottom:8px;border:1px solid rgba(128,128,128,.22);border-radius:12px;background:rgba(128,128,128,.05);}
.fa-recent-sub{opacity:.65;font-size:.85rem;}
@media (max-width:700px){.fa-stats,.fa-grid{grid-template-columns:1fr;}.fa-title{font-size:1.7rem;}}
</style>
"""

# Applied on top of the light theme when the sidebar "Dark mode" switch is on.
# Dark mode: the whole page (every widget, dropdown, calendar, chart and table) is
# colour-inverted, then pictures, video and the coloured banners are inverted back
# so they look normal. Needs `base = "light"` in .streamlit/config.toml.
DARK_CSS = """
<style>
html{filter:invert(1) hue-rotate(180deg) brightness(1.15);}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stHeader"]{background:#eef1f6 !important;}
[data-testid="stSidebar"],[data-testid="stSidebar"]>div{background:#e4e8f2 !important;}
img,video,.fa-hero,.fa-banner,.fa-ico{filter:brightness(.87) hue-rotate(180deg) invert(1);}
.fa-ico{display:inline-block;}
/* borders for text boxes and drop-downs (colours are flipped by the filter above) */
[data-testid="stTextInputRootElement"],[data-testid="stNumberInputContainer"],
[data-testid="stTextInput"] div:has(> input),[data-testid="stNumberInput"] div:has(> input),
[data-testid="stDateInput"] div:has(> input),[data-testid="stTextArea"] div:has(> textarea),
[data-testid="stSelectbox"] div:has(> div > [role="combobox"]),
[data-testid="stFileUploaderDropzone"],[data-testid="stCameraInput"]{
    border:1px solid #64748b !important;border-radius:8px !important;}
</style>
"""

NOTICE_KINDS = ("ok", "info", "warn", "err")


def hero(title, subtitle, date_text):
    return (
        '<div class="fa-hero">'
        f'<div class="fa-title">📷 {escape(title)}</div>'
        f'<div class="fa-sub">{escape(subtitle)}</div>'
        f'<span class="fa-chip">📅 {escape(date_text)}</span>'
        "</div>"
    )


def stats_row(stats):
    """``stats`` is a list of (icon, label, value) tuples."""
    cards = "".join(
        f'<div class="fa-stat"><div class="fa-stat-v"><span class="fa-ico">{escape(str(icon))}</span> {escape(str(value))}</div>'
        f'<div class="fa-stat-l">{escape(str(label))}</div></div>'
        for icon, label, value in stats
    )
    return f'<div class="fa-stats">{cards}</div>'


def notice(kind, title, text=""):
    """A coloured banner. kind is one of: ok, info, warn, err."""
    if kind not in NOTICE_KINDS:
        raise ValueError(f"kind must be one of {NOTICE_KINDS}")
    detail = f"<small>{escape(text)}</small>" if text else ""
    return f'<div class="fa-banner fa-{kind}">{escape(title)}{detail}</div>'


def result_card(name, roll_no, class_name, subject, date, time):
    return (
        '<div class="fa-result">'
        f'<div class="fa-name">{escape(name)}</div>'
        f'<span class="fa-badge"><span class="fa-ico">🆔</span> Roll {escape(str(roll_no))}</span>'
        f'<span class="fa-badge"><span class="fa-ico">🏫</span> {escape(class_name)}</span>'
        '<div class="fa-grid">'
        f'<div><div class="fa-l">Subject</div><div class="fa-v">{escape(subject)}</div></div>'
        f'<div><div class="fa-l">Date</div><div class="fa-v">{escape(date)}</div></div>'
        f'<div><div class="fa-l">Time</div><div class="fa-v">{escape(time)}</div></div>'
        "</div></div>"
    )


def recent_list(rows):
    """Rows are dicts with 'name', 'subject' and 'time'. Returns '' when empty."""
    return "".join(
        '<div class="fa-recent">'
        f'<div><b>{escape(r["name"])}</b><div class="fa-recent-sub">{escape(r["subject"])}</div></div>'
        f'<div class="fa-recent-sub"><span class="fa-ico">🕒</span> {escape(r["time"])}</div>'
        "</div>"
        for r in rows
    )
