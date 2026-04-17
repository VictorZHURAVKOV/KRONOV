"""Генерация PDF: коммерческое предложение и договор.

Используется WeasyPrint (HTML→PDF). Шаблоны — Jinja2.
Пользователь обещал прислать фирменный шаблон КП — когда пришлёт, меняем
`templates/kp.html` и `contract.html`, сама механика остаётся.

Файлы сохраняются в data/kp/. Сервер раздаёт их по /kp/<filename> — ссылка
уходит клиенту.
"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import KP_DIR, BASE_DIR, ALENA_PHONE, ALENA_NAME, SITE_URL
from db import add_event

TEMPLATES_DIR = BASE_DIR / "prompts"  # шаблоны лежат рядом
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _render(template_name: str, context: dict) -> str:
    tpl = _env.get_template(template_name)
    return tpl.render(**context)


async def generate_kp_pdf(
    session_id: str,
    client_name: str,
    client_city: Optional[str],
    model_article: str,
    model_name: str,
    size: str,
    breakdown: dict,
    total_byn: int,
    roof_type: str = "двускатная",
    stain_type: str = "aquatex",
    delivery_km: float = 0,
    accessories: Optional[list] = None,
    nonstandard_uplift_byn: int = 0,
    notes: Optional[str] = None,
) -> dict:
    """Сформировать PDF коммерческого предложения. Вернуть ссылку."""
    try:
        from weasyprint import HTML  # type: ignore
    except Exception as e:
        return {
            "error": f"WeasyPrint не установлен или нет системных зависимостей: {e}. "
                     f"См. README — нужны pango/cairo."
        }

    filename = f"KP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}.pdf"
    out_path = Path(KP_DIR) / filename

    html = _render("kp_template.html", {
        "date": datetime.now().strftime("%d.%m.%Y"),
        "session_short": session_id[:8],
        "client_name": client_name or "—",
        "client_city": client_city or "—",
        "model_article": model_article,
        "model_name": model_name,
        "size": size,
        "roof_type": roof_type,
        "stain_type": stain_type,
        "delivery_km": delivery_km,
        "accessories": accessories or [],
        "breakdown": breakdown,
        "total_byn": total_byn,
        "nonstandard_uplift_byn": nonstandard_uplift_byn,
        "alena_name": ALENA_NAME,
        "alena_phone": ALENA_PHONE,
        "site_url": SITE_URL,
        "notes": notes or "",
    })

    HTML(string=html, base_url=str(BASE_DIR)).write_pdf(str(out_path))
    url = f"{SITE_URL}/kp/{filename}"

    await add_event(session_id, "kp_sent", {
        "filename": filename,
        "model": model_article,
        "size": size,
        "total_byn": total_byn,
    })

    return {"ok": True, "url": url, "filename": filename, "local_path": str(out_path)}


async def generate_contract_pdf(
    session_id: str,
    client_full_name: str,
    passport_series: str,
    passport_number: str,
    passport_issued_by: str,
    passport_issued_date: str,
    client_address: str,
    client_phone: str,
    delivery_address: str,
    model_article: str,
    model_name: str,
    size: str,
    total_byn: int,
    prepayment_byn: int,
    notes: Optional[str] = None,
) -> dict:
    """Сформировать PDF договора-заявки с данными клиента.

    Электронная подпись не используется — клиент подписывает при встрече
    или по почте. Договор отправляется клиенту для ознакомления.
    """
    try:
        from weasyprint import HTML  # type: ignore
    except Exception as e:
        return {"error": f"WeasyPrint не установлен: {e}"}

    filename = f"DOG-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}.pdf"
    out_path = Path(KP_DIR) / filename

    html = _render("contract_template.html", {
        "date": datetime.now().strftime("%d.%m.%Y"),
        "contract_num": f"КР-{datetime.now().strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}",
        "client_full_name": client_full_name,
        "passport_series": passport_series,
        "passport_number": passport_number,
        "passport_issued_by": passport_issued_by,
        "passport_issued_date": passport_issued_date,
        "client_address": client_address,
        "client_phone": client_phone,
        "delivery_address": delivery_address,
        "model_article": model_article,
        "model_name": model_name,
        "size": size,
        "total_byn": total_byn,
        "prepayment_byn": prepayment_byn,
        "balance_byn": total_byn - prepayment_byn,
        "notes": notes or "",
    })

    HTML(string=html, base_url=str(BASE_DIR)).write_pdf(str(out_path))
    url = f"{SITE_URL}/kp/{filename}"

    await add_event(session_id, "contract_sent", {
        "filename": filename,
        "client": client_full_name,
        "total_byn": total_byn,
    })

    return {"ok": True, "url": url, "filename": filename, "local_path": str(out_path)}
