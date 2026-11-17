import os
from starlette.templating import Jinja2Templates
from starlette.requests import Request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

def format_currency_filter(val, lang="ar"):
    try:
        num = float(val)
        formatted = f"{num:,.0f}"
        if lang == "en":
            return f"{formatted} EGP"
        return f"{formatted} ج.م"
    except Exception:
        return str(val)

def format_number_filter(val):
    try:
        num = float(val)
        return f"{num:,.0f}"
    except Exception:
        return str(val)

def country_flag_filter(country):
    c = str(country).lower()
    if "germany" in c or "ألمانيا" in c:
        return "🇩🇪 ألمانيا (Germany)"
    elif "korea" in c or "كوريا" in c:
        return "🇰🇷 كوريا الجنوبية (South Korea)"
    elif "uae" in c or "إمارات" in c or "دبي" in c or "gulf" in c or "خليج" in c:
        return "🇦🇪 الإمارات (Gulf Specs)"
    elif "usa" in c or "أمريكا" in c:
        return "🇺🇸 أمريكا (USA)"
    elif "japan" in c or "اليابان" in c:
        return "🇯🇵 اليابان (Japan)"
    return f"🌐 {country}"

templates.env.filters["currency"] = format_currency_filter
templates.env.filters["number"] = format_number_filter
templates.env.filters["flag"] = country_flag_filter

def render_template(request: Request, name: str, context: dict = None, status_code: int = 200):
    """Clean unified template renderer with explicit keyword arguments."""
    ctx = context or {}
    return templates.TemplateResponse(request=request, name=name, context=ctx, status_code=status_code)
