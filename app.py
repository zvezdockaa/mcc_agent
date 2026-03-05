from flask import Flask, render_template, request, jsonify
import datetime
import os
import random
import time
import re
import requests
from urllib.parse import quote
import socket
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

app = Flask(__name__)

# Конфигурация из переменных окружения
DGIS_API_KEY = os.getenv('DGIS_API_KEY', '')  # Ключ 2GIS
DGIS_API_URL = "https://catalog.api.2gis.com/3.0/items"

# Telegram конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_ADMIN_CHAT_ID', '')

# Flask конфигурация
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')

# Проверка наличия обязательных переменных
if not DGIS_API_KEY:
    print("⚠️ ВНИМАНИЕ: DGIS_API_KEY не настроен! Поиск по 2GIS не будет работать.")

if not TELEGRAM_TOKEN:
    print("⚠️ ВНИМАНИЕ: TELEGRAM_BOT_TOKEN не настроен! Отправка в Telegram не будет работать.")

if not TELEGRAM_CHAT_ID:
    print("⚠️ ВНИМАНИЕ: TELEGRAM_ADMIN_CHAT_ID не настроен! Уведомления админу не будут приходить.")

# Расширенная база MCC-кодов с подробными описаниями для поиска
MCC_DATABASE = [
    # Рестораны и кафе
    {
        "code": "5812",
        "name": "Рестораны",
        "keywords": ["ресторан", "кафе", "кофейня", "столовая", "общепит", "питание", "еда", "обед", "ужин", "меню"],
        "description": "Места общественного питания: рестораны, кафе, кофейни, столовые, закусочные"
    },
    {
        "code": "5812",
        "name": "Кофейни",
        "keywords": ["кофе", "кофейня", "капучино", "латте", "эспрессо", "кофейный", "чай"],
        "description": "Заведения специализирующиеся на продаже кофе и чая, часто с десертами"
    },
    {
        "code": "5814",
        "name": "Рестораны быстрого питания",
        "keywords": ["фастфуд", "макдональдс", "бургер", "пицца", "быстрое питание", "бургерная", "шаурма", "хот-дог",
                     "fast food"],
        "description": "Заведения быстрого питания: бургерные, пиццерии, шаурмичные, точки с едой на вынос"
    },

    # АЗС
    {
        "code": "5541",
        "name": "Автозаправочные станции",
        "keywords": ["азс", "заправка", "бензин", "топливо", "газпромнефть", "лукойл", "shell", "bp", "дт", "дизель"],
        "description": "Автозаправочные станции, продажа бензина, дизельного топлива, газа"
    },

    # Больницы и медицина
    {
        "code": "8062",
        "name": "Больницы",
        "keywords": ["больница", "стационар", "клиника", "лечение", "медицина", "госпиталь", "поликлиника"],
        "description": "Медицинские учреждения с круглосуточным стационаром, больницы, госпитали"
    },
    {
        "code": "8090",
        "name": "Медицинские услуги",
        "keywords": ["медицинский центр", "диагностика", "анализы", "узи", "мрт", "врач", "доктор", "прием врача",
                     "медуслуги"],
        "description": "Платные медицинские услуги, диагностические центры, консультации врачей"
    },
    # Косметика и парфюмерия
    {
        "code": "5977",
        "name": "Косметика и парфюмерия",
        "keywords": [
            "косметика", "парфюмерия", "духи", "помада", "тушь", "тональный крем",
            "уход за кожей", "кремы", "маски для лица", "сыворотка", "лосьон",
            "декоративная косметика", "уходовая косметика", "бьюти", "beauty",
            "макияж", "брови", "ресницы", "ногти", "лак для ногтей",
            "золотое яблоко", "лэтуаль", "рив гош", "иль де ботэ", "sephora",
            "парфюмерный", "косметический", "бьюти-бутик", "бренды косметики",
            "люксовая косметика", "профессиональная косметика", "аптечная косметика",
            "натуральная косметика", "органическая косметика", "эко-косметика"
        ],
        "description": "Магазины косметики и парфюмерии: парфюмерные бутики, сетевые магазины косметики, бьюти-маркеты"
    },
    {
        "code": "5977",
        "name": "Парфюмерные магазины",
        "keywords": [
            "парфюм", "духи", "туалетная вода", "одеколон", "ароматы",
            "селективная парфюмерия", "нишевая парфюмерия", "элитная парфюмерия",
            "пробники духов", "наборы парфюмерии", "подарочные наборы косметики"
        ],
        "description": "Магазины парфюмерии, бутики элитной и нишевой парфюмерии"
    },
    {
        "code": "5977",
        "name": "Бьюти-маркеты",
        "keywords": [
            "бьюти", "beauty", "бьюти-маркет", "бьюти-бутик", "бьюти-пространство",
            "золотое яблоко", "лэтуаль", "рив гош", "иль де ботэ", "подружка",
            "улыбка радуги", "магнит косметик", "sephora", "nyx", "mac cosmetics"
        ],
        "description": "Сетевые бьюти-маркеты и магазины косметики"
    },
    {
        "code": "8021",
        "name": "Стоматологические клиники",
        "keywords": ["стоматология", "зубной", "дантист", "зубы", "лечение зубов", "пломба", "ортодонт", "имплант"],
        "description": "Стоматологические клиники и кабинеты, лечение зубов, протезирование"
    },
    {
        "code": "5912",
        "name": "Аптеки",
        "keywords": ["аптека", "лекарство", "таблетки", "медикаменты", "препараты", "витамины", "здоровье", "фармация",
                     "продажа лекарства", "лекарственные средства"],
        "description": "Аптеки, аптечные пункты, продажа лекарственных препаратов и медицинских изделий"
    },
    {
        "code": "742",
        "name": "Ветеринарные клиники",
        "keywords": ["ветеринар", "ветклиника", "животные", "собака", "кошка", "лечение животных", "ветаптека"],
        "description": "Ветеринарные клиники и аптеки, лечение домашних животных"
    },

    # Магазины одежды
    {
        "code": "5651",
        "name": "Магазины одежды",
        "keywords": ["одежда", "zara", "h&m", "adidas", "nike", "магазин одежды", "бутик", "платье", "рубашка",
                     "брюки"],
        "description": "Магазины одежды, бутики, сетевые магазины одежды"
    },
    {
        "code": "5651",
        "name": "Спортивная одежда",
        "keywords": ["спортивная одежда", "спорттовары", "экипировка", "adidas", "nike", "puma", "спортмастер"],
        "description": "Магазины спортивной одежды и экипировки"
    },
    {
        "code": "5661",
        "name": "Магазины обуви",
        "keywords": ["обувь", "ботинки", "туфли", "кроссовки", "сапоги", "кеды", "обувной"],
        "description": "Магазины обуви, обувные бутики"
    },

    # Продукты
    {
        "code": "5411",
        "name": "Продуктовые магазины",
        "keywords": ["продукты", "магазин продуктов", "гастроном", "кулинария", "еда", "бакалея", "овощи", "фрукты",
                     "мясо", "молоко"],
        "description": "Продуктовые магазины, гастрономы, отделы кулинарии"
    },
    {
        "code": "5411",
        "name": "Супермаркеты",
        "keywords": ["супермаркет", "магнит", "пятерочка", "перекресток", "ашан", "лента", "дика", "гипермаркет",
                     "универсам"],
        "description": "Сетевые супермаркеты и гипермаркеты с широким ассортиментом продуктов"
    },

    # Развлечения - Парки развлечений, океанариумы, зоопарки
    {
        "code": "7996",
        "name": "Парки развлечений",
        "keywords": ["парк развлечений", "аттракционы", "аквапарк", "лунапарк", "диснейленд", "карусели",
                     "американские горки", "колесо обозрения", "детский парк", "развлекательный парк"],
        "description": "Парки развлечений, лунапарки, парки с аттракционами, аквапарки"
    },
    {
        "code": "7996",
        "name": "Аквапарки",
        "keywords": ["аквапарк", "водные горки", "бассейны", "водные аттракционы", "аквазона"],
        "description": "Аквапарки, водные развлекательные комплексы с горками и бассейнами"
    },
    {
        "code": "7996",
        "name": "Зоопарки",
        "keywords": ["зоопарк", "зоосад", "зверинец", "животные", "зоологический парк", "террариум", "экзотариум"],
        "description": "Зоопарки, зоологические парки, места содержания и показа животных"
    },
    {
        "code": "7996",
        "name": "Океанариумы",
        "keywords": ["океанариум", "дельфинарий", "аквариум", "морские животные", "дельфины", "тюлени", "морской музей",
                     "подводный мир"],
        "description": "Океанариумы, дельфинарии, аквариумы с морскими животными и рыбами"
    },
    {
        "code": "7996",
        "name": "Дельфинарии",
        "keywords": ["дельфинарий", "дельфины", "шоу с дельфинами", "плавание с дельфинами", "морские млекопитающие"],
        "description": "Дельфинарии, места проведения шоу с дельфинами и морскими животными"
    },

    # Развлечения - другие
    {
        "code": "7832",
        "name": "Кинотеатры",
        "keywords": ["кино", "кинотеатр", "фильм", "кинозал", "кинопоказ", "премьера"],
        "description": "Кинотеатры, кинозалы, места для просмотра фильмов"
    },
    {
        "code": "7922",
        "name": "Театры",
        "keywords": ["театр", "спектакль", "опера", "балет", "представление", "сцена"],
        "description": "Театры, оперные и балетные театры, драматические театры"
    },
    {
        "code": "7997",
        "name": "Фитнес-клубы",
        "keywords": ["фитнес", "тренажерный зал", "спортзал", "качалка", "тренировки", "йога", "пилатес", "аэробика"],
        "description": "Фитнес-центры, тренажерные залы, студии йоги и групповых занятий"
    },
    {
        "code": "7997",
        "name": "Спортивные клубы",
        "keywords": ["спортклуб", "спортивный комплекс", "бассейн", "теннис", "футбол", "баскетбол", "волейбол"],
        "description": "Спортивные клубы и комплексы, секции, спортивные площадки"
    },

    # Красота и здоровье
    {
        "code": "7230",
        "name": "Парикмахерские",
        "keywords": ["парикмахерская", "стрижка", "прическа", "барбершоп", "мужская стрижка"],
        "description": "Парикмахерские, барбершопы, салоны стрижки"
    },
    {
        "code": "7230",
        "name": "Салоны красоты",
        "keywords": ["салон красоты", "косметология", "маникюр", "педикюр", "ногти", "брови", "ресницы"],
        "description": "Салоны красоты, косметологические кабинеты, ногтевые студии"
    },
    {
        "code": "7298",
        "name": "Спа-салоны",
        "keywords": ["спа", "массаж", "сауна", "баня", "хамам", "релакс", "оздоровление"],
        "description": "Спа-салоны, массажные кабинеты, сауны, бани"
    },

    # Транспорт
    {
        "code": "4121",
        "name": "Такси",
        "keywords": ["такси", "uber", "яндекс такси", "извоз", "перевозки", "пассажирские перевозки"],
        "description": "Службы такси, пассажирские перевозки на легковых автомобилях"
    },
    {
        "code": "4111",
        "name": "Общественный транспорт",
        "keywords": ["метро", "автобус", "трамвай", "троллейбус", "электричка", "проезд", "транспорт"],
        "description": "Общественный транспорт, проездные билеты, транспортные карты"
    },
    {
        "code": "4511",
        "name": "Авиакомпании",
        "keywords": ["авиабилеты", "самолет", "авиаперелеты", "аэрофлот", "победа", "s7", "авиакасса"],
        "description": "Авиакомпании, продажа авиабилетов, авиаперевозки"
    },
    {
        "code": "4112",
        "name": "Железнодорожные перевозки",
        "keywords": ["жд билеты", "поезд", "ржд", "железная дорога", "вокзал", "плацкарт", "купе"],
        "description": "Железнодорожные перевозки, продажа билетов на поезда"
    },

    # Отели
    {
        "code": "7011",
        "name": "Отели",
        "keywords": ["отель", "гостиница", "хостел", "проживание", "номер", "гостиничный комплекс"],
        "description": "Отели, гостиницы, хостелы, места для временного проживания"
    },

    # Образование
    {
        "code": "8211",
        "name": "Школы",
        "keywords": ["школа", "гимназия", "лицей", "образование", "учеба", "ученики"],
        "description": "Общеобразовательные школы, гимназии, лицеи"
    },
    {
        "code": "8220",
        "name": "Высшее образование",
        "keywords": ["университет", "институт", "академия", "вуз", "высшее образование", "студенты"],
        "description": "Высшие учебные заведения, университеты, институты, академии"
    },
    {
        "code": "8299",
        "name": "Образовательные курсы",
        "keywords": ["курсы", "обучение", "тренинг", "семинар", "повышение квалификации", "репетитор"],
        "description": "Образовательные курсы, тренинги, семинары, репетиторство"
    },
    # Магазины тканей и рукоделия
    {
        "code": "5949",
        "name": "Магазины тканей и рукоделия",
        "keywords": [
            "ткани", "магазин тканей", "текстиль", "шитье", "швейная фурнитура",
            "нитки", "пряжа", "выкройки", "пуговицы", "заклепки", "шнурки",
            "кружева", "молнии", "застежки", "тесьма", "подкладочная ткань",
            "отделка для одежды", "атлас", "шелк", "хлопок", "лен", "шерсть",
            "вязание", "рукоделие", "вышивка", "пяльцы", "канва", "мулине",
            "бисер", "бусины", "фурнитура для бижутерии", "леска", "спицы",
            "крючки для вязания", "наборы для шитья", "ножницы", "раскройный нож",
            "сантиметровая лента", "булавки", "иглы", "наперстки", "швейные машины",
            "консультации по шитью", "курсы кройки и шитья", "мастер-классы по шитью"
        ],
        "description": "Магазины тканей, швейной фурнитуры и товаров для рукоделия: ткани, нитки, пряжа, пуговицы, молнии, кружева, а также консультации по шитью"
    },
    {
        "code": "5949",
        "name": "Магазины пряжи и вязания",
        "keywords": [
            "пряжа", "вязание", "спицы", "крючки", "шерсть", "ангора", "мохер",
            "акрил", "меланж", "секционная пряжа", "наборы для вязания",
            "журналы по вязанию", "схемы вязания", "клубок", "моток"
        ],
        "description": "Магазины пряжи и товаров для вязания"
    },
    {
        "code": "5949",
        "name": "Магазины для вышивания",
        "keywords": [
            "вышивка", "мулине", "канва", "пяльцы", "схемы для вышивки",
            "наборы для вышивания", "вышивка крестом", "вышивка гладью",
            "вышивка бисером", "нитки для вышивания", "гобелен", "ришелье"
        ],
        "description": "Магазины товаров для вышивания"
    },

    # Специализированные розничные магазины
    {
        "code": "5999",
        "name": "Специализированные розничные магазины",
        "keywords": [
            "специализированный магазин", "уникальные товары", "сувениры",
            "подарки", "магазин подарков", "хендмейд", "handmade", "магазин сувениров",
            "эзотерика", "магические товары", "амулеты", "талисманы", "обереги",
            "карты таро", "руны", "магические свечи", "благовония", "аромалампы",
            "вечеринки", "товары для праздника", "праздничные украшения",
            "воздушные шары", "пиньяты", "колпаки", "аксессуары для вечеринок",
            "атласы", "географические карты", "путеводители", "карты мира",
            "дистиллированная вода", "льдов", "сухой лед", "питьевая вода",
            "аксессуары для красоты", "профессиональная косметика", "инструменты для макияжа",
            "кисти для макияжа", "спонжи", "щипцы для завивки", "бигуди",
            "магазин приколов", "розыгрыши", "фокусы", "магия", "эксклюзивные товары"
        ],
        "description": "Специализированные розничные магазины с уникальными товарами: сувениры, эзотерика, товары для праздников, карты и атласы, дистиллированная вода, аксессуары для красоты и другие специализированные товары"
    },
    {
        "code": "5999",
        "name": "Магазины эзотерики",
        "keywords": [
            "эзотерика", "магические товары", "амулеты", "талисманы", "обереги",
            "карты таро", "руны", "магические свечи", "благовония", "аромалампы",
            "маятники", "рамки", "оракулы", "книги по эзотерике", "хиромантия",
            "нумерология", "астрология", "фэн-шуй", "камни", "кристаллы", "минералы"
        ],
        "description": "Магазины эзотерических и магических товаров"
    },
    {
        "code": "5999",
        "name": "Магазины товаров для праздника",
        "keywords": [
            "товары для праздника", "праздничные украшения", "воздушные шары",
            "пиньяты", "колпаки", "аксессуары для вечеринок", "день рождения",
            "новый год", "свадьба", "корпоратив", "декор", "гирлянды",
            "праздничная посуда", "свечи для торта", "хлопушки", "конфетти",
            "маскарадные костюмы", "аквагрим", "фотозона", "праздничный декор"
        ],
        "description": "Магазины товаров для праздников и вечеринок"
    },

    # Различные продовольственные магазины
    {
        "code": "5499",
        "name": "Различные продовольственные магазины",
        "keywords": [
            "продукты", "продуктовый магазин", "магазин у дома", "минимаркет",
            "продукты на вынос", "специализированные продукты", "деликатесы",
            "элитные продукты", "деликатесный магазин", "гастроном",
            "диетические продукты", "здоровое питание", "полезные продукты",
            "эко-продукты", "био-продукты", "органические продукты",
            "без глютена", "без лактозы", "веганские продукты", "вегетарианские продукты",
            "сыры", "сырная лавка", "колбасы", "мясная лавка", "домашняя птица",
            "мясные деликатесы", "рыбный магазин", "морепродукты", "свежая рыба",
            "овощной магазин", "фруктовый магазин", "овощи и фрукты", "зелень",
            "фермерские продукты", "фермерский рынок", "рынок выходного дня",
            "кофейня", "кофе с собой", "кофейный бутик", "кофе зерновой",
            "чайный магазин", "чайная лавка", "свежеобжаренный кофе",
            "мороженое", "магазин мороженого", "йогурты", "десерты",
            "полуфабрикаты", "замороженные продукты", "готовая еда", "кулинария",
            "хлебобулочные изделия", "пекарня", "свежая выпечка", "хлеб",
            "кондитерская", "пирожные", "торты", "сладости", "восточные сладости",
            "мед", "варенье", "джемы", "соусы", "маринады", "соленья"
        ],
        "description": "Различные продовольственные магазины: специализированные продуктовые рынки, магазины деликатесов, диетических продуктов, овощные и фруктовые магазины, кофейни, магазины мороженого и полуфабрикатов, небольшие магазины у дома"
    },
    {
        "code": "5499",
        "name": "Магазины деликатесов",
        "keywords": [
            "деликатесы", "элитные продукты", "гастрономия", "фуа-гра",
            "трюфели", "икра", "лосось", "пармезан", "хамон", "прошутто",
            "сырная тарелка", "мясная тарелка", "винные деликатесы",
            "итальянские продукты", "французские продукты", "испанские продукты"
        ],
        "description": "Магазины элитных продуктов и деликатесов"
    },
    {
        "code": "5499",
        "name": "Магазины здорового питания",
        "keywords": [
            "здоровое питание", "диетические продукты", "без глютена",
            "без лактозы", "веганские продукты", "вегетарианские продукты",
            "органические продукты", "эко-продукты", "био-продукты",
            "суперфуды", "чиа", "киноа", "спирулина", "протеиновые батончики",
            "зож", "правильное питание", "пп", "фитнес-питание"
        ],
        "description": "Магазины диетических и здоровых продуктов питания"
    },
    {
        "code": "5499",
        "name": "Фермерские магазины",
        "keywords": [
            "фермерские продукты", "фермерский магазин", "эко-продукты",
            "натуральные продукты", "деревенские продукты", "молоко фермерское",
            "яйца домашние", "мясо фермерское", "овощи с грядки",
            "фрукты сезонные", "зелень свежая", "мед натуральный",
            "сыр домашний", "творог", "сметана", "масло сливочное"
        ],
        "description": "Фермерские магазины и лавки с натуральными продуктами"
    },
    {
        "code": "5499",
        "name": "Овощные и фруктовые магазины",
        "keywords": [
            "овощной магазин", "фруктовый магазин", "овощи и фрукты",
            "зелень", "фруктовая лавка", "овощная лавка", "фреш маркет",
            "сезонные овощи", "сезонные фрукты", "ягоды", "экзотические фрукты",
            "сухофрукты", "орехи", "свежие овощи", "свежие фрукты"
        ],
        "description": "Магазины свежих овощей и фруктов"
    },

    # Другое
    {
        "code": "5995",
        "name": "Зоомагазины",
        "keywords": ["зоомагазин", "зоотовары", "корм для животных", "аксессуары для животных"],
        "description": "Магазины товаров для животных, зоомагазины"
    },
    {
        "code": "5251",
        "name": "Хозяйственные магазины",
        "keywords": ["хозтовары", "хозяйственный магазин", "бытовая химия", "товары для дома"],
        "description": "Магазины хозяйственных товаров, бытовой химии"
    },
    {
        "code": "5712",
        "name": "Магазины мебели",
        "keywords": ["мебель", "мебельный магазин", "шкаф", "кровать", "стол", "стул", "диван"],
        "description": "Магазины мебели, мебельные салоны"
    },
    {
        "code": "5211",
        "name": "Строительные материалы",
        "keywords": ["стройматериалы", "строительный магазин", "инструменты", "ремонт", "стройка"],
        "description": "Магазины строительных материалов, инструментов, товаров для ремонта"
    },
    {
        "code": "5992",
        "name": "Цветочные магазины",
        "keywords": ["цветы", "букет", "цветочный магазин", "флористика", "растения"],
        "description": "Цветочные магазины, салоны флористики"
    },
    {
        "code": "5944",
        "name": "Ювелирные магазины",
        "keywords": ["ювелирный", "золото", "серебро", "украшения", "кольца", "серьги", "бриллианты"],
        "description": "Ювелирные магазины, салоны, продажа украшений"
    },
    {
        "code": "5942",
        "name": "Книжные магазины",
        "keywords": ["книги", "книжный магазин", "литература", "учебники", "бестселлеры"],
        "description": "Книжные магазины, магазины учебной литературы"
    },
    {
        "code": "5921",
        "name": "Алкогольные магазины",
        "keywords": ["алкоголь", "вино", "водка", "пиво", "ликер", "алкомаркет", "красное и белое"],
        "description": "Магазины алкогольной продукции, алкомаркеты"
    },
    {
        "code": "5993",
        "name": "Табачные магазины",
        "keywords": ["табак", "сигареты", "табачный магазин", "вейп", "кальяны"],
        "description": "Табачные магазины, продажа сигарет и табачных изделий"
    },
    {
        "code": "7699",
        "name": "Ремонтные мастерские",
        "keywords": ["ремонт", "мастерская", "починка", "обувь ремонт", "часы ремонт", "техника ремонт"],
        "description": "Ремонтные мастерские, услуги по ремонту различных товаров"
    },
    {
        "code": "2842",
        "name": "Химчистки",
        "keywords": ["химчистка", "чистка одежды", "стирка", "пятна"],
        "description": "Химчистки, услуги по химической чистке одежды"
    }
]


def calculate_similarity(text, keywords):
    """Рассчитывает релевантность текста набору ключевых слов"""
    text_lower = text.lower()
    score = 0
    matches = []

    for keyword in keywords:
        # Ищем точное вхождение слова
        if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            score += 10
            matches.append(keyword)
        # Ищем частичное вхождение
        elif keyword in text_lower:
            score += 5
            matches.append(keyword + "*")
        # Проверяем вхождение частей слова (для русских слов с окончаниями)
        elif len(keyword) > 4 and keyword[:-2] in text_lower:  # отбрасываем окончание
            score += 3
            matches.append(keyword[:-2] + "~")

    return score, matches


def search_2gis(address):
    """
    Двухэтапный поиск организаций по адресу через API 2GIS:
    1. Поиск здания по адресу (type=building)
    2. Поиск организаций внутри здания по building_id (search_type=indoor)
    """
    try:
        # Проверяем, настроен ли ключ
        if DGIS_API_KEY == "ваш_api_ключ_2gis":
            return {
                "error": "API ключ 2GIS не настроен. Пожалуйста, получите ключ на https://dev.2gis.com/ и добавьте его в файл app.py",
                "needs_api_key": True
            }

        print(f"\n=== НАЧАЛО ПОИСКА ПО АДРЕСУ: '{address}' ===\n")

        # ЭТАП 1: Поиск здания по адресу (type=building)
        print("ЭТАП 1: Поиск здания по адресу (type=building)...")

        building_response = requests.get(
            DGIS_API_URL,
            params={
                'q': address,
                'type': 'building',
                'key': DGIS_API_KEY,
                'fields': 'items.address_name,items.building_name,items.full_name,items.id,items.name,items.purpose_name'
            },
            timeout=10,
            headers={'User-Agent': 'MCC-AI-Agent/1.0'}
        )

        print(f"Статус ответа (здания): {building_response.status_code}")

        if building_response.status_code != 200:
            error_msg = f"Ошибка API 2GIS при поиске здания: {building_response.status_code}"
            print(error_msg)
            return {"error": error_msg}

        building_data = building_response.json()

        # Проверяем, есть ли результаты поиска зданий
        if 'result' not in building_data or 'items' not in building_data['result'] or not building_data['result'][
            'items']:
            print("Здания по указанному адресу не найдены")
            return {
                "error": f"По адресу '{address}' не найдено зданий. Проверьте правильность ввода адреса.",
                "results": []
            }

        # Берем первое найденное здание (самое релевантное)
        first_building = building_data['result']['items'][0]
        building_id = first_building.get('id')
        building_name = first_building.get('name', '')
        building_address = first_building.get('address_name', '')
        building_purpose = first_building.get('purpose_name', '')

        print(f"✅ Найдено здание:")
        print(f"   - ID: {building_id}")
        print(f"   - Название: {building_name}")
        print(f"   - Адрес: {building_address}")
        print(f"   - Назначение: {building_purpose}")

        # ЭТАП 2: Поиск организаций внутри здания по building_id (search_type=indoor)
        print("\nЭТАП 2: Поиск организаций внутри здания (search_type=indoor)...")

        org_response = requests.get(
            DGIS_API_URL,
            params={
                'search_type': 'indoor',
                'building_id': building_id,
                'key': DGIS_API_KEY,
                'fields': 'items.point,items.address_name,items.name,items.rubrics,items.external_content',
                'limit': 10
            },
            timeout=10,
            headers={'User-Agent': 'MCC-AI-Agent/1.0'}
        )

        print(f"Статус ответа (организации): {org_response.status_code}")

        if org_response.status_code != 200:
            error_msg = f"Ошибка API 2GIS при поиске организаций: {org_response.status_code}"
            print(error_msg)
            return {
                "building": {
                    "id": building_id,
                    "name": building_name,
                    "address": building_address,
                    "purpose": building_purpose
                },
                "error": error_msg,
                "organizations": []
            }

        org_data = org_response.json()

        # Формируем результат
        result = {
            "building": {
                "id": building_id,
                "name": building_name,
                "address": building_address,
                "purpose": building_purpose
            },
            "organizations": []
        }

        # Парсим организации
        if 'result' in org_data and 'items' in org_data['result']:
            organizations = org_data['result']['items']
            print(f"✅ Найдено организаций внутри здания: {len(organizations)}")

            for org in organizations:
                org_info = {
                    'name': org.get('name', 'Название не указано'),
                    'address': org.get('address_name', building_address),
                    'rubrics': [],
                    'services': []
                }

                # Получаем рубрики (категории)
                if 'rubrics' in org:
                    for rubric in org['rubrics']:
                        if 'name' in rubric:
                            org_info['rubrics'].append(rubric['name'])

                # Получаем услуги из внешнего контента
                if 'external_content' in org:
                    for content in org['external_content']:
                        if content.get('type') == 'services' and 'items' in content:
                            for service in content['items']:
                                if 'name' in service:
                                    org_info['services'].append(service['name'])

                result["organizations"].append(org_info)

            print(f"=== ПОИСК ЗАВЕРШЕН УСПЕШНО, НАЙДЕНО {len(result['organizations'])} ОРГАНИЗАЦИЙ ===\n")
        else:
            print("В здании не найдено организаций")
            result["message"] = "В указанном здании не найдено организаций"

        return result

    except requests.exceptions.Timeout:
        print("Таймаут при запросе к 2GIS API")
        return {"error": "Превышено время ожидания ответа от 2GIS"}
    except requests.exceptions.ConnectionError:
        print("Ошибка соединения с 2GIS API")
        return {"error": "Ошибка соединения с сервером 2GIS"}
    except Exception as e:
        print(f"Исключение при запросе к 2GIS: {str(e)}")
        return {"error": f"Ошибка при запросе к 2GIS: {str(e)}"}


def save_feedback_to_file(name, email, message):
    """Сохраняет обратную связь в файл"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    feedback_entry = f"""
[{timestamp}]
👤 Имя: {name}
📧 Email: {email}
💬 Сообщение: {message}
{'-' * 60}
"""
    try:
        with open('feedback.txt', 'a', encoding='utf-8') as f:
            f.write(feedback_entry)
        print(f"✅ Сообщение сохранено в feedback.txt")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сохранении feedback: {e}")
        return False


def save_unsent_feedback(name, email, message):
    """Сохраняет неотправленные сообщения в отдельный файл"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    feedback_entry = f"""
[{timestamp}] ⚠️ НЕ ОТПРАВЛЕНО В TELEGRAM
👤 Имя: {name}
📧 Email: {email}
💬 Сообщение: {message}
{'-' * 60}
"""
    try:
        with open('unsent_feedback.txt', 'a', encoding='utf-8') as f:
            f.write(feedback_entry)
        print(f"✅ Сообщение сохранено в unsent_feedback.txt")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сохранении: {e}")
        return False


def save_message_for_bot(name, email, message):
    """Сохраняет сообщение в файл для последующей рассылки ботом"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open('telegram_messages.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n[{timestamp}]\nИмя: {name}\nEmail: {email}\nСообщение: {message}\n{'-' * 40}\n")
        print(f"✅ Сообщение сохранено для рассылки")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False


def send_to_telegram_subscribers(name, email, message):
    """
    Отправляет сообщение всем подписчикам бота
    """
    try:
        # Формируем сообщение
        text = f"📬 НОВАЯ ОБРАТНАЯ СВЯЗЬ\n\n👤 Имя: {name}\n📧 Email: {email}\n\n💬 Сообщение:\n{message}"

        # Отправляем админу (для контроля)
        admin_sent = False
        if TELEGRAM_CHAT_ID:
            admin_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            admin_params = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': f"📢 Начинаю рассылку всем подписчикам...\n\n{text[:100]}..."
            }
            requests.get(admin_url, params=admin_params, timeout=5, verify=False)
            admin_sent = True

        # ВАЖНО: Здесь должен быть эндпоинт для бота
        # Но в данной версии рассылку делает сам бот через getUpdates

        # Возвращаем успех
        return True

    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False

def predict_mcc(shop_name, merchant, city, street, house, building, description):
    """
    Функция для определения MCC-кода с поиском по релевантности
    """
    # Добавляем небольшую задержку для анимации
    time.sleep(1.5)

    # Формируем полный адрес
    full_address = f"{city} {street} {house} {building}".strip()

    # Объединяем все поля для поиска
    combined_text = f"{shop_name} {merchant} {full_address} {description}".lower()

    # Оцениваем релевантность для каждой записи в базе
    best_match = None
    best_score = 0
    best_matches = []

    for item in MCC_DATABASE:
        score, matches = calculate_similarity(combined_text, item["keywords"])
        if score > best_score:
            best_score = score
            best_match = item
            best_matches = matches

    # Если нашли совпадение с достаточным баллом
    if best_match and best_score >= 5:
        # Нормализуем уверенность (макс 98%)
        confidence = min(98, 50 + best_score * 2)
        result = {
            "code": best_match["code"],
            "name": best_match["name"],
            "description": best_match["description"],
            "confidence": confidence,
            "found": True,
            "matches": best_matches[:3]
        }
    else:
        # Если ничего не нашли
        result = {
            "code": "????",
            "name": "Специфичная ниша",
            "confidence": 0,
            "found": False,
            "message": "Данная ниша специфичная. Пожалуйста, уточните описание торговой точки, добавьте больше деталей о деятельности.",
            "suggestions": get_suggestions(combined_text)
        }

    # Сохраняем в историю
    save_to_history(shop_name, merchant, full_address, description, result["code"], result["name"])

    return result


def get_suggestions(text):
    """Возвращает подсказки на основе частичных совпадений"""
    suggestions = []
    for item in MCC_DATABASE:
        for keyword in item["keywords"]:
            if keyword in text and item not in suggestions:
                suggestions.append(f"{item['name']} ({item['code']})")
                break
    return suggestions[:3]


def save_to_history(shop_name, merchant, address, description, mcc_code, mcc_name):
    """Сохраняет запрос в историю"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history_entry = f"""
[{timestamp}]
📍 Торговая точка: {shop_name}
👤 Предприниматель: {merchant}
🏠 Адрес: {address}
📝 Описание: {description}
✅ Результат: {mcc_code} - {mcc_name}
{'-' * 60}
"""
    try:
        with open('history.txt', 'a', encoding='utf-8') as f:
            f.write(history_entry)
    except Exception as e:
        print(f"Ошибка при сохранении истории: {e}")


@app.route('/')
def index():
    """Отображает главную страницу"""
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    """Обрабатывает запрос от формы"""
    # Получаем данные из формы
    shop_name = request.form.get('shop_name', '')
    merchant = request.form.get('merchant', '')
    city = request.form.get('city', '')
    street = request.form.get('street', '')
    house = request.form.get('house', '')
    building = request.form.get('building', '')
    description = request.form.get('description', '')

    # Вызываем функцию определения MCC
    result = predict_mcc(shop_name, merchant, city, street, house, building, description)

    return jsonify(result)


@app.route('/search_2gis', methods=['POST'])
def search_2gis_route():
    """Обрабатывает запрос к API 2GIS"""
    data = request.get_json()
    address = data.get('address', '')

    if not address:
        return jsonify({"error": "Адрес не указан"})

    result = search_2gis(address)
    return jsonify(result)


@app.route('/send_feedback', methods=['POST'])
def send_feedback():
    """Обрабатывает отправку обратной связи и сохраняет в Google Sheets"""
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    message = data.get('message', '').strip()

    # Валидация
    if not name:
        return jsonify({"success": False, "error": "Укажите ваше имя"})

    if not email or '@' not in email or '.' not in email:
        return jsonify({"success": False, "error": "Укажите корректный email"})

    if not message or len(message) < 10:
        return jsonify({"success": False, "error": "Сообщение должно содержать минимум 10 символов"})

    # Сохраняем в локальный файл (как резервную копию)
    save_feedback_to_file(name, email, message)

    # Отправляем в Google Sheets
    google_sheets_success = send_to_google_sheets(name, email, message)

    # Отправляем в Telegram (опционально)
    telegram_success = False
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        telegram_success = send_to_telegram_subscribers(name, email, message)

    # Формируем ответ пользователю
    if google_sheets_success:
        return jsonify({
            "success": True,
            "message": "Спасибо! Ваше сообщение сохранено в Google Таблице",
            "details": {
                "google_sheets": True,
                "telegram": telegram_success
            }
        })
    else:
        return jsonify({
            "success": True,
            "message": "Спасибо! Сообщение сохранено локально",
            "details": {
                "google_sheets": False,
                "telegram": telegram_success
            }
        })


def send_to_google_sheets(name, email, message):
    """
    Отправляет данные в Google Sheets через вебхук
    """
    try:
        webhook_url = os.getenv('GOOGLE_SHEETS_WEBHOOK_URL')

        if not webhook_url:
            print("❌ GOOGLE_SHEETS_WEBHOOK_URL не настроен")
            return False

        print(f"📤 Отправка в Google Sheets: {name}, {email}")
        print(f"🔗 URL: {webhook_url}")

        # Данные для отправки
        payload = {
            'name': name,
            'email': email,
            'message': message
        }

        # Отправляем POST запрос
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )

        print(f"📊 Статус ответа: {response.status_code}")
        print(f"📄 Ответ: {response.text[:200]}")

        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    print(f"✅ Данные сохранены в Google Sheets")
                    return True
                else:
                    print(f"❌ Ошибка Google Sheets: {result.get('error')}")
                    return False
            except:
                print(f"❌ Не удалось распарсить ответ")
                return False
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print("❌ Таймаут при отправке в Google Sheets")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Ошибка соединения с Google Sheets")
        return False
    except Exception as e:
        print(f"❌ Неизвестная ошибка: {e}")
        return False
@app.route('/check_telegram', methods=['GET'])
def check_telegram():
    """Проверка доступности Telegram API"""
    results = []

    # Проверка 1: DNS резолв
    try:
        ip = socket.gethostbyname('api.telegram.org')
        results.append({"test": "DNS lookup", "success": True, "ip": ip})
    except Exception as e:
        results.append({"test": "DNS lookup", "success": False, "error": str(e)})

    # Проверка 2: HTTP соединение (без SSL)
    try:
        response = requests.get(
            'http://api.telegram.org',
            timeout=5,
            verify=False
        )
        results.append({
            "test": "HTTP connection",
            "success": True,
            "status": response.status_code
        })
    except Exception as e:
        results.append({
            "test": "HTTP connection",
            "success": False,
            "error": str(e)
        })

    # Проверка 3: HTTPS соединение
    try:
        response = requests.get(
            'https://api.telegram.org',
            timeout=5,
            verify=False
        )
        results.append({
            "test": "HTTPS connection",
            "success": True,
            "status": response.status_code
        })
    except Exception as e:
        results.append({
            "test": "HTTPS connection",
            "success": False,
            "error": str(e)
        })

    # Проверка 4: Валидность токена
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
        response = requests.get(url, timeout=5, verify=False)
        if response.status_code == 200:
            bot_info = response.json()
            results.append({
                "test": "Bot token",
                "success": True,
                "bot_name": bot_info.get('result', {}).get('first_name', 'Unknown')
            })
        else:
            results.append({
                "test": "Bot token",
                "success": False,
                "status": response.status_code,
                "text": response.text
            })
    except Exception as e:
        results.append({
            "test": "Bot token",
            "success": False,
            "error": str(e)
        })

    return jsonify({
        "timestamp": datetime.datetime.now().isoformat(),
        "results": results,
        "telegram_available": any(r.get("success") for r in results if r["test"] == "HTTP connection"),
        "bot_working": any(r.get("success") for r in results if r["test"] == "Bot token")
    })


@app.route('/test_feedback', methods=['GET'])
def test_feedback():
    """Тестовый endpoint для проверки обратной связи"""
    result = send_to_telegram_broadcast(
        "Тестовый пользователь",
        "test@example.com",
        "Это тестовое сообщение для проверки работы Telegram бота"
    )

    return jsonify({
        "success": result,
        "message": "Тестовое сообщение отправлено" if result else "Ошибка отправки"
    })


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("🚀 MCC AI Agent запущен!")
    print(f"📍 Адрес: http://{FLASK_HOST}:{FLASK_PORT}")
    print("=" * 50 + "\n")

    # Отключаем предупреждения о SSL
    requests.packages.urllib3.disable_warnings()

    if os.getenv('FLASK_ENV') == 'development':
        app.run(debug=True, host=FLASK_HOST, port=FLASK_PORT)

# Для продакшена на Render
if __name__ != '__main__':
    # Это нужно, чтобы gunicorn мог найти приложение
    application = app