"""Каталог моделей беседок КРОНОВЪ.

Единый источник правды — здесь. На сайте карточки живут отдельно,
но агент обращается сюда, чтобы не дублировать описания в промпте.
"""
from dataclasses import dataclass
from typing import Literal, Optional

Style = Literal["классика", "современный", "брутальный", "универсальный", "открытый", "камерный"]


@dataclass
class Model:
    article: str
    name: str
    short: str
    full: str
    style: Style
    roof_type: str
    open_sides: bool
    min_area_m2: float
    typical_area_m2: float
    url_slug: str
    tags: list[str]
    start_price_byn: int = 0            # стартовая цена в BYN (регламент v1.0)
    capacity: str = ""                  # «8–12 чел.», из регламента 1.1


CATALOG: dict[str, Model] = {
    "КР-001": Model(
        article="КР-001",
        name="Резиденция",
        short="Флагман. Шатровая крыша, вертикальные рейки, солидные нижние панели.",
        full=(
            "Представительная беседка премиум-класса. Шатровая крыша, "
            "вертикальные рейки по периметру, солидные нижние панели придают "
            "закрытый, статусный вид. Хорошо смотрится рядом с большим домом."
        ),
        style="классика",
        roof_type="шатровая",
        open_sides=False,
        min_area_m2=9,
        typical_area_m2=16,
        url_slug="kr-001",
        tags=["статус", "премиум", "закрытая", "флагман", "семейная"],
        start_price_byn=4900,
        capacity="8–12 чел.",
    ),
    "КР-002": Model(
        article="КР-002",
        name="Эстетъ",
        short="Открытая квадратная, чайная, элегантная, без нижних панелей.",
        full=(
            "Классическая открытая беседка с рейками по всем сторонам. Нет "
            "нижних глухих панелей — лёгкая, воздушная. Хороша для чаепитий и "
            "семейных посиделок на свежем воздухе."
        ),
        style="классика",
        roof_type="шатровая",
        open_sides=True,
        min_area_m2=6,
        typical_area_m2=12,
        url_slug="kr-002",
        tags=["открытая", "чайная", "семейная", "лёгкая", "архитектурный акцент"],
        start_price_byn=5200,
        capacity="6–8 чел.",
    ),
    "КР-003": Model(
        article="КР-003",
        name="Патриархъ",
        short="Современная плоская кровля, серый каркас, горизонтальные рейки.",
        full=(
            "Современный минималистичный силуэт. Плоская кровля, серый каркас, "
            "горизонтальные рейки. Смотрится как архитектурный объект, не "
            "традиционная беседка."
        ),
        style="современный",
        roof_type="плоская",
        open_sides=True,
        min_area_m2=9,
        typical_area_m2=12,
        url_slug="kr-003",
        tags=["минимализм", "современный", "архитектурный", "большая", "праздничная"],
        start_price_byn=6800,
        capacity="12–20 чел.",
    ),
    "КР-004": Model(
        article="КР-004",
        name="Привилегия",
        short="Белый каркас, Х-ограждения, пергола с качелями. Комплекс отдыха.",
        full=(
            "Комплекс: беседка + пристроенная пергола с качелями. Белый каркас, "
            "декоративные X-образные ограждения. Для тех, кто хочет место "
            "«всё в одном»."
        ),
        style="универсальный",
        roof_type="скатная",
        open_sides=True,
        min_area_m2=15,
        typical_area_m2=24,
        url_slug="kr-004",
        tags=["комплекс", "пергола", "качели", "большая", "премиум", "трёхсезонная"],
        start_price_byn=7500,
        capacity="6–10 чел.",
    ),
    "КР-005": Model(
        article="КР-005",
        name="Встреча",
        short="Классическая, сбалансированная, универсальная.",
        full=(
            "Сбалансированная универсальная модель. Хороший старт если клиент "
            "не определился со стилем. Подходит практически любому участку."
        ),
        style="универсальный",
        roof_type="шатровая",
        open_sides=True,
        min_area_m2=9,
        typical_area_m2=12,
        url_slug="kr-005",
        tags=["универсальная", "дефолт", "сбалансированная", "камерная", "для пары"],
        start_price_byn=3200,
        capacity="2–4 чел.",
    ),
    "КР-006": Model(
        article="КР-006",
        name="Шатёръ",
        short="Квадрат 4 стороны, шатровая крыша 4 ската, арочные балки, ромбы-решётки.",
        full=(
            "Квадратное основание с четырьмя сторонами. Шатровая крыша с "
            "четырьмя скатами. В проёмах арочные балки, по периметру "
            "ромбовидные решётчатые панели. Это НЕ «ротонда» и НЕ восемь граней."
        ),
        style="классика",
        roof_type="шатровая 4 ската",
        open_sides=True,
        min_area_m2=9,
        typical_area_m2=16,
        url_slug="kr-006",
        tags=["классика", "романтика", "ажурная", "усадебная"],
        start_price_byn=5600,
        capacity="6–8 чел.",
    ),
    "КР-007": Model(
        article="КР-007",
        name="Бельведеръ",
        short="Массивный брус, двускатная крыша, фахверковый стиль, открытый.",
        full=(
            "Брутальная открытая беседка на массивном брусе. Двускатная крыша, "
            "фахверковый характер. Для мужского загородного стиля — мангал, "
            "баня, честная древесина."
        ),
        style="брутальный",
        roof_type="двускатная",
        open_sides=True,
        min_area_m2=12,
        typical_area_m2=20,
        url_slug="kr-007",
        tags=["брус", "брутальный", "фахверк", "мангальная"],
        start_price_byn=5400,
        capacity="6–10 чел.",
    ),
    "КР-008": Model(
        article="КР-008",
        name="Дворъ",
        short="Тёмное дерево, шатровая крыша с перголой, открытые стороны.",
        full=(
            "Тёмное дерево, шатровая крыша с пристроенной перголой, открытые "
            "стороны, низкие ограждения. Создаёт «дворовую» атмосферу для "
            "компании друзей и мангальных вечеров."
        ),
        style="брутальный",
        roof_type="шатровая+пергола",
        open_sides=True,
        min_area_m2=12,
        typical_area_m2=20,
        url_slug="kr-008",
        tags=["тёмная", "мангальная", "компания", "вечера", "мужская"],
        start_price_byn=4400,
        capacity="8–12 чел.",
    ),
    "КР-009": Model(
        article="КР-009",
        name="Павильонъ",
        short="Полностью открытый, без стен, мощные стойки, только крыша и платформа.",
        full=(
            "Максимально открытая конструкция. Нет стен и реек — только мощные "
            "стойки, крыша и платформа. Для больших участков, когда важен "
            "простор."
        ),
        style="открытый",
        roof_type="шатровая",
        open_sides=True,
        min_area_m2=12,
        typical_area_m2=20,
        url_slug="kr-009",
        tags=["максимум", "открытая", "простор", "платформа", "без стен"],
        start_price_byn=4200,
        capacity="6–8 чел.",
    ),
    "КР-010": Model(
        article="КР-010",
        name="Приютъ",
        short="Компактная, вертикальные рейки-ширмы, приватная, камерная.",
        full=(
            "Компактная беседка для маленьких участков. Вертикальные рейки "
            "работают как ширмы — создают приватность, закрывают от соседских "
            "взглядов. Камерное уединённое место для интровертов, "
            "читателей, работающих удалённо. Тёплая и камерная."
        ),
        style="камерный",
        roof_type="шатровая",
        open_sides=False,
        min_area_m2=4,
        typical_area_m2=6,
        url_slug="kr-010",
        tags=["компактная", "приватная", "малый участок", "уединение"],
        start_price_byn=3800,
        capacity="2–3 чел.",
    ),
    "КР-011": Model(
        article="КР-011",
        name="Классика",
        short="Универсальная, быстрая в производстве. Классический силуэт.",
        full=(
            "Сбалансированная классическая модель. Универсальный силуэт, "
            "быстрая в производстве. Хороший выбор без экспериментов."
        ),
        style="классика",
        roof_type="шатровая",
        open_sides=True,
        min_area_m2=9,
        typical_area_m2=12,
        url_slug="kr-011",
        tags=["классика", "универсальная", "быстрая"],
        start_price_byn=3600,
        capacity="6–8 чел.",
    ),
    "КР-012": Model(
        article="КР-012",
        name="Садовникъ",
        short="Бюджетная, простая, базовая. Та же технология, минимум изысков.",
        full=(
            "Бюджетная базовая модель. Та же технология производства — массив "
            "сушки 12%, пропитка в 3 слоя — но без декоративных деталей и "
            "сложной геометрии. Идеально когда важно качество, но ограничен бюджет."
        ),
        style="универсальный",
        roof_type="шатровая",
        open_sides=True,
        min_area_m2=6,
        typical_area_m2=9,
        url_slug="kr-012",
        tags=["бюджетная", "базовая", "садовая", "простая"],
        start_price_byn=2800,
        capacity="4–6 чел.",
    ),
    "КР-013": Model(
        article="КР-013",
        name="Веранда",
        short="Пристройка к дому. Общая стена с домом, прямой выход.",
        full=(
            "Беседка-пристройка к дому: одна стена общая с домом, прямой выход "
            "с террасы или крыльца. Для тех кто хочет продолжение жилого "
            "пространства, а не отдельный павильон."
        ),
        style="универсальный",
        roof_type="односкатная",
        open_sides=True,
        min_area_m2=9,
        typical_area_m2=15,
        url_slug="kr-013",
        tags=["веранда", "пристройка", "к дому"],
        start_price_byn=4100,
        capacity="6–10 чел.",
    ),
    "КР-014": Model(
        article="КР-014",
        name="Набережная",
        short="У воды, низкий силуэт. Для пруда, бассейна, реки.",
        full=(
            "Модель для участков у воды — пруд, бассейн, берег реки или озера. "
            "Низкий силуэт, открытая конструкция, отсутствие лишних перегородок. "
            "Акцент на виде на воду."
        ),
        style="открытый",
        roof_type="односкатная",
        open_sides=True,
        min_area_m2=6,
        typical_area_m2=10,
        url_slug="kr-014",
        tags=["вода", "пруд", "бассейн", "низкий силуэт"],
        start_price_byn=4600,
        capacity="4–6 чел.",
    ),
    "КР-015": Model(
        article="КР-015",
        name="Охотникъ",
        short="Лесная изба, очаг, массив, атмосфера охотничьего домика.",
        full=(
            "Брутальная модель в стиле охотничьего домика — массивный брус, "
            "стационарный очаг/мангал, лесная эстетика. Для больших участков "
            "с деревьями, для мужских компаний и семейных застолий."
        ),
        style="брутальный",
        roof_type="двускатная",
        open_sides=False,
        min_area_m2=12,
        typical_area_m2=25,
        url_slug="kr-015",
        tags=["лес", "охота", "очаг", "изба", "массив", "мангал"],
        start_price_byn=5100,
        capacity="8–12 чел.",
    ),
}


def get_model_info(article: str) -> dict:
    """Полная информация по модели."""
    article = article.upper().strip()
    m = CATALOG.get(article)
    if not m:
        return {"error": f"Модель {article} не найдена. Доступны: {', '.join(CATALOG.keys())}"}
    return {
        "article": m.article,
        "name": m.name,
        "short": m.short,
        "full": m.full,
        "style": m.style,
        "roof_type": m.roof_type,
        "open_sides": m.open_sides,
        "typical_area_m2": m.typical_area_m2,
        "min_area_m2": m.min_area_m2,
        "url": f"/gazebo/{m.url_slug}.html",
        "tags": m.tags,
        "start_price_byn": m.start_price_byn,
        "capacity": m.capacity,
    }


def suggest_model(
    for_what: Optional[str] = None,
    style: Optional[str] = None,
    size_hint: Optional[str] = None,
    budget_byn: Optional[float] = None,
) -> dict:
    """Подсказывает 1-2 модели под портрет клиента.

    Простая эвристика — основное решение оставляем за агентом, у него больше
    контекста из диалога.
    """
    candidates = list(CATALOG.values())

    if style:
        s = style.lower()
        if "соврем" in s or "минимал" in s or "архитектур" in s:
            candidates = [m for m in candidates if m.style == "современный"]
        elif "брутал" in s or "мужск" in s or "фахверк" in s:
            candidates = [m for m in candidates if m.style == "брутальный"]
        elif "классик" in s or "традицион" in s:
            candidates = [m for m in candidates if m.style == "классика"]

    if for_what:
        f = for_what.lower()
        if "мангал" in f or "компан" in f or "друз" in f:
            candidates = [m for m in candidates if "мангал" in m.tags or "компания" in m.tags or "вечера" in m.tags] or candidates
        elif "чай" in f or "семь" in f or "дети" in f:
            candidates = [m for m in candidates if "семейная" in m.tags or "чайная" in m.tags] or candidates
        elif "уединен" in f or "двое" in f or "малень" in f:
            candidates = [m for m in candidates if "приватная" in m.tags or "малый участок" in m.tags] or candidates

    if size_hint:
        if "малень" in size_hint.lower() or "2x2" in size_hint or "2×2" in size_hint:
            candidates = [m for m in candidates if m.min_area_m2 <= 6] or candidates
        elif "больш" in size_hint.lower() or "5x6" in size_hint or "5×6" in size_hint:
            candidates = [m for m in candidates if m.typical_area_m2 >= 16] or candidates

    # Максимум 2 варианта, обрежем
    top = candidates[:2] if candidates else list(CATALOG.values())[:2]

    return {
        "suggestions": [
            {
                "article": m.article,
                "name": m.name,
                "why": m.short,
                "url": f"/gazebo/{m.url_slug}.html",
            }
            for m in top
        ]
    }
