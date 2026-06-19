import asyncio
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_NAME = os.getenv("BOT_NAME", "MD STORE Global")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@bot_MD_global")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/MD_WEBSITE")
WEB_APP_URL = os.getenv("WEB_APP_URL", "https://mdgiftshop-94hvjt93.manus.space/")
WELCOME_PHOTO_PATH = os.getenv("WELCOME_PHOTO_PATH", "photo_2026-06-13_18-11-52.jpg")
BYBIT_ID = os.getenv("BYBIT_ID", "524739312")
BINANCE_ID = os.getenv("BINANCE_ID", "1254699995")
BINANCE_NOTE = os.getenv("BINANCE_NOTE", "E7988E77-166F-4C84-A")
USDT_BEP20_ADDRESS = os.getenv("USDT_BEP20_ADDRESS", "0xA2E0c2eC432953Dd2F832488a1EC061e6e761361")
MIN_ORDER = float(os.getenv("MIN_ORDER_USDT", "50"))

DB_PATH_RAW = os.getenv("DATABASE_PATH", "md_store_bot.db")
DB = str(Path(DB_PATH_RAW) if Path(DB_PATH_RAW).is_absolute() else BASE_DIR / DB_PATH_RAW)
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "7504221023").replace(" ", "").split(",") if x.isdigit()}

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing in .env or Railway Variables")

PRODUCTS_PATH = BASE_DIR / "products.json"
PRODUCTS = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))

session = AiohttpSession()
bot = Bot(BOT_TOKEN, session=session)
dp = Dispatcher()

# Simple in-memory states for quantity purchase and top-up amount entry.
PENDING_QUANTITY: Dict[int, Dict[str, Any]] = {}
PENDING_TOPUP: Dict[int, Dict[str, Any]] = {}

LANGS = {"ar": "العربية", "en": "English", "ru": "Русский"}

# Custom emoji IDs used in Telegram colored buttons.
# These IDs were provided from Telegram RawDataBot/custom emoji entities.
CUSTOM_EMOJI = {
    "shop": "5309801015015405183",
    "topup": "5310177404474390190",
    "balance": "5276137490846075469",
    "cart_orders": "5443143274061642333",
    "profile": "5242442819573927209",
    "support": "5440411975509096877",
    "channel": "5364125616801073577",
    "razer": "5262644026451960385",
    "pubg_uc": "5314544952422704045",
    "steam": "5318801707394695066",
    "playstation": "5363934885893389858",
    "roblox": "5388921730016240894",
    "itunes": "5332512686112520612",
}

# Hide products that should no longer appear in the bot.
# iTunes Gift Cards remain available; only iTunes Accounts are hidden.
HIDDEN_PRODUCT_KEYWORDS = ("yalla", "ludo", "itunes account", "itunes accounts")

T = {
    "choose_lang": {
        "ar": "اختر اللغة:",
        "en": "Choose language:",
        "ru": "Выберите язык:",
    },
    "welcome": {
        "ar": "مرحبا بك في MD STORE\nمتجر البطاقات الرقمية وشحن الالعاب.\n\nنحن نوفر بطاقات رقمية وشحن العاب للتجار والعملاء.\nللكميات الكبيرة والتعاون طويل المدى تواصل مع الدعم.\n\nاختر من القائمة:",
        "en": "Welcome to MD STORE\nDigital gift card marketplace.\n\nMD STORE supplies digital cards and game top-ups for traders and resellers.\nFor large quantities and long-term cooperation, contact support.\n\nChoose from the menu:",
        "ru": "Добро пожаловать в MD STORE\nМаркетплейс цифровых подарочных карт.\n\nMD STORE поставляет цифровые карты и пополнения игр для клиентов и реселлеров.\nДля крупных заказов и долгосрочного сотрудничества свяжитесь с поддержкой.\n\nВыберите пункт меню:",
    },
    "shop": {"ar": "SHOP", "en": "SHOP", "ru": "SHOP"},
    "products": {"ar": "🛒 Our Products", "en": "🛒 Our Products", "ru": "🛒 Our Products"},
    "special_offers": {"ar": "🎁 العروض", "en": "🎁 Special Offers", "ru": "🎁 Акции"},
    "best_sellers": {"ar": "⭐ الاكثر مبيعا", "en": "⭐ Best Sellers", "ru": "⭐ Хиты продаж"},
    "reviews": {"ar": "المراجعات", "en": "Reviews", "ru": "Отзывы"},
    "profile": {"ar": "الحساب", "en": "Profile", "ru": "Профиль"},
    "coupons": {"ar": "Coupons", "en": "Coupons", "ru": "Coupons"},
    "wholesale": {"ar": "Wholesale Prices", "en": "Wholesale Prices", "ru": "Wholesale Prices"},
    "topup": {"ar": "شحن الرصيد", "en": "Top Up Balance", "ru": "Пополнить баланс"},
    "balance": {"ar": "الرصيد", "en": "Balance", "ru": "Баланс"},
    "cart": {"ar": "السلة", "en": "Cart", "ru": "Корзина"},
    "favorites": {"ar": "❤️ المفضلة", "en": "❤️ Favorites", "ru": "❤️ Избранное"},
    "orders": {"ar": "طلباتي", "en": "My Orders", "ru": "Мои заказы"},
    "latest": {"ar": "آخر عمليات الشراء", "en": "Latest Purchases", "ru": "Последние покупки"},
    "support": {"ar": "الدعم", "en": "Support", "ru": "Поддержка"},
    "faq": {"ar": "الأسئلة الشائعة", "en": "FAQ", "ru": "FAQ"},
    "referrals": {"ar": "👥 الاحالات", "en": "👥 Referrals", "ru": "👥 Рефералы"},
    "copy_usdt": {"ar": "نسخ عنوان USDT", "en": "Copy USDT Address", "ru": "Скопировать USDT"},
    "channel": {"ar": "القناة الرسمية", "en": "Official Channel", "ru": "Официальный канал"},
    "language": {"ar": "🌍 اللغة", "en": "🌍 Language", "ru": "🌍 Язык"},
    "back": {"ar": "رجوع", "en": "Back", "ru": "Назад"},
    "main": {"ar": "القائمة الرئيسية", "en": "Main Menu", "ru": "Главное меню"},
    "category_text": {"ar": "اختر المنتج:", "en": "Choose product:", "ru": "Выберите товар:"},
    "wallet": {
        "ar": "رصيدك الحالي: {balance:.2f} USDT",
        "en": "Your balance: {balance:.2f} USDT",
        "ru": "Ваш баланс: {balance:.2f} USDT",
    },
    "need_balance": {
        "ar": "رصيدك غير كافي لإجراء عمليات الشراء.\nيرجى شحن رصيد حسابك أولاً.",
        "en": "Your balance is not enough to make purchases.\nPlease top up your account first.",
        "ru": "Недостаточно средств для покупки.\nСначала пополните баланс.",
    },
    "min_order": {
        "ar": "الحد الأدنى للطلب هو {min_order:.0f} USDT.",
        "en": "The minimum order amount is {min_order:.0f} USDT.",
        "ru": "Минимальная сумма заказа — {min_order:.0f} USDT.",
    },
    "pay": {
        "ar": "لشحن الرصيد، أرسل الدفع ثم اضغط زر: تم الدفع.\nبعد ذلك تواصل مع الدعم وأرسل لقطة شاشة أو رابط/Hash الدفع.\n\nUSDT BEP20:\n{wallet}\n\nBybit ID:\n{bybit}\n\nالدعم: {support}",
        "en": "To top up your balance, send the payment then press: I Have Paid.\nAfter that, contact support and send a screenshot or payment hash/link.\n\nUSDT BEP20:\n{wallet}\n\nBybit ID:\n{bybit}\n\nSupport: {support}",
        "ru": "Для пополнения баланса отправьте оплату, затем нажмите: Я оплатил.\nПосле этого свяжитесь с поддержкой и отправьте скриншот или hash/ссылку платежа.\n\nUSDT BEP20:\n{wallet}\n\nBybit ID:\n{bybit}\n\nПоддержка: {support}",
    },
    "i_paid": {"ar": "تم الدفع", "en": "I Have Paid", "ru": "Я оплатил"},
    "pay_bep20": {"ar": "💎 USDT(BEP20)", "en": "💎 USDT(BEP20)", "ru": "💎 USDT(BEP20)"},
    "pay_binance": {"ar": "🪙 Binance ID", "en": "🪙 Binance ID", "ru": "🪙 Binance ID"},
    "pay_bybit": {"ar": "🔑 BYBIT", "en": "🔑 BYBIT", "ru": "🔑 BYBIT"},
    "enter_amount": {
        "ar": "📝 Enter the amount in USD:-\n🪶 Example: 20.50\n\n❌ If you want to cancel the process send /cancel",
        "en": "📝 Enter the amount in USD:-\n🪶 Example: 20.50\n\n❌ If you want to cancel the process send /cancel",
        "ru": "📝 Enter the amount in USD:-\n🪶 Example: 20.50\n\n❌ If you want to cancel the process send /cancel",
    },
    "cancelled": {"ar": "Cancelled.", "en": "Cancelled.", "ru": "Отменено."},
    "paid_sent": {
        "ar": "تم إرسال إشعار الدفع إلى الإدارة.\nيرجى إرسال لقطة الشاشة أو Hash الدفع إلى الدعم.",
        "en": "Your payment notice has been sent to admin.\nPlease send the screenshot or payment hash to support.",
        "ru": "Уведомление об оплате отправлено администратору.\nОтправьте скриншот или hash платежа в поддержку.",
    },
    "buy_now": {"ar": "شراء الآن", "en": "Buy Now", "ru": "Купить сейчас"},
    "add_cart": {"ar": "إضافة للسلة", "en": "Add to Cart", "ru": "В корзину"},
    "add_fav": {"ar": "إضافة للمفضلة", "en": "Add to Favorites", "ru": "В избранное"},
    "gift": {"ar": "إرسال كهدية", "en": "Send as Gift", "ru": "Отправить как подарок"},
    "confirm": {"ar": "تأكيد الشراء", "en": "Confirm Purchase", "ru": "Подтвердить покупку"},
    "order_done": {
        "ar": "تم إنشاء طلبك بنجاح.\nسيتم التواصل معك للتسليم.",
        "en": "Your order has been created successfully.\nYou will be contacted for delivery.",
        "ru": "Ваш заказ успешно создан.\nС вами свяжутся для доставки.",
    },
    "added_cart": {"ar": "تمت الإضافة إلى السلة.", "en": "Added to cart.", "ru": "Добавлено в корзину."},
    "added_fav": {"ar": "تمت الإضافة إلى المفضلة.", "en": "Added to favorites.", "ru": "Добавлено в избранное."},
    "empty_cart": {"ar": "السلة فارغة.", "en": "Your cart is empty.", "ru": "Корзина пуста."},
    "empty_fav": {"ar": "المفضلة فارغة.", "en": "Favorites are empty.", "ru": "Избранное пусто."},
    "clear_cart": {"ar": "تفريغ السلة", "en": "Clear Cart", "ru": "Очистить корзину"},
    "checkout": {"ar": "إتمام الطلب", "en": "Checkout", "ru": "Оформить заказ"},
    "coupon_help": {
        "ar": "لإضافة كوبون اكتب:\n/coupon CODE",
        "en": "To apply coupon, send:\n/coupon CODE",
        "ru": "Чтобы применить купон, отправьте:\n/coupon CODE",
    },
    "coupon_ok": {"ar": "تم تفعيل الكوبون.", "en": "Coupon applied.", "ru": "Купон применён."},
    "coupon_bad": {"ar": "الكوبون غير صحيح أو غير مفعل.", "en": "Invalid or inactive coupon.", "ru": "Купон недействителен или неактивен."},
    "no_orders": {"ar": "لا توجد طلبات حالياً.", "en": "No orders yet.", "ru": "Заказов пока нет."},
    "no_latest": {"ar": "لا توجد عمليات شراء حالياً.", "en": "No purchases yet.", "ru": "Покупок пока нет."},
    "admin_only": {"ar": "هذا الأمر للأدمن فقط.", "en": "This command is for admin only.", "ru": "Эта команда только для администратора."},
    "cancel_payment": {"ar": "إلغاء الدفع", "en": "Cancel Payment", "ru": "Отменить оплату"},
    "payment_cancelled": {"ar": "تم إلغاء عملية الدفع.", "en": "Payment request cancelled.", "ru": "Запрос на оплату отменён."},
    "payment_expired": {"ar": "انتهت صلاحية عملية الدفع. يرجى إنشاء عملية دفع جديدة.", "en": "This payment request has expired. Please create a new one.", "ru": "Срок оплаты истёк. Создайте новый запрос."},
}


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            lang TEXT DEFAULT 'en',
            balance REAL DEFAULT 0,
            active_coupon TEXT DEFAULT '',
            created_at TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            product TEXT,
            price REAL,
            status TEXT DEFAULT 'pending',
            gift_to TEXT DEFAULT '',
            created_at TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS cart(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            cat_key TEXT,
            product_id TEXT,
            quantity INTEGER DEFAULT 1,
            created_at TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS favorites(
            user_id INTEGER,
            cat_key TEXT,
            product_id TEXT,
            created_at TEXT,
            PRIMARY KEY(user_id, cat_key, product_id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS coupons(
            code TEXT PRIMARY KEY,
            discount REAL DEFAULT 0,
            active INTEGER DEFAULT 1,
            created_at TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS payment_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS product_prices(
            cat_key TEXT NOT NULL,
            product_id TEXT NOT NULL,
            label TEXT DEFAULT '',
            price REAL,
            updated_at TEXT,
            PRIMARY KEY(cat_key, product_id)
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS referrals(
            invited_id INTEGER PRIMARY KEY,
            referrer_id INTEGER,
            created_at TEXT
        )""")

        # Safe migrations for old database versions on Railway.
        # CREATE TABLE IF NOT EXISTS does not add new columns to existing tables,
        # so we add missing columns manually.
        user_cols = {row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()}
        if "active_coupon" not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN active_coupon TEXT DEFAULT ''")
        if "created_at" not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
        if "referred_by" not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER DEFAULT 0")
        if "referral_earnings" not in user_cols:
            c.execute("ALTER TABLE users ADD COLUMN referral_earnings REAL DEFAULT 0")

        order_cols = {row[1] for row in c.execute("PRAGMA table_info(orders)").fetchall()}
        if "gift_to" not in order_cols:
            c.execute("ALTER TABLE orders ADD COLUMN gift_to TEXT DEFAULT ''")
        if "created_at" not in order_cols:
            c.execute("ALTER TABLE orders ADD COLUMN created_at TEXT")

        pay_cols = {row[1] for row in c.execute("PRAGMA table_info(payment_requests)").fetchall()}
        if "expires_at" not in pay_cols:
            c.execute("ALTER TABLE payment_requests ADD COLUMN expires_at TEXT")
        if "wallet" not in pay_cols:
            c.execute("ALTER TABLE payment_requests ADD COLUMN wallet TEXT DEFAULT ''")
        if "amount" not in pay_cols:
            c.execute("ALTER TABLE payment_requests ADD COLUMN amount REAL DEFAULT 0")
        if "updated_at" not in pay_cols:
            c.execute("ALTER TABLE payment_requests ADD COLUMN updated_at TEXT")
        if "method" not in pay_cols:
            c.execute("ALTER TABLE payment_requests ADD COLUMN method TEXT DEFAULT 'bep20'")

        seed_product_prices(c, discount_percent=5.0)

        c.execute("""CREATE TABLE IF NOT EXISTS user_min_orders(
            user_id INTEGER PRIMARY KEY,
            min_order REAL NOT NULL,
            created_at TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS banned_users(
            user_id INTEGER PRIMARY KEY,
            reason TEXT DEFAULT '',
            created_at TEXT
        )""")
        c.execute(
            "INSERT OR REPLACE INTO user_min_orders(user_id, min_order, created_at) VALUES(?,?,?)",
            (7106605623, 250.0, datetime.utcnow().isoformat())
        )
        c.commit()

def ensure(u, referrer_id: int = 0):
    with conn() as c:
        r = c.execute("SELECT user_id, referred_by FROM users WHERE user_id=?", (u.id,)).fetchone()
        if not r:
            valid_ref = int(referrer_id) if referrer_id and int(referrer_id) != int(u.id) else 0
            c.execute(
                "INSERT INTO users(user_id, username, first_name, lang, balance, active_coupon, created_at, referred_by, referral_earnings) VALUES(?,?,?,?,?,?,?,?,?)",
                (u.id, u.username or "", u.first_name or "", "en", 0.0, "", datetime.utcnow().isoformat(), valid_ref, 0.0),
            )
            if valid_ref:
                c.execute(
                    "INSERT OR IGNORE INTO referrals(invited_id, referrer_id, created_at) VALUES(?,?,?)",
                    (u.id, valid_ref, datetime.utcnow().isoformat()),
                )
        else:
            c.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?", (u.username or "", u.first_name or "", u.id))
        c.commit()

def user(uid):
    with conn() as c:
        return c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()

def lang(uid):
    u = user(uid)
    return u["lang"] if u and u["lang"] else "en"

def txt(uid, key, **kw):
    return T[key][lang(uid)].format(**kw)

def admin(uid):
    return uid in ADMIN_IDS


def get_min_order(user_id):
    with conn() as c:
        row = c.execute("SELECT min_order FROM user_min_orders WHERE user_id=?", (user_id,)).fetchone()
    return float(row["min_order"]) if row else MIN_ORDER

def is_banned(user_id):
    with conn() as c:
        row = c.execute("SELECT user_id FROM banned_users WHERE user_id=?", (user_id,)).fetchone()
    return row is not None

async def block_if_banned(obj):
    uid = obj.from_user.id
    if is_banned(uid):
        if isinstance(obj, Message):
            await obj.answer("Your account has been blocked. Please contact support.")
        else:
            await obj.answer("Your account has been blocked.", show_alert=True)
        return True
    return False

def set_lang(uid, l):
    with conn() as c:
        c.execute("UPDATE users SET lang=? WHERE user_id=?", (l, uid))
        c.commit()

def add_balance(uid, amount):
    with conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO users(user_id, username, first_name, lang, balance, active_coupon, created_at) VALUES(?,?,?,?,?,?,?)",
            (uid, "", "", "en", 0.0, "", datetime.utcnow().isoformat()),
        )
        c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, uid))
        c.commit()

def set_balance(uid, amount):
    with conn() as c:
        c.execute("UPDATE users SET balance=? WHERE user_id=?", (amount, uid))
        c.commit()

def remove_balance(uid, amount):
    with conn() as c:
        c.execute("UPDATE users SET balance=MAX(balance-?,0) WHERE user_id=?", (amount, uid))
        c.commit()

def raw_iter_items(cat_key):
    items = PRODUCTS.get(cat_key, {}).get("items", [])
    normalized = []
    for item in items:
        if isinstance(item, dict):
            normalized.append({"id": str(item.get("id")), "label": str(item.get("label")), "price": item.get("price")})
        elif isinstance(item, (list, tuple)) and len(item) >= 3:
            normalized.append({"id": str(item[0]), "label": str(item[1]), "price": item[2]})
    return normalized

def seed_product_prices(c, discount_percent: float = 5.0):
    # حفظ الأسعار داخل قاعدة البيانات حتى لا تضيع عند تعديل ملف البايثون.
    # يتم تطبيق تخفيض 5% مرة واحدة فقط على الأسعار الأصلية عند أول تشغيل للتحديث.
    flag = c.execute("SELECT value FROM settings WHERE key=?", ("product_prices_seeded_v2",)).fetchone()
    if flag:
        return
    for cat_key in PRODUCTS.keys():
        for item in raw_iter_items(cat_key):
            price = item.get("price")
            if price is None:
                db_price = None
            else:
                db_price = round(float(price) * (1 - discount_percent / 100.0), 2)
            c.execute(
                "INSERT OR IGNORE INTO product_prices(cat_key, product_id, label, price, updated_at) VALUES(?,?,?,?,?)",
                (cat_key, item["id"], item["label"], db_price, datetime.utcnow().isoformat())
            )
    c.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)", ("product_prices_seeded_v2", "1"))

def get_product_price(cat_key: str, product_id: str, fallback=None):
    try:
        with conn() as c:
            row = c.execute("SELECT price FROM product_prices WHERE cat_key=? AND product_id=?", (cat_key, str(product_id))).fetchone()
        if row and row["price"] is not None:
            return float(row["price"])
    except Exception:
        pass
    return fallback

def set_product_price(cat_key: str, product_id: str, price: float, label: str = ""):
    with conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO product_prices(cat_key, product_id, label, price, updated_at) VALUES(?,?,?,?,?)",
            (cat_key, str(product_id), label, float(price), datetime.utcnow().isoformat())
        )
        c.commit()

def iter_items(cat_key):
    normalized = raw_iter_items(cat_key)
    for item in normalized:
        item["price"] = get_product_price(cat_key, item["id"], item.get("price"))
    return normalized

def get_item(cat_key, pid):
    for item in iter_items(cat_key):
        if item["id"] == pid:
            return item
    return None

def cat_name(cat_key, l):
    cat = PRODUCTS.get(cat_key, {})
    return cat.get(l, cat.get("en", cat_key))

def is_hidden_category(cat_key: str, cat: Dict[str, Any]) -> bool:
    names = " ".join(str(cat.get(k, "")) for k in ("ar", "en", "ru"))
    haystack = f"{cat_key} {names}".lower()
    return any(word in haystack for word in HIDDEN_PRODUCT_KEYWORDS)

def category_custom_emoji_id(cat_key: str, cat: Optional[Dict[str, Any]] = None) -> Optional[str]:
    cat = cat or PRODUCTS.get(cat_key, {})
    names = " ".join(str(cat.get(k, "")) for k in ("ar", "en", "ru"))
    haystack = f"{cat_key} {names}".lower()
    if "razer" in haystack:
        return CUSTOM_EMOJI["razer"]
    if "pubg" in haystack or " uc" in f" {haystack}" or "uc " in haystack:
        return CUSTOM_EMOJI["pubg_uc"]
    if "steam" in haystack:
        return CUSTOM_EMOJI["steam"]
    if "playstation" in haystack or "play station" in haystack or "psn" in haystack:
        return CUSTOM_EMOJI["playstation"]
    if "roblox" in haystack:
        return CUSTOM_EMOJI["roblox"]
    if "itunes" in haystack or "apple" in haystack:
        return CUSTOM_EMOJI["itunes"]
    return None

def product_name(cat_key, item, l):
    return f"{cat_name(cat_key, l)} {item['label']}"

def price_text(price):
    return "Available" if price is None else f"{float(price):.2f} USDT"

def get_setting(key: str, default: str = "") -> str:
    with conn() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)", (key, value))
        c.commit()

def start_flash_discount(percent: float = 2.0, hours: int = 24):
    until = (datetime.utcnow() + timedelta(hours=hours)).isoformat()
    set_setting("flash_discount_percent", str(percent))
    set_setting("flash_discount_until", until)
    return until

def get_flash_discount():
    try:
        until_raw = get_setting("flash_discount_until", "")
        percent = float(get_setting("flash_discount_percent", "0") or 0)
        if not until_raw or percent <= 0:
            return "", 0.0
        until = datetime.fromisoformat(until_raw)
        if datetime.utcnow() >= until:
            set_setting("flash_discount_percent", "0")
            return "", 0.0
        return "24H_DISCOUNT", percent
    except Exception:
        return "", 0.0

def get_discount(uid):
    flash_code, flash_percent = get_flash_discount()
    u = user(uid)
    code = (u["active_coupon"] if u and "active_coupon" in u.keys() else "") or ""
    coupon_code, coupon_percent = "", 0.0
    if code:
        with conn() as c:
            row = c.execute("SELECT * FROM coupons WHERE code=? AND active=1", (code.upper(),)).fetchone()
        if row:
            coupon_code, coupon_percent = row["code"], float(row["discount"])
    if flash_percent >= coupon_percent and flash_percent > 0:
        return flash_code, flash_percent
    if coupon_percent > 0:
        return coupon_code, coupon_percent
    return "", 0.0

def apply_discount(uid, amount):
    code, percent = get_discount(uid)
    if not code or amount <= 0:
        return amount, "", 0.0
    discount_amount = amount * (percent / 100.0)
    final = max(amount - discount_amount, 0)
    return final, code, percent

def add_referral_commission(buyer_id: int, amount: float, percent: float = 3.0):
    u = user(buyer_id)
    if not u or "referred_by" not in u.keys():
        return
    referrer = int(u["referred_by"] or 0)
    if not referrer or referrer == buyer_id or amount <= 0:
        return
    commission = round(amount * (percent / 100.0), 2)
    with conn() as c:
        c.execute("UPDATE users SET balance=balance+?, referral_earnings=referral_earnings+? WHERE user_id=?", (commission, commission, referrer))
        c.commit()

def referral_stats(uid: int):
    with conn() as c:
        invited = c.execute("SELECT COUNT(*) AS n FROM referrals WHERE referrer_id=?", (uid,)).fetchone()["n"]
        u = c.execute("SELECT referral_earnings FROM users WHERE user_id=?", (uid,)).fetchone()
    earnings = float(u["referral_earnings"] or 0.0) if u else 0.0
    return invited, earnings

def styled_button(text: str, *, style: Optional[str] = None, icon_custom_emoji_id: Optional[str] = None, **kwargs) -> InlineKeyboardButton:
    """
    Create Telegram inline buttons with the new Bot API color/style fields.
    Supported styles: danger = red, success = green, primary = blue.
    """
    data = {"text": text, **kwargs}
    if style:
        data["style"] = style
    if icon_custom_emoji_id:
        data["icon_custom_emoji_id"] = icon_custom_emoji_id
    return InlineKeyboardButton(**data)

def menu_reply_keyboard(uid: int) -> ReplyKeyboardMarkup:
    l = lang(uid)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=T["products"][l])],
            [KeyboardButton(text=T["topup"][l]), KeyboardButton(text=T["balance"][l])],
            [KeyboardButton(text=T["orders"][l]), KeyboardButton(text=T["cart"][l])],
            [KeyboardButton(text=T["special_offers"][l]), KeyboardButton(text=T["best_sellers"][l])],
            [KeyboardButton(text=T["favorites"][l]), KeyboardButton(text=T["profile"][l])],
            [KeyboardButton(text=T["referrals"][l]), KeyboardButton(text=T["language"][l])],
            [KeyboardButton(text=T["support"][l]), KeyboardButton(text=T["channel"][l])],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

def display_stock(cat_key: str, item: Dict[str, Any]) -> int:
    raw = item.get("stock", 0)
    try:
        raw = int(raw)
    except Exception:
        raw = 0
    # For display, show strong available stock as requested.
    return max(raw, 8000)

def pretty_product_label(cat_key: str, item: Dict[str, Any]) -> str:
    label = str(item.get("label", "")).strip()
    lower = f"{cat_key} {label}".lower()
    if "pubg" in lower and "uc" in lower:
        amount = label.split()[0]
        if amount.isdigit():
            return f"{amount} UC 1Year Stockable"
    return label

def topup_methods_keyboard(uid: int) -> InlineKeyboardMarkup:
    l = lang(uid)
    return InlineKeyboardMarkup(inline_keyboard=[
        [styled_button(text=T["pay_bep20"][l], callback_data="paymethod:bep20", style="primary"),
         styled_button(text=T["pay_binance"][l], callback_data="paymethod:binance", style="primary")],
        [styled_button(text=T["pay_bybit"][l], callback_data="paymethod:bybit", style="primary"),
         styled_button(text=T["back"][l], callback_data="main", style="danger")],
    ])

def paid_only_keyboard(uid: int, payment_id: Optional[int] = None) -> InlineKeyboardMarkup:
    l = lang(uid)
    paid_cb = f"paid:{payment_id}" if payment_id else "paid"
    return InlineKeyboardMarkup(inline_keyboard=[
        [styled_button(text=f"✅ {T['i_paid'][l]}", callback_data=paid_cb, style="success")],
        [styled_button(text=SUPPORT_USERNAME, url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}", style="success", icon_custom_emoji_id=CUSTOM_EMOJI["support"])],
        [styled_button(text=T["back"][l], callback_data="main", style="danger")],
    ])

def balance_info_message(uid: int) -> str:
    u = user(uid)
    b = float(u["balance"]) if u else 0.0
    name = (u["first_name"] if u and "first_name" in u.keys() else "") or "Customer"
    code, discount = get_discount(uid)
    text = (
        "💵 Your Balance Information\n\n"
        f"Hello, {name}! Here’s your current balance:\n\n"
        f"🔹 Telegram ID: {uid}\n"
        f"🔹 Current Balance: {b:.3f} $\n\n"
        "✨ What would you like to do next?\n"
        "You can top up your balance using one of the following methods:"
    )
    if code:
        text += f"\n\nCoupon: {code} ({discount:.0f}%)"
    return text

def invoice_message(method: str, amount: float) -> str:
    amount_text = f"{amount:.2f}".rstrip("0").rstrip(".")
    if method == "binance":
        return (
            f"🔑 UID: {BINANCE_ID}\n\n"
            "Please send the amount to this UID and include the note\n\n"
            f"{BINANCE_NOTE}\n\n"
            "Make sure you are sending only USDT 💵. After that, click the '✅ I Have Paid' button."
        )
    if method == "bybit":
        return (
            f"🔑 BYBIT ID: {BYBIT_ID}\n\n"
            f"Please send exactly {amount_text} USDT to this BYBIT ID.\n\n"
            "Make sure you are sending only USDT 💵. After that, click the '✅ I Have Paid' button."
        )
    return (
        f"✅ Kindly deposit exactly {amount_text} USDT (BSC) to the address below:\n\n"
        "💼\n\n"
        f"{USDT_BEP20_ADDRESS}\n\n"
        "👆 Tap to copy\n\n"
        "⏰ This invoice will expire in 20 minutes.\n"
        "⏬ Kindly complete the deposit of exact amount within this time frame.\n\n"
        "🕑 This message will be deleted after 20 minutes. 🗑️"
    )

def kb_lang():
    return InlineKeyboardMarkup(inline_keyboard=[
        [styled_button(text=v, callback_data=f"lang:{k}", style="primary")]
        for k, v in LANGS.items()
    ])

def web_reviews_url():
    base = WEB_APP_URL.rstrip("/")
    return f"{base}/#reviews"

def kb_main(uid):
    l = lang(uid)
    rows = [
        [styled_button(text=T["products"][l], callback_data="shop", style="primary", icon_custom_emoji_id=CUSTOM_EMOJI["shop"])],
        [styled_button(text=T["topup"][l], callback_data="topup", style="primary", icon_custom_emoji_id=CUSTOM_EMOJI["topup"]),
         styled_button(text=T["balance"][l], callback_data="balance", style="primary", icon_custom_emoji_id=CUSTOM_EMOJI["balance"])],
        [styled_button(text=T["orders"][l], callback_data="orders", style="primary", icon_custom_emoji_id=CUSTOM_EMOJI["cart_orders"]),
         styled_button(text=T["cart"][l], callback_data="cart", style="primary", icon_custom_emoji_id=CUSTOM_EMOJI["cart_orders"])],
        [styled_button(text=T["special_offers"][l], callback_data="special_offers", style="danger"),
         styled_button(text=T["best_sellers"][l], callback_data="best_sellers", style="danger")],
        [styled_button(text=T["favorites"][l], callback_data="favorites", style="primary"),
         styled_button(text=T["profile"][l], callback_data="profile", style="primary", icon_custom_emoji_id=CUSTOM_EMOJI["profile"])],
        [styled_button(text=T["referrals"][l], callback_data="referrals", style="danger"),
         styled_button(text=T["language"][l], callback_data="choose_lang", style="primary")],
        [styled_button(text=T["support"][l], callback_data="support", style="success", icon_custom_emoji_id=CUSTOM_EMOJI["support"]),
         styled_button(text=T["channel"][l], url=CHANNEL_URL, style="primary", icon_custom_emoji_id=CUSTOM_EMOJI["channel"])],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_cats(uid):
    l = lang(uid)
    rows = []
    for k, v in PRODUCTS.items():
        if is_hidden_category(k, v):
            continue
        rows.append([styled_button(
            text=v.get(l, v.get("en", k)),
            callback_data=f"cat:{k}",
            style="primary",
            icon_custom_emoji_id=category_custom_emoji_id(k, v),
        )])
    rows.append([styled_button(text=T["back"][l], callback_data="main", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_items(uid, cat_key):
    l = lang(uid)
    rows = []
    for item in iter_items(cat_key):
        label = pretty_product_label(cat_key, item)
        rows.append([styled_button(
            text=f"{label} | {price_text(item['price'])} | {display_stock(cat_key, item)}",
            callback_data=f"view:{cat_key}:{item['id']}",
            style="primary"
        )])
    rows.append([styled_button(text=T["back"][l], callback_data="shop", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_product_actions(uid, cat_key, pid):
    l = lang(uid)
    return InlineKeyboardMarkup(inline_keyboard=[
        [styled_button(text=T["buy_now"][l], callback_data=f"buy:{cat_key}:{pid}", style="success")],
        [styled_button(text=T["add_cart"][l], callback_data=f"addcart:{cat_key}:{pid}", style="primary")],
        [styled_button(text=T["add_fav"][l], callback_data=f"addfav:{cat_key}:{pid}", style="danger")],
        [styled_button(text=T["gift"][l], callback_data=f"gift:{cat_key}:{pid}", style="primary")],
        [styled_button(text=T["back"][l], callback_data=f"cat:{cat_key}", style="danger")],
    ])

def payment_keyboard(uid, payment_id: Optional[int] = None):
    l = lang(uid)
    paid_cb = f"paid:{payment_id}" if payment_id else "paid"
    cancel_cb = f"cancel_payment:{payment_id}" if payment_id else "main"
    return InlineKeyboardMarkup(inline_keyboard=[
        [styled_button(text=T["copy_usdt"][l], callback_data="copy_usdt", style="primary", icon_custom_emoji_id=CUSTOM_EMOJI["topup"])],
        [styled_button(text=T["i_paid"][l], callback_data=paid_cb, style="success", icon_custom_emoji_id=CUSTOM_EMOJI["topup"])],
        [styled_button(text=T["cancel_payment"][l], callback_data=cancel_cb, style="danger")],
        [styled_button(text=SUPPORT_USERNAME, url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}", style="success", icon_custom_emoji_id=CUSTOM_EMOJI["support"])],
        [styled_button(text=T["back"][l], callback_data="main", style="danger")],
    ])

def main_back_keyboard(uid):
    l = lang(uid)
    return InlineKeyboardMarkup(inline_keyboard=[[styled_button(text=T["main"][l], callback_data="main", style="primary")]])

def create_payment_request(uid: int, username: str = "", amount: float = 0.0, method: str = "bep20"):
    now = datetime.utcnow()
    expires = now + timedelta(minutes=20)
    with conn() as c:
        # أي عملية قديمة قيد الانتظار لنفس المستخدم تصبح منتهية عند إنشاء عملية جديدة.
        c.execute("UPDATE payment_requests SET status='expired', updated_at=? WHERE user_id=? AND status='pending'", (now.isoformat(), uid))
        cur = c.execute(
            "INSERT INTO payment_requests(user_id, username, status, wallet, amount, method, created_at, expires_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (uid, username or "", "pending", USDT_BEP20_ADDRESS, float(amount or 0), method, now.isoformat(), expires.isoformat(), now.isoformat())
        )
        pid = cur.lastrowid
        c.commit()
    return pid, expires

def get_payment_request(payment_id: int):
    with conn() as c:
        return c.execute("SELECT * FROM payment_requests WHERE id=?", (payment_id,)).fetchone()

def expire_old_payment_requests():
    now = datetime.utcnow().isoformat()
    with conn() as c:
        c.execute("UPDATE payment_requests SET status='expired', updated_at=? WHERE status='pending' AND expires_at IS NOT NULL AND expires_at < ?", (now, now))
        c.commit()

def payment_is_expired(row) -> bool:
    try:
        return bool(row and row["expires_at"] and datetime.utcnow() >= datetime.fromisoformat(row["expires_at"]))
    except Exception:
        return False

def payment_message(uid: int, payment_id: int, expires_at: datetime) -> str:
    l = lang(uid)
    if l == "ar":
        return (
            f"طلب شحن الرصيد #{payment_id}\n\n"
            f"USDT BEP20 Address:\n{USDT_BEP20_ADDRESS}\n\n"
            "لديك 20 دقيقة لإتمام الدفع على هذا العنوان. بعد انتهاء الوقت سيتم إلغاء عملية الدفع تلقائيا.\n\n"
            "بعد الدفع اضغط زر I Have Paid ثم أرسل لقطة شاشة أو رابط/هاش المعاملة للدعم."
        )
    if l == "ru":
        return (
            f"Запрос на пополнение #{payment_id}\n\n"
            f"USDT BEP20 Address:\n{USDT_BEP20_ADDRESS}\n\n"
            "У вас есть 20 минут для оплаты на этот адрес. После окончания времени запрос будет отменён автоматически.\n\n"
            "После оплаты нажмите I Have Paid и отправьте скриншот или hash/link в поддержку."
        )
    return (
        f"Top Up Request #{payment_id}\n\n"
        f"USDT BEP20 Address:\n{USDT_BEP20_ADDRESS}\n\n"
        "You have 20 minutes to complete the payment to this address. After the time ends, this payment request will be cancelled automatically.\n\n"
        "After payment, press I Have Paid and send the screenshot or transaction hash/link to support."
    )

async def safe_edit(cq: CallbackQuery, text: str, reply_markup=None, **kwargs):
    """Edit the current bot message without deleting it, so buttons feel fast and smooth."""
    try:
        if cq.message and cq.message.photo:
            await cq.message.edit_caption(caption=text, reply_markup=reply_markup, **kwargs)
        else:
            await cq.message.edit_text(text, reply_markup=reply_markup, **kwargs)
        return
    except Exception:
        pass
    try:
        await cq.message.answer(text, reply_markup=reply_markup, **kwargs)
    except Exception:
        pass

async def notify_admins(text):
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, text)
        except Exception:
            pass

async def send_welcome_message(m: Message):
    photo_candidates = [
        Path(WELCOME_PHOTO_PATH),
        BASE_DIR / WELCOME_PHOTO_PATH,
        BASE_DIR / "photo_2026-06-13_18-11-52.jpg",
        BASE_DIR / "md_store_welcome.jpg",
    ]
    for photo_path in photo_candidates:
        if photo_path.exists():
            try:
                await m.answer_photo(
                    FSInputFile(photo_path),
                    caption=txt(m.from_user.id, "welcome"),
                    reply_markup=menu_reply_keyboard(m.from_user.id),
                )
                return
            except Exception:
                continue
    await m.answer(txt(m.from_user.id, "welcome"), reply_markup=menu_reply_keyboard(m.from_user.id))

@dp.message(CommandStart())
async def start(m: Message):
    referrer_id = 0
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) > 1:
        payload = parts[1].strip()
        if payload.startswith("ref_") and payload[4:].isdigit():
            referrer_id = int(payload[4:])
    ensure(m.from_user, referrer_id)

    for aid in ADMIN_IDS:
        try:
            await bot.send_message(
                aid,
                f"New User Started Bot\n\n"
                f"ID: {m.from_user.id}\n"
                f"Username: @{m.from_user.username}\n"
                f"Name: {m.from_user.first_name}\n"
                f"Referrer ID: {referrer_id or 'None'}"
            )
        except Exception:
            pass

    await send_welcome_message(m)

@dp.message(Command("language"))
async def cmd_language(m: Message):
    ensure(m.from_user)
    await m.answer(T["choose_lang"][lang(m.from_user.id)], reply_markup=kb_lang())


@dp.message(Command("admin"))
async def admin_panel(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    await m.answer(
        "MD STORE Admin Panel\n\n"
        "/addbalance USER_ID AMOUNT\n"
        "/removebalance USER_ID AMOUNT\n"
        "/setbalance USER_ID AMOUNT\n"
        "/check USER_ID\n"
        "/orders\n"
        "/broadcast MESSAGE\n"
        "/addcoupon CODE PERCENT\n"
        "/delcoupon CODE\n"
        "/coupons\n"
        "/ban USER_ID\n"
        "/unban USER_ID\n"
        "/setmin USER_ID AMOUNT\n"
        "/resetmin USER_ID\n"
        "/discount24\n"
        "/prices\n"
        "/setprice CAT_KEY PRODUCT_ID PRICE\n"
        "/discountall PERCENT\n"
        "/payments"
    )

@dp.message(Command("addbalance"))
async def cmd_addbalance(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    p = m.text.split()
    if len(p) != 3:
        return await m.answer("Usage: /addbalance USER_ID AMOUNT")
    try:
        uid = int(p[1])
        amount = float(p[2])
        add_balance(uid, amount)
        await m.answer(f"Balance Added\n\nUser ID: {uid}\nAmount: {amount:.2f} USDT")
        try:
            await bot.send_message(uid, f"Your balance has been topped up by {amount:.2f} USDT.")
        except Exception:
            pass
    except Exception:
        await m.answer("Invalid input")

@dp.message(Command("removebalance"))
async def cmd_removebalance(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    p = m.text.split()
    if len(p) != 3:
        return await m.answer("Usage: /removebalance USER_ID AMOUNT")
    try:
        remove_balance(int(p[1]), float(p[2]))
        await m.answer("Balance removed.")
    except Exception:
        await m.answer("Invalid input")

@dp.message(Command("setbalance"))
async def cmd_setbalance(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    p = m.text.split()
    if len(p) != 3:
        return await m.answer("Usage: /setbalance USER_ID AMOUNT")
    try:
        uid = int(p[1])
        amount = float(p[2])
        add_balance(uid, 0)
        set_balance(uid, amount)
        await m.answer(f"Balance set.\nUser ID: {uid}\nBalance: {amount:.2f} USDT")
    except Exception:
        await m.answer("Invalid input")

@dp.message(Command("check"))
async def cmd_check(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    p = m.text.split()
    if len(p) != 2 or not p[1].isdigit():
        return await m.answer("Usage: /check USER_ID")
    u = user(int(p[1]))
    await m.answer(
        "User not found." if not u else
        f"User Info\n\nID: {u['user_id']}\nUsername: @{u['username']}\nBalance: {u['balance']:.2f} USDT\nLanguage: {u['lang']}\nCoupon: {u['active_coupon'] or '-'}"
    )

@dp.message(Command("orders"))
async def cmd_orders_admin(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    with conn() as c:
        rows = c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 25").fetchall()
    if not rows:
        return await m.answer("No orders.")
    text = "Last Orders\n\n"
    for r in rows:
        text += f"#{r['id']} | {r['user_id']} | {r['product']} | {r['price']:.2f} USDT | {r['status']}\n"
    await m.answer(text)

@dp.message(Command("broadcast"))
async def cmd_broadcast(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    msg = m.text.replace("/broadcast", "", 1).strip()
    if not msg:
        return await m.answer("Usage: /broadcast MESSAGE")
    with conn() as c:
        users = c.execute("SELECT user_id FROM users").fetchall()
    sent = 0
    for u in users:
        try:
            await bot.send_message(u["user_id"], msg)
            sent += 1
        except Exception:
            pass
    await m.answer(f"Broadcast sent to {sent} users.")

@dp.message(Command("addcoupon"))
async def cmd_addcoupon(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    p = m.text.split()
    if len(p) != 3:
        return await m.answer("Usage: /addcoupon CODE PERCENT")
    try:
        code = p[1].upper()
        percent = float(p[2])
        with conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO coupons(code, discount, active, created_at) VALUES(?,?,1,?)",
                (code, percent, datetime.utcnow().isoformat())
            )
            c.commit()
        await m.answer(f"Coupon saved.\nCode: {code}\nDiscount: {percent}%")
    except Exception:
        await m.answer("Invalid coupon data.")

@dp.message(Command("delcoupon"))
async def cmd_delcoupon(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    p = m.text.split()
    if len(p) != 2:
        return await m.answer("Usage: /delcoupon CODE")
    with conn() as c:
        c.execute("UPDATE coupons SET active=0 WHERE code=?", (p[1].upper(),))
        c.commit()
    await m.answer("Coupon disabled.")

@dp.message(Command("coupons"))
async def cmd_coupons(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    with conn() as c:
        rows = c.execute("SELECT * FROM coupons ORDER BY created_at DESC LIMIT 30").fetchall()
    if not rows:
        return await m.answer("No coupons.")
    await m.answer("\n".join([f"{r['code']} | {r['discount']}% | {'active' if r['active'] else 'off'}" for r in rows]))


@dp.message(Command("discount24"))
async def cmd_discount24(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    until = start_flash_discount(2.0, 24)
    await m.answer(f"2% discount activated for 24 hours. Ends UTC: {until}")

@dp.message(Command("prices"))
async def cmd_prices(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    lines = ["Product Prices", "Use: /setprice CAT_KEY PRODUCT_ID PRICE", ""]
    for cat_key, cat in PRODUCTS.items():
        if is_hidden_category(cat_key, cat):
            continue
        lines.append(f"[{cat_key}] {cat.get('en', cat_key)}")
        for item in iter_items(cat_key):
            lines.append(f"  {item['id']} | {item['label']} | {price_text(item['price'])}")
        lines.append("")
    text = "\n".join(lines)
    for i in range(0, len(text), 3900):
        await m.answer(text[i:i+3900])

@dp.message(Command("setprice"))
async def cmd_setprice(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    p = m.text.split()
    if len(p) != 4:
        return await m.answer("Usage: /setprice CAT_KEY PRODUCT_ID PRICE")
    cat_key, pid = p[1], p[2]
    item = get_item(cat_key, pid)
    if not item:
        return await m.answer("Product not found. Use /prices to see CAT_KEY and PRODUCT_ID.")
    try:
        price = float(p[3])
        set_product_price(cat_key, pid, price, item.get("label", ""))
        await m.answer(f"Price updated.\nCategory: {cat_key}\nProduct: {item['label']}\nNew price: {price:.2f} USDT")
    except Exception:
        await m.answer("Invalid price.")

@dp.message(Command("discountall"))
async def cmd_discountall(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    p = m.text.split()
    if len(p) != 2:
        return await m.answer("Usage: /discountall PERCENT")
    try:
        percent = float(p[1])
        if percent < 0 or percent > 90:
            return await m.answer("Percent must be between 0 and 90.")
        count = 0
        for cat_key, cat in PRODUCTS.items():
            if is_hidden_category(cat_key, cat):
                continue
            for item in iter_items(cat_key):
                if item.get("price") is None:
                    continue
                new_price = round(float(item["price"]) * (1 - percent / 100.0), 2)
                set_product_price(cat_key, item["id"], new_price, item.get("label", ""))
                count += 1
        await m.answer(f"Discount applied to all current product prices.\nPercent: {percent}%\nUpdated products: {count}")
    except Exception:
        await m.answer("Invalid percent.")

@dp.message(Command("payments"))
async def cmd_payments(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    expire_old_payment_requests()
    with conn() as c:
        rows = c.execute("SELECT * FROM payment_requests ORDER BY id DESC LIMIT 30").fetchall()
    if not rows:
        return await m.answer("No payment requests.")
    text = "Payment Requests\n\n"
    for r in rows:
        text += f"#{r['id']} | User: {r['user_id']} | @{r['username']} | {r['status']} | Created: {r['created_at']} | Expires: {r['expires_at'] or '-'}\n"
    await m.answer(text[:4000])

@dp.message(Command("coupon"))
async def cmd_coupon(m: Message):
    ensure(m.from_user)
    p = m.text.split()
    if len(p) != 2:
        return await m.answer(txt(m.from_user.id, "coupon_help"))
    code = p[1].upper()
    with conn() as c:
        row = c.execute("SELECT * FROM coupons WHERE code=? AND active=1", (code,)).fetchone()
        if not row:
            return await m.answer(txt(m.from_user.id, "coupon_bad"))
        c.execute("UPDATE users SET active_coupon=? WHERE user_id=?", (code, m.from_user.id))
        c.commit()
    await m.answer(txt(m.from_user.id, "coupon_ok"))


@dp.message(Command("ban"))
async def cmd_ban(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    p = m.text.split(maxsplit=2)
    if len(p) < 2 or not p[1].isdigit():
        return await m.answer("Usage: /ban USER_ID")
    uid = int(p[1])
    reason = p[2] if len(p) > 2 else ""
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO banned_users(user_id, reason, created_at) VALUES(?,?,?)", (uid, reason, datetime.utcnow().isoformat()))
        c.commit()
    await m.answer(f"User banned.\nUser ID: {uid}")

@dp.message(Command("unban"))
async def cmd_unban(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    p = m.text.split()
    if len(p) != 2 or not p[1].isdigit():
        return await m.answer("Usage: /unban USER_ID")
    uid = int(p[1])
    with conn() as c:
        c.execute("DELETE FROM banned_users WHERE user_id=?", (uid,))
        c.commit()
    await m.answer(f"User unbanned.\nUser ID: {uid}")

@dp.message(Command("setmin"))
async def cmd_setmin(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    p = m.text.split()
    if len(p) != 3 or not p[1].isdigit():
        return await m.answer("Usage: /setmin USER_ID AMOUNT")
    try:
        uid = int(p[1])
        amount = float(p[2])
        with conn() as c:
            c.execute("INSERT OR REPLACE INTO user_min_orders(user_id, min_order, created_at) VALUES(?,?,?)", (uid, amount, datetime.utcnow().isoformat()))
            c.commit()
        await m.answer(f"Custom minimum order saved.\nUser ID: {uid}\nMinimum: {amount:.2f} USDT")
    except Exception:
        await m.answer("Invalid input")

@dp.message(Command("resetmin"))
async def cmd_resetmin(m: Message):
    if not admin(m.from_user.id):
        return await m.answer(T["admin_only"]["en"])
    p = m.text.split()
    if len(p) != 2 or not p[1].isdigit():
        return await m.answer("Usage: /resetmin USER_ID")
    uid = int(p[1])
    with conn() as c:
        c.execute("DELETE FROM user_min_orders WHERE user_id=?", (uid,))
        c.commit()
    await m.answer(f"Custom minimum removed.\nUser ID: {uid}\nDefault minimum: {MIN_ORDER:.2f} USDT")

@dp.callback_query(F.data.startswith("lang:"))
async def cb_lang(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    ensure(cq.from_user)
    set_lang(cq.from_user.id, cq.data.split(":")[1])
    await safe_edit(cq, txt(cq.from_user.id, "welcome"), reply_markup=None)
    await cq.message.answer(T["main"][lang(cq.from_user.id)], reply_markup=menu_reply_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "choose_lang")
async def cb_choose_lang(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    await safe_edit(cq, T["choose_lang"][lang(cq.from_user.id)], reply_markup=kb_lang())
    await cq.answer()

@dp.callback_query(F.data == "main")
async def cb_main(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    PENDING_TOPUP.pop(cq.from_user.id, None)
    PENDING_QUANTITY.pop(cq.from_user.id, None)
    await safe_edit(cq, txt(cq.from_user.id, "welcome"), reply_markup=None)
    await cq.message.answer(T["main"][lang(cq.from_user.id)], reply_markup=menu_reply_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "shop")
async def cb_shop(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    PENDING_TOPUP.pop(cq.from_user.id, None)
    PENDING_QUANTITY.pop(cq.from_user.id, None)
    await safe_edit(cq, txt(cq.from_user.id, "category_text"), reply_markup=kb_cats(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "topup")
async def cb_topup(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    PENDING_TOPUP.pop(cq.from_user.id, None)
    ensure(cq.from_user)
    expire_old_payment_requests()
    await safe_edit(cq, balance_info_message(cq.from_user.id), reply_markup=topup_methods_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data.startswith("paymethod:"))
async def cb_paymethod(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    method = cq.data.split(":", 1)[1]
    if method not in {"bep20", "binance", "bybit"}:
        return await cq.answer("Unavailable", show_alert=True)
    PENDING_TOPUP[cq.from_user.id] = {"method": method}
    await safe_edit(cq, txt(cq.from_user.id, "enter_amount"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [styled_button(text=T["back"][lang(cq.from_user.id)], callback_data="topup", style="danger")]
    ]))
    await cq.answer()

@dp.callback_query(F.data.startswith("paid"))
async def cb_paid(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    ensure(cq.from_user)
    expire_old_payment_requests()
    parts = cq.data.split(":")
    pid = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else 0
    if not pid:
        with conn() as c:
            row = c.execute("SELECT * FROM payment_requests WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1", (cq.from_user.id,)).fetchone()
        if not row:
            pid, _ = create_payment_request(cq.from_user.id, cq.from_user.username or "")
        else:
            pid = int(row["id"])
    row = get_payment_request(pid)
    if not row or int(row["user_id"]) != int(cq.from_user.id):
        return await cq.answer("Payment request not found", show_alert=True)
    if row["status"] != "pending" or payment_is_expired(row):
        with conn() as c:
            c.execute("UPDATE payment_requests SET status='expired', updated_at=? WHERE id=? AND status='pending'", (datetime.utcnow().isoformat(), pid))
            c.commit()
        await safe_edit(cq, txt(cq.from_user.id, "payment_expired"), reply_markup=main_back_keyboard(cq.from_user.id))
        return await cq.answer()
    with conn() as c:
        c.execute("UPDATE payment_requests SET status='paid', updated_at=? WHERE id=?", (datetime.utcnow().isoformat(), pid))
        c.commit()
    amount_info = ""
    try:
        amount_info = f"\nAmount: {float(row['amount'] or 0):.2f} USDT\nMethod: {row['method'] or 'bep20'}"
    except Exception:
        pass
    await notify_admins(
        f"Payment Notice #{pid}\n\nUser ID: {cq.from_user.id}\nUsername: @{cq.from_user.username}\nStatus: Paid / Waiting Review{amount_info}\nWallet: {USDT_BEP20_ADDRESS}\n\nAsk the user for screenshot/hash if needed, then add balance manually after verification."
    )
    await safe_edit(cq, txt(cq.from_user.id, "paid_sent"), reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data.startswith("cancel_payment:"))
async def cb_cancel_payment(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    pid = int(cq.data.split(":", 1)[1])
    row = get_payment_request(pid)
    if row and int(row["user_id"]) == int(cq.from_user.id) and row["status"] == "pending":
        with conn() as c:
            c.execute("UPDATE payment_requests SET status='cancelled', updated_at=? WHERE id=?", (datetime.utcnow().isoformat(), pid))
            c.commit()
    await safe_edit(cq, txt(cq.from_user.id, "payment_cancelled"), reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "copy_usdt")
async def cb_copy_usdt(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    await cq.message.answer(USDT_BEP20_ADDRESS)
    await cq.answer()

@dp.callback_query(F.data == "faq")
async def cb_faq(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    l = lang(cq.from_user.id)
    if l == "ar":
        text = (
            "الأسئلة الشائعة\n\n"
            "من نحن؟\n"
            "نحن MD STORE متجر متخصص في بيع البطاقات الرقمية وشحن الألعاب للتجار والعملاء مع دعم سريع وأسعار مناسبة.\n\n"
            "كيف أثق؟\n"
            f"يمكنك التواصل معنا للحصول على مراجعات وتجارب العملاء عبر {SUPPORT_USERNAME}.\n\n"
            "كيف يعمل البوت؟\n"
            "تختار المنتج ثم تشحن محفظتك داخل البوت وتؤكد الطلب وبعدها يتم تجهيز وتسليم الكود.\n\n"
            "هل الأكواد فورية؟\n"
            "نعم، الأكواد تسليم فوري وصالحة للتخزين سنة كاملة."
        )
    elif l == "ru":
        text = (
            "FAQ\n\n"
            "Кто мы?\n"
            "MD STORE — магазин цифровых карт и игровых пополнений для клиентов и реселлеров.\n\n"
            "Как доверять?\n"
            f"Свяжитесь с нами для отзывов клиентов: {SUPPORT_USERNAME}.\n\n"
            "Как работает бот?\n"
            "Вы выбираете товар, пополняете баланс в боте, подтверждаете заказ, затем получаете код.\n\n"
            "Коды быстрые?\n"
            "Да, доставка мгновенная, коды можно хранить целый год."
        )
    else:
        text = (
            "FAQ\n\n"
            "Who are we?\n"
            "We are MD STORE, a digital gift card and game top-up store for customers and resellers with fast support and good prices.\n\n"
            "How can I trust?\n"
            f"Contact us for customer reviews and proof: {SUPPORT_USERNAME}.\n\n"
            "How does the bot work?\n"
            "Choose a product, top up your wallet in the bot, confirm your order, then receive your code.\n\n"
            "Are codes instant?\n"
            "Yes, codes are delivered instantly and are valid for storage for a full year."
        )
    await safe_edit(cq, text, reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "referrals")
async def cb_referrals(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    ensure(cq.from_user)
    invited, earnings = referral_stats(cq.from_user.id)
    bot_username = (await bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=ref_{cq.from_user.id}"
    text = (
        f"Referral System\n\n"
        f"Your referral link:\n{link}\n\n"
        f"Invited users: {invited}\n"
        f"Referral earnings: {earnings:.2f} USDT\n\n"
        f"Share your link. When your invited users buy, you receive referral balance."
    )
    await safe_edit(cq, text, reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "balance")
async def cb_balance(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    ensure(cq.from_user)
    await safe_edit(cq, balance_info_message(cq.from_user.id), reply_markup=topup_methods_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "support")
async def cb_support(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    text = txt(cq.from_user.id, "pay", wallet=USDT_BEP20_ADDRESS, bybit=BYBIT_ID, support=SUPPORT_USERNAME)
    await safe_edit(cq, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [styled_button(text=SUPPORT_USERNAME, url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}", style="success", icon_custom_emoji_id=CUSTOM_EMOJI["support"])],
        [styled_button(text=T["channel"][lang(cq.from_user.id)], url=CHANNEL_URL, style="primary", icon_custom_emoji_id=CUSTOM_EMOJI["channel"])],
        [styled_button(text=T["back"][lang(cq.from_user.id)], callback_data="main", style="danger")]
    ]))
    await cq.answer()

@dp.callback_query(F.data == "orders")
async def cb_orders(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    with conn() as c:
        rows = c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (cq.from_user.id,)).fetchall()
    if not rows:
        text = txt(cq.from_user.id, "no_orders")
    else:
        text = "My Orders\n\n"
        for r in rows:
            text += f"#{r['id']} | {r['product']}\nAmount: {r['price']:.2f} USDT\nStatus: {r['status']}\n\n"
    await safe_edit(cq, text, reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "latest")
async def cb_latest(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    with conn() as c:
        rows = c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 10").fetchall()
    if not rows:
        text = txt(cq.from_user.id, "no_latest")
    else:
        text = "Latest Purchases\n\n"
        for r in rows:
            text += f"Someone purchased {r['product']}\nAmount: {r['price']:.2f} USDT\nStatus: {r['status']}\n\n"
    await safe_edit(cq, text, reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "profile")
async def cb_profile(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    u = user(cq.from_user.id)
    invited, earnings = referral_stats(cq.from_user.id)
    b = float(u["balance"]) if u else 0.0
    text = (
        "Profile\n\n"
        f"ID: {cq.from_user.id}\n"
        f"Username: @{cq.from_user.username}\n"
        f"Balance: {b:.2f} USDT\n"
        f"Invited users: {invited}\n"
        f"Referral earnings: {earnings:.2f} USDT"
    )
    await safe_edit(cq, text, reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "special_offers")
async def cb_special_offers(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    text = (
        "Special Offers\n\n"
        "HOT DEAL: Razer Gold and PUBG UC are available with trader prices.\n"
        "Coupon: WELCOME5\n"
        "For every 200 USDT deposit, contact support to receive a 5 USDT discount."
    )
    await safe_edit(cq, text, reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "best_sellers")
async def cb_best_sellers(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    text = (
        "Best Sellers\n\n"
        "Razer Gold\n"
        "PUBG UC\n"
        "Steam USA\n"
        "PlayStation USA\n"
        "iTunes USA\n"
        "Roblox Gift Cards"
    )
    await safe_edit(cq, text, reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "reviews")
async def cb_reviews(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    text = (
        "Customer Reviews\n\n"
        "Open the MD STORE Web App to view customer reviews, ratings, and proof of recent deals."
    )
    await safe_edit(cq, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [styled_button(text="Open Reviews", web_app=WebAppInfo(url=web_reviews_url()), style="success")],
        [styled_button(text=T["back"][lang(cq.from_user.id)], callback_data="main", style="danger")]
    ]))
    await cq.answer()

@dp.callback_query(F.data == "coupons")
async def cb_coupons(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    text = (
        "Coupons\n\n"
        "WELCOME5\n"
        "Every 200 USDT deposit can receive a 5 USDT discount.\n\n"
        "To apply a coupon, send:\n/coupon CODE"
    )
    await safe_edit(cq, text, reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "wholesale")
async def cb_wholesale(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    text = (
        "Wholesale Prices\n\n"
        "MD STORE supplies digital cards and game top-ups for traders and resellers.\n"
        "For large quantities and long-term cooperation, contact support.\n\n"
        f"Minimum order: {get_min_order(cq.from_user.id):.0f} USDT"
    )
    await safe_edit(cq, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [styled_button(text=SUPPORT_USERNAME, url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}", style="success", icon_custom_emoji_id=CUSTOM_EMOJI["support"])],
        [styled_button(text=T["back"][lang(cq.from_user.id)], callback_data="main", style="danger")]
    ]))
    await cq.answer()

@dp.callback_query(F.data.startswith("cat:"))
async def cb_cat(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    cat_key = cq.data.split(":")[1]
    cat = PRODUCTS.get(cat_key, {})
    if is_hidden_category(cat_key, cat):
        await cq.answer("Product is unavailable", show_alert=True)
        return
    await safe_edit(cq, "✨ Here are some amazing products we have for you:", reply_markup=kb_items(cq.from_user.id, cat_key))
    await cq.answer()

@dp.callback_query(F.data.startswith("view:"))
async def cb_view(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    _, cat_key, pid = cq.data.split(":")
    item = get_item(cat_key, pid)
    if not item:
        return await cq.answer("Product not found", show_alert=True)
    l = lang(cq.from_user.id)
    name = pretty_product_label(cat_key, item)
    text = (
        f"🛍️ {name}\n\n"
        f"- ID: {pid}\n"
        "- Description: N/A\n"
        f"- Price: {price_text(item['price'])}\n"
        f"- In Stock: {display_stock(cat_key, item)} items available"
    )
    await safe_edit(cq, text, reply_markup=kb_product_actions(cq.from_user.id, cat_key, pid))
    await cq.answer()

@dp.callback_query(F.data.startswith("addcart:"))
async def cb_addcart(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    _, cat_key, pid = cq.data.split(":")
    item = get_item(cat_key, pid)
    if not item:
        return await cq.answer("Product not found", show_alert=True)
    with conn() as c:
        c.execute(
            "INSERT INTO cart(user_id, cat_key, product_id, quantity, created_at) VALUES(?,?,?,?,?)",
            (cq.from_user.id, cat_key, pid, 1, datetime.utcnow().isoformat())
        )
        c.commit()
    await cq.answer(txt(cq.from_user.id, "added_cart"), show_alert=True)

@dp.callback_query(F.data.startswith("addfav:"))
async def cb_addfav(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    _, cat_key, pid = cq.data.split(":")
    item = get_item(cat_key, pid)
    if not item:
        return await cq.answer("Product not found", show_alert=True)
    with conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO favorites(user_id, cat_key, product_id, created_at) VALUES(?,?,?,?)",
            (cq.from_user.id, cat_key, pid, datetime.utcnow().isoformat())
        )
        c.commit()
    await cq.answer(txt(cq.from_user.id, "added_fav"), show_alert=True)

@dp.callback_query(F.data == "favorites")
async def cb_favorites(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    l = lang(cq.from_user.id)
    with conn() as c:
        rows = c.execute("SELECT * FROM favorites WHERE user_id=? ORDER BY created_at DESC", (cq.from_user.id,)).fetchall()
    if not rows:
        return await safe_edit(cq, txt(cq.from_user.id, "empty_fav"), reply_markup=main_back_keyboard(cq.from_user.id))
    buttons = []
    for r in rows:
        item = get_item(r["cat_key"], r["product_id"])
        if item:
            buttons.append([styled_button(text=product_name(r["cat_key"], item, l), callback_data=f"view:{r['cat_key']}:{r['product_id']}", style="primary")])
    buttons.append([styled_button(text=T["back"][l], callback_data="main", style="danger")])
    await safe_edit(cq, T["favorites"][l], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await cq.answer()

@dp.callback_query(F.data == "cart")
async def cb_cart(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    l = lang(cq.from_user.id)
    with conn() as c:
        rows = c.execute("SELECT * FROM cart WHERE user_id=? ORDER BY id DESC", (cq.from_user.id,)).fetchall()
    if not rows:
        return await safe_edit(cq, txt(cq.from_user.id, "empty_cart"), reply_markup=main_back_keyboard(cq.from_user.id))
    total = 0.0
    text = "Cart\n\n"
    for r in rows:
        item = get_item(r["cat_key"], r["product_id"])
        if not item:
            continue
        price = float(item["price"] or 0.0)
        total += price
        text += f"{product_name(r['cat_key'], item, l)} — {price_text(item['price'])}\n"
    final, code, percent = apply_discount(cq.from_user.id, total)
    text += f"\nSubtotal: {total:.2f} USDT"
    if code:
        text += f"\nCoupon: {code} - {percent:.0f}%\nTotal: {final:.2f} USDT"
    text += "\n\n" + txt(cq.from_user.id, "coupon_help")
    await safe_edit(cq, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [styled_button(text=T["checkout"][l], callback_data="checkout", style="success")],
        [styled_button(text=T["clear_cart"][l], callback_data="clearcart", style="danger")],
        [styled_button(text=T["back"][l], callback_data="main", style="danger")]
    ]))
    await cq.answer()

@dp.callback_query(F.data == "clearcart")
async def cb_clearcart(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    with conn() as c:
        c.execute("DELETE FROM cart WHERE user_id=?", (cq.from_user.id,))
        c.commit()
    await safe_edit(cq, txt(cq.from_user.id, "empty_cart"), reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

async def create_order(cq: CallbackQuery, product: str, price: float, gift_to: str = ""):
    with conn() as c:
        if price > 0:
            c.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (price, cq.from_user.id))
        cur = c.execute(
            "INSERT INTO orders(user_id, username, product, price, status, gift_to, created_at) VALUES(?,?,?,?,?,?,?)",
            (cq.from_user.id, cq.from_user.username or "", product, price, "pending", gift_to, datetime.utcnow().isoformat())
        )
        oid = cur.lastrowid
        c.commit()
    add_referral_commission(cq.from_user.id, price)
    gift_line = f"\nGift To: {gift_to}" if gift_to else ""
    await notify_admins(
        f"New Order #{oid}\n\nUser ID: {cq.from_user.id}\nUsername: @{cq.from_user.username}\nProduct: {product}\nAmount: {price:.2f} USDT{gift_line}"
    )
    return oid

@dp.callback_query(F.data == "checkout")
async def cb_checkout(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    u = user(cq.from_user.id)
    balance = float(u["balance"]) if u else 0.0
    l = lang(cq.from_user.id)

    if balance <= 0:
        return await safe_edit(cq, txt(cq.from_user.id, "need_balance"), reply_markup=main_back_keyboard(cq.from_user.id))
    if balance < get_min_order(cq.from_user.id):
        return await safe_edit(cq, txt(cq.from_user.id, "min_order", min_order=get_min_order(cq.from_user.id)), reply_markup=main_back_keyboard(cq.from_user.id))

    with conn() as c:
        rows = c.execute("SELECT * FROM cart WHERE user_id=? ORDER BY id", (cq.from_user.id,)).fetchall()

    if not rows:
        return await safe_edit(cq, txt(cq.from_user.id, "empty_cart"), reply_markup=main_back_keyboard(cq.from_user.id))

    total = 0.0
    names = []
    for r in rows:
        item = get_item(r["cat_key"], r["product_id"])
        if item:
            total += float(item["price"] or 0.0)
            names.append(product_name(r["cat_key"], item, l))
    final, code, percent = apply_discount(cq.from_user.id, total)

    if balance < final:
        return await safe_edit(cq, txt(cq.from_user.id, "need_balance"), reply_markup=main_back_keyboard(cq.from_user.id))

    await create_order(cq, "Cart: " + ", ".join(names), final)
    with conn() as c:
        c.execute("DELETE FROM cart WHERE user_id=?", (cq.from_user.id,))
        c.commit()

    await safe_edit(cq, txt(cq.from_user.id, "order_done"), reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data.startswith("buy:"))
async def cb_buy(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    _, cat_key, pid = cq.data.split(":")
    item = get_item(cat_key, pid)
    if not item:
        return await cq.answer("Product not found", show_alert=True)

    stock = display_stock(cat_key, item)
    name = pretty_product_label(cat_key, item)
    PENDING_QUANTITY[cq.from_user.id] = {"cat_key": cat_key, "pid": pid, "max": stock}
    text = (
        f"You are purchasing {name}\n\n"
        f"📝 Enter a quantity between 1 and {stock}:\n\n"
        "❌ If you want to cancel the process, send /cancel"
    )
    await safe_edit(cq, text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [styled_button(text=T["back"][lang(cq.from_user.id)], callback_data=f"view:{cat_key}:{pid}", style="danger")]
    ]))
    await cq.answer()

@dp.callback_query(F.data.startswith("gift:"))
async def cb_gift(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    _, cat_key, pid = cq.data.split(":")
    item = get_item(cat_key, pid)
    if not item:
        return await cq.answer("Product not found", show_alert=True)
    l = lang(cq.from_user.id)
    pname = product_name(cat_key, item, l)
    await safe_edit(cq, 
        f"{T['gift'][l]}\n\n{pname}\n\nTo send this as a gift, confirm the purchase then send the recipient details to support.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [styled_button(text=T["confirm"][l], callback_data=f"confirmgift:{cat_key}:{pid}", style="success")],
            [styled_button(text=T["back"][l], callback_data=f"view:{cat_key}:{pid}", style="danger")]
        ])
    )
    await cq.answer()

@dp.callback_query(F.data.startswith("confirmgift:"))
async def cb_confirm_gift(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    _, cat_key, pid = cq.data.split(":")
    item = get_item(cat_key, pid)
    if not item:
        return await cq.answer("Product not found", show_alert=True)
    u = user(cq.from_user.id)
    b = float(u["balance"]) if u else 0.0
    if b <= 0:
        return await safe_edit(cq, txt(cq.from_user.id, "need_balance"), reply_markup=main_back_keyboard(cq.from_user.id))
    if b < get_min_order(cq.from_user.id):
        return await safe_edit(cq, txt(cq.from_user.id, "min_order", min_order=get_min_order(cq.from_user.id)), reply_markup=main_back_keyboard(cq.from_user.id))
    price_val = float(item["price"] or 0.0)
    final, code, percent = apply_discount(cq.from_user.id, price_val)
    if b < final:
        return await safe_edit(cq, txt(cq.from_user.id, "need_balance"), reply_markup=main_back_keyboard(cq.from_user.id))
    pname = product_name(cat_key, item, lang(cq.from_user.id))
    await create_order(cq, pname, final, gift_to="Recipient details will be sent to support")
    await safe_edit(cq, txt(cq.from_user.id, "order_done"), reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data.startswith("confirm:"))
async def cb_confirm(cq: CallbackQuery):
    if await block_if_banned(cq):
        return
    _, cat_key, pid = cq.data.split(":")
    item = get_item(cat_key, pid)
    if not item:
        return await cq.answer("Product not found", show_alert=True)

    u = user(cq.from_user.id)
    b = float(u["balance"]) if u else 0.0

    if b <= 0:
        return await safe_edit(cq, txt(cq.from_user.id, "need_balance"), reply_markup=main_back_keyboard(cq.from_user.id))
    if b < get_min_order(cq.from_user.id):
        return await cq.answer(f"Minimum order is {get_min_order(cq.from_user.id):.0f} USDT", show_alert=True)

    price_val = float(item["price"] or 0.0)
    final, code, percent = apply_discount(cq.from_user.id, price_val)

    if b < final:
        return await cq.answer("Not enough balance", show_alert=True)

    pname = product_name(cat_key, item, lang(cq.from_user.id))
    await create_order(cq, pname, final)
    await safe_edit(cq, txt(cq.from_user.id, "order_done"), reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.message(Command("cancel"))
async def cancel_current_process(m: Message):
    ensure(m.from_user)
    PENDING_QUANTITY.pop(m.from_user.id, None)
    PENDING_TOPUP.pop(m.from_user.id, None)
    await m.answer(txt(m.from_user.id, "cancelled"), reply_markup=menu_reply_keyboard(m.from_user.id))

async def open_main_from_text(m: Message, callback_name: str):
    # Helper for reply keyboard navigation.
    fake = type("FakeCQ", (), {})()

@dp.message(F.text)
async def reply_keyboard_and_states(m: Message):
    ensure(m.from_user)
    if await block_if_banned(m):
        return
    text = (m.text or "").strip()
    l = lang(m.from_user.id)

    if text == "/cancel":
        PENDING_QUANTITY.pop(m.from_user.id, None)
        PENDING_TOPUP.pop(m.from_user.id, None)
        return await m.answer(txt(m.from_user.id, "cancelled"), reply_markup=menu_reply_keyboard(m.from_user.id))

    if m.from_user.id in PENDING_TOPUP:
        state = PENDING_TOPUP.pop(m.from_user.id)
        try:
            amount = float(text.replace(",", "."))
            if amount <= 0:
                raise ValueError
        except Exception:
            PENDING_TOPUP[m.from_user.id] = state
            return await m.answer(txt(m.from_user.id, "enter_amount"))
        expire_old_payment_requests()
        pid, expires = create_payment_request(m.from_user.id, m.from_user.username or "", amount=amount, method=state["method"])
        inv = invoice_message(state["method"], amount)
        await m.answer(inv, reply_markup=paid_only_keyboard(m.from_user.id, pid))
        if state["method"] == "bep20":
            await m.answer(USDT_BEP20_ADDRESS)
        await notify_admins(
            f"Top Up Request #{pid}\n\n"
            f"User ID: {m.from_user.id}\n"
            f"Username: @{m.from_user.username}\n"
            f"Method: {state['method']}\n"
            f"Amount: {amount:.2f} USDT"
        )
        return

    if m.from_user.id in PENDING_QUANTITY:
        state = PENDING_QUANTITY.pop(m.from_user.id)
        try:
            qty = int(text)
            if qty < 1 or qty > int(state["max"]):
                raise ValueError
        except Exception:
            PENDING_QUANTITY[m.from_user.id] = state
            return await m.answer(f"Please enter a quantity between 1 and {state['max']}.")
        item = get_item(state["cat_key"], state["pid"])
        if not item:
            return await m.answer("Product not found.", reply_markup=menu_reply_keyboard(m.from_user.id))
        u = user(m.from_user.id)
        balance = float(u["balance"]) if u else 0.0
        unit = float(item["price"] or 0.0)
        total = round(unit * qty, 2)
        final, code, percent = apply_discount(m.from_user.id, total)
        if balance <= 0 or balance < final:
            return await m.answer(txt(m.from_user.id, "need_balance"), reply_markup=menu_reply_keyboard(m.from_user.id))
        pname = pretty_product_label(state["cat_key"], item)
        with conn() as c:
            c.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (final, m.from_user.id))
            cur = c.execute(
                "INSERT INTO orders(user_id, username, product, price, status, gift_to, created_at) VALUES(?,?,?,?,?,?,?)",
                (m.from_user.id, m.from_user.username or "", f"{pname} x{qty}", final, "pending", "", datetime.utcnow().isoformat())
            )
            oid = cur.lastrowid
            c.commit()
        add_referral_commission(m.from_user.id, final)
        await notify_admins(
            f"New Order #{oid}\n\n"
            f"User ID: {m.from_user.id}\n"
            f"Username: @{m.from_user.username}\n"
            f"Product: {pname}\n"
            f"Quantity: {qty}\n"
            f"Amount: {final:.2f} USDT"
        )
        return await m.answer(txt(m.from_user.id, "order_done"), reply_markup=menu_reply_keyboard(m.from_user.id))

    # Reply keyboard navigation
    if text == T["products"][l] or text.lower().strip() in {"shop", "our products"}:
        return await m.answer(txt(m.from_user.id, "category_text"), reply_markup=kb_cats(m.from_user.id))
    if text == T["balance"][l] or text == T["topup"][l]:
        return await m.answer(balance_info_message(m.from_user.id), reply_markup=topup_methods_keyboard(m.from_user.id))
    if text == T["orders"][l]:
        with conn() as c:
            rows = c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (m.from_user.id,)).fetchall()
        if not rows:
            return await m.answer(txt(m.from_user.id, "no_orders"), reply_markup=menu_reply_keyboard(m.from_user.id))
        msg = "My Orders\n\n"
        for r in rows:
            msg += f"#{r['id']} | {r['product']}\nAmount: {r['price']:.2f} USDT\nStatus: {r['status']}\n\n"
        return await m.answer(msg, reply_markup=menu_reply_keyboard(m.from_user.id))
    if text == T["cart"][l]:
        with conn() as c:
            rows = c.execute("SELECT * FROM cart WHERE user_id=? ORDER BY id", (m.from_user.id,)).fetchall()
        if not rows:
            return await m.answer(txt(m.from_user.id, "empty_cart"), reply_markup=menu_reply_keyboard(m.from_user.id))
        msg = "Cart\n\n"
        total = 0.0
        for r in rows:
            item = get_item(r["cat_key"], r["product_id"])
            if item:
                total += float(item["price"] or 0.0)
                msg += f"{pretty_product_label(r['cat_key'], item)} - {price_text(item['price'])}\n"
        msg += f"\nTotal: {total:.2f} USDT"
        return await m.answer(msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [styled_button(text=T["confirm"][l], callback_data="checkout", style="success")],
            [styled_button(text=T["back"][l], callback_data="main", style="danger")]
        ]))
    if text == T["language"][l]:
        return await m.answer(T["choose_lang"][l], reply_markup=kb_lang())
    if text == T["support"][l]:
        return await m.answer(txt(m.from_user.id, "pay", wallet=USDT_BEP20_ADDRESS, bybit=BYBIT_ID, support=SUPPORT_USERNAME), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [styled_button(text=SUPPORT_USERNAME, url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}", style="success", icon_custom_emoji_id=CUSTOM_EMOJI["support"])],
            [styled_button(text=T["channel"][l], url=CHANNEL_URL, style="primary", icon_custom_emoji_id=CUSTOM_EMOJI["channel"])],
        ]))
    if text == T["profile"][l]:
        u = user(m.from_user.id)
        invited, earnings = referral_stats(m.from_user.id)
        b = float(u["balance"]) if u else 0.0
        return await m.answer(
            "Profile\n\n"
            f"ID: {m.from_user.id}\n"
            f"Username: @{m.from_user.username}\n"
            f"Balance: {b:.2f} USDT\n"
            f"Invited users: {invited}\n"
            f"Referral earnings: {earnings:.2f} USDT",
            reply_markup=menu_reply_keyboard(m.from_user.id)
        )
    if text == T["special_offers"][l]:
        return await m.answer("Special Offers\n\nHOT DEAL: Razer Gold and PUBG UC are available with trader prices.\nCoupon: WELCOME5", reply_markup=menu_reply_keyboard(m.from_user.id))
    if text == T["best_sellers"][l]:
        return await m.answer("Best Sellers\n\nRazer Gold\nPUBG UC\nSteam USA\nPlayStation USA\niTunes USA\nRoblox Gift Cards", reply_markup=menu_reply_keyboard(m.from_user.id))
    if text == T["favorites"][l]:
        with conn() as c:
            rows = c.execute("SELECT * FROM favorites WHERE user_id=?", (m.from_user.id,)).fetchall()
        if not rows:
            return await m.answer(txt(m.from_user.id, "empty_fav"), reply_markup=menu_reply_keyboard(m.from_user.id))
        msg = "Favorites\n\n"
        for r in rows:
            item = get_item(r["cat_key"], r["product_id"])
            if item:
                msg += f"{pretty_product_label(r['cat_key'], item)} - {price_text(item['price'])}\n"
        return await m.answer(msg, reply_markup=menu_reply_keyboard(m.from_user.id))
    if text == T["referrals"][l]:
        invited, earnings = referral_stats(m.from_user.id)
        me = await bot.get_me()
        ref_link = f"https://t.me/{me.username}?start=ref_{m.from_user.id}"
        return await m.answer(
            "Referral Program\n\n"
            f"Your referral link:\n{ref_link}\n\n"
            f"Invited users: {invited}\n"
            f"Referral earnings: {earnings:.2f} USDT",
            reply_markup=menu_reply_keyboard(m.from_user.id)
        )
    if text == T["channel"][l]:
        return await m.answer(CHANNEL_URL, reply_markup=menu_reply_keyboard(m.from_user.id))

    # Not a menu/state message: let the admin-forward handler below process it.
    content = m.text or m.caption or ""
    await notify_admins(
        f"User Message\n\n"
        f"ID: {m.from_user.id}\n"
        f"Username: @{m.from_user.username}\n"
        f"Name: {m.from_user.first_name}\n\n"
        f"Message:\n{content}"
    )

@dp.message()
async def forward_user_messages_to_admin(m: Message):
    ensure(m.from_user)
    if admin(m.from_user.id):
        return
    content = m.text or m.caption or ""
    if not content:
        if m.photo:
            content = "[Photo]"
        elif m.document:
            content = f"[Document] {m.document.file_name or ''}"
        elif m.sticker:
            content = "[Sticker]"
        elif m.video:
            content = "[Video]"
        elif m.voice:
            content = "[Voice]"
        else:
            content = "[Non-text message]"
    await notify_admins(
        f"User Message\n\n"
        f"ID: {m.from_user.id}\n"
        f"Username: @{m.from_user.username}\n"
        f"Name: {m.from_user.first_name}\n\n"
        f"Message:\n{content}"
    )

async def main():
    init_db()
    print(f"{BOT_NAME} started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
