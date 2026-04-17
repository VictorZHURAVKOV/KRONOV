"""Калькулятор стоимости беседки КРОНОВЪ.

Формула повторяет ту, что в calculator.html на сайте — чтобы клиент видел
то же число и в чате, и в онлайн-калькуляторе. Добавлено правило +20% за
нестандартный размер.
"""
from typing import Literal, Optional

# ==== Ставки (BYN) ====
FRAME_PER_M2 = 430

ROOF_RATES = {
    "none": 0,
    "односкатная": 95,
    "двускатная": 145,
    "шатровая": 175,
}

STAIN_RATES = {
    "none": 0,
    "aquatex": 40,
    "belinka": 115,
}

FOUNDATION_BASE = 800      # базовый выезд за свайный
FOUNDATION_PER_PILE = 220  # цена за одну сваю

DELIVERY_PER_KM = 3        # туда-обратно = 2 × 3 BYN/км

INSTALL_PCT = 0.10  # монтаж = 10% от каркаса

NONSTANDARD_UPLIFT = 0.20  # +20% если размер нестандартный

# Типовые допы (для агента, когда клиент просит что-то конкретное)
ACCESSORIES = {
    "штора_oxford_1.45x2": 57,
    "штора_oxford_1.45x2.5": 94,
    "штора_oxford_1.45x3": 120,
    "штора_пвх_м2": 35,
    "гирлянда_ретро_25": 90,
    "гирлянда_ретро_50_15м": 140,
    "гирлянда_роса_100м": 115,
    "гирлянда_роса_150м": 195,
    "светильник_солнечный_4": 48,
    "светильник_солнечный_8": 76,
    "подушка_45x45": 38,
    "подушка_110x50": 92,
    "плед_200x230": 80,
    "тюль_лён_600x270": 100,
    "кресло_гамак": 240,
    "гамак_деревянная_планка": 108,
    "ростомер_с_гравировкой": 60,
    "табличка_семейная": 80,
}


def _is_nonstandard(length: float, width: float) -> bool:
    """Нестандарт — если хотя бы одна из сторон не целое число метров или не из сетки 2..6."""
    standard = {2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0}
    for side in (length, width):
        if round(side, 2) not in standard:
            return True
    return False


def calculate_price(
    length: float,
    width: float,
    roof: Literal["none", "односкатная", "двускатная", "шатровая"] = "двускатная",
    stain: Literal["none", "aquatex", "belinka"] = "aquatex",
    foundation: bool = True,
    piles: int = 6,
    delivery_km: float = 0,
    install: bool = True,
    accessories: Optional[dict[str, int]] = None,
    nonstandard: Optional[bool] = None,
) -> dict:
    """Рассчитать стоимость беседки под ключ.

    Args:
        length/width: размеры в метрах.
        roof/stain: опции покрытия.
        foundation: делать ли свайный фундамент.
        piles: количество свай (обычно 4-8).
        delivery_km: расстояние от производства до участка (в одну сторону).
        install: включать ли монтаж (10% от каркаса).
        accessories: {key: qty} из ACCESSORIES.
        nonstandard: если указано явно — используем, иначе проверяем сетку.

    Returns:
        dict с полной разбивкой и итогом в BYN.
    """
    if length <= 0 or width <= 0:
        return {"error": "Размеры должны быть положительными"}
    if length > 10 or width > 10:
        return {"error": "Максимальный размер — 10×10 метров. Для больших — Алёна."}

    area = round(length * width, 2)

    # Определяем нестандартность
    if nonstandard is None:
        nonstandard = _is_nonstandard(length, width)

    # --- Компоненты
    frame = area * FRAME_PER_M2
    roof_cost = area * ROOF_RATES.get(roof, 0)
    stain_cost = area * STAIN_RATES.get(stain, 0)
    install_cost = frame * INSTALL_PCT if install else 0
    foundation_cost = (FOUNDATION_BASE + piles * FOUNDATION_PER_PILE) if foundation else 0
    delivery_cost = delivery_km * 2 * DELIVERY_PER_KM

    acc_cost = 0
    acc_lines = []
    if accessories:
        for key, qty in accessories.items():
            price = ACCESSORIES.get(key)
            if price:
                acc_cost += price * qty
                acc_lines.append({"name": key, "qty": qty, "price": price, "sum": price * qty})

    subtotal = frame + roof_cost + stain_cost + install_cost + foundation_cost + delivery_cost + acc_cost

    # Применяем надбавку за нестандарт
    uplift_amount = 0
    if nonstandard:
        uplift_amount = round(subtotal * NONSTANDARD_UPLIFT)

    total = round(subtotal + uplift_amount)

    return {
        "size": f"{length}×{width}",
        "area_m2": area,
        "nonstandard": nonstandard,
        "breakdown": {
            "каркас": round(frame),
            "кровля": round(roof_cost),
            "пропитка": round(stain_cost),
            "монтаж": round(install_cost),
            "фундамент": round(foundation_cost),
            "доставка": round(delivery_cost),
            "допы": round(acc_cost),
        },
        "roof_type": roof,
        "stain_type": stain,
        "delivery_km": delivery_km,
        "accessories": acc_lines,
        "subtotal_byn": round(subtotal),
        "nonstandard_uplift_byn": uplift_amount,
        "total_byn": total,
        "note_for_client": (
            f"Нестандартный размер {length}×{width} — мы применяем +20% на раскрой и отдельные работы. "
            f"Если подойдёт стандартный {round(length)}×{round(width)}, будет без надбавки."
            if nonstandard else None
        ),
    }
