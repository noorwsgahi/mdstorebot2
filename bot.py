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
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
BOT_NAME = os.getenv("BOT_NAME", "MD STORE Global")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "@bot_MD_global")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/MD_WEBSITE")
BYBIT_ID = os.getenv("BYBIT_ID", "524739312")
USDT_BEP20_ADDRESS = os.getenv("USDT_BEP20_ADDRESS", "0xA2E0c2eC432953Dd2F832488a1EC061e6e761361")
MIN_ORDER = float(os.getenv("MIN_ORDER_USDT", "50"))

SPECIAL_MIN_ORDERS = {
    7781514279: 100.0,
    358930912: 100.0,
}

def get_min_order(user_id):
    return SPECIAL_MIN_ORDERS.get(user_id, MIN_ORDER)
DB = os.getenv("DATABASE_PATH", "md_store_bot.db")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "7504221023").replace(" ", "").split(",") if x.isdigit()}

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing in .env or Railway Variables")

PRODUCTS = json.loads(Path("products.json").read_text(encoding="utf-8"))

session = AiohttpSession()
bot = Bot(BOT_TOKEN, session=session)
dp = Dispatcher()

LANGS = {"ar": "العربية", "en": "English", "ru": "Русский"}

T = {
    "choose_lang": {
        "ar": "اختر اللغة:",
        "en": "Choose language:",
        "ru": "Выберите язык:",
    },
    "welcome": {
        "ar": "أهلاً بك في MD STORE\nمتجر البطاقات الرقمية للتجار والعملاء.\n\nاختر من القائمة:",
        "en": "Welcome to MD STORE\nDigital gift card marketplace.\n\nChoose from the menu:",
        "ru": "Добро пожаловать в MD STORE\nМагазин цифровых карт.\n\nВыберите раздел:",
    },
    "shop": {"ar": "المتجر", "en": "Shop", "ru": "Магазин"},
    "topup": {"ar": "شحن الرصيد", "en": "Top Up Balance", "ru": "Пополнить баланс"},
    "balance": {"ar": "الرصيد", "en": "Balance", "ru": "Баланс"},
    "cart": {"ar": "السلة", "en": "Cart", "ru": "Корзина"},
    "favorites": {"ar": "المفضلة", "en": "Favorites", "ru": "Избранное"},
    "orders": {"ar": "طلباتي", "en": "My Orders", "ru": "Мои заказы"},
    "latest": {"ar": "آخر عمليات الشراء", "en": "Latest Purchases", "ru": "Последние покупки"},
    "support": {"ar": "الدعم", "en": "Support", "ru": "Поддержка"},
    "faq": {"ar": "الأسئلة الشائعة", "en": "FAQ", "ru": "FAQ"},
    "referrals": {"ar": "الإحالات", "en": "Referrals", "ru": "Рефералы"},
    "copy_usdt": {"ar": "نسخ عنوان USDT", "en": "Copy USDT Address", "ru": "Скопировать USDT"},
    "channel": {"ar": "القناة الرسمية", "en": "Official Channel", "ru": "Официальный канал"},
    "language": {"ar": "اللغة", "en": "Language", "ru": "Язык"},
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

def iter_items(cat_key):
    items = PRODUCTS.get(cat_key, {}).get("items", [])
    normalized = []
    for item in items:
        if isinstance(item, dict):
            normalized.append({"id": str(item.get("id")), "label": str(item.get("label")), "price": item.get("price")})
        elif isinstance(item, (list, tuple)) and len(item) >= 3:
            normalized.append({"id": str(item[0]), "label": str(item[1]), "price": item[2]})
    return normalized

def get_item(cat_key, pid):
    for item in iter_items(cat_key):
        if item["id"] == pid:
            return item
    return None

def cat_name(cat_key, l):
    cat = PRODUCTS.get(cat_key, {})
    return cat.get(l, cat.get("en", cat_key))

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

def kb_lang():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=v, callback_data=f"lang:{k}")]
        for k, v in LANGS.items()
    ])

def kb_main(uid):
    l = lang(uid)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=T["shop"][l], callback_data="shop")],
        [InlineKeyboardButton(text=T["topup"][l], callback_data="topup"), InlineKeyboardButton(text=T["balance"][l], callback_data="balance")],
        [InlineKeyboardButton(text=T["cart"][l], callback_data="cart"), InlineKeyboardButton(text=T["favorites"][l], callback_data="favorites")],
        [InlineKeyboardButton(text=T["orders"][l], callback_data="orders"), InlineKeyboardButton(text=T["latest"][l], callback_data="latest")],
        [InlineKeyboardButton(text=T["support"][l], callback_data="support"), InlineKeyboardButton(text=T["language"][l], callback_data="choose_lang")],
        [InlineKeyboardButton(text=T["faq"][l], callback_data="faq"), InlineKeyboardButton(text=T["referrals"][l], callback_data="referrals")],
        [InlineKeyboardButton(text=T["channel"][l], url=CHANNEL_URL)],
    ])

def kb_cats(uid):
    l = lang(uid)
    rows = []
    for k, v in PRODUCTS.items():
        rows.append([InlineKeyboardButton(text=v.get(l, v.get("en", k)), callback_data=f"cat:{k}")])
    rows.append([InlineKeyboardButton(text=T["back"][l], callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_items(uid, cat_key):
    l = lang(uid)
    rows = []
    for item in iter_items(cat_key):
        rows.append([InlineKeyboardButton(text=f"{item['label']} - {price_text(item['price'])}", callback_data=f"view:{cat_key}:{item['id']}")])
    rows.append([InlineKeyboardButton(text=T["back"][l], callback_data="shop")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_product_actions(uid, cat_key, pid):
    l = lang(uid)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=T["buy_now"][l], callback_data=f"buy:{cat_key}:{pid}")],
        [InlineKeyboardButton(text=T["add_cart"][l], callback_data=f"addcart:{cat_key}:{pid}")],
        [InlineKeyboardButton(text=T["add_fav"][l], callback_data=f"addfav:{cat_key}:{pid}")],
        [InlineKeyboardButton(text=T["gift"][l], callback_data=f"gift:{cat_key}:{pid}")],
        [InlineKeyboardButton(text=T["back"][l], callback_data=f"cat:{cat_key}")],
    ])

def payment_keyboard(uid):
    l = lang(uid)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=T["copy_usdt"][l], callback_data="copy_usdt")],
        [InlineKeyboardButton(text=T["i_paid"][l], callback_data="paid")],
        [InlineKeyboardButton(text=SUPPORT_USERNAME, url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}")],
        [InlineKeyboardButton(text=T["back"][l], callback_data="main")],
    ])

def main_back_keyboard(uid):
    l = lang(uid)
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=T["main"][l], callback_data="main")]])

async def notify_admins(text):
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, text)
        except Exception:
            pass

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

    await m.answer(txt(m.from_user.id, "welcome"), reply_markup=kb_main(m.from_user.id))

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
        "/discount24"
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

@dp.callback_query(F.data.startswith("lang:"))
async def cb_lang(cq: CallbackQuery):
    ensure(cq.from_user)
    set_lang(cq.from_user.id, cq.data.split(":")[1])
    await cq.message.edit_text(txt(cq.from_user.id, "welcome"), reply_markup=kb_main(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "choose_lang")
async def cb_choose_lang(cq: CallbackQuery):
    await cq.message.edit_text(T["choose_lang"][lang(cq.from_user.id)], reply_markup=kb_lang())
    await cq.answer()

@dp.callback_query(F.data == "main")
async def cb_main(cq: CallbackQuery):
    await cq.message.edit_text(txt(cq.from_user.id, "welcome"), reply_markup=kb_main(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "shop")
async def cb_shop(cq: CallbackQuery):
    await cq.message.edit_text(txt(cq.from_user.id, "category_text"), reply_markup=kb_cats(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "topup")
async def cb_topup(cq: CallbackQuery):
    text = txt(cq.from_user.id, "pay", wallet=USDT_BEP20_ADDRESS, bybit=BYBIT_ID, support=SUPPORT_USERNAME)
    await cq.message.edit_text(text, reply_markup=payment_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "paid")
async def cb_paid(cq: CallbackQuery):
    ensure(cq.from_user)
    with conn() as c:
        cur = c.execute(
            "INSERT INTO payment_requests(user_id, username, status, created_at) VALUES(?,?,?,?)",
            (cq.from_user.id, cq.from_user.username or "", "pending", datetime.utcnow().isoformat())
        )
        pid = cur.lastrowid
        c.commit()
    await notify_admins(
        f"Payment Notice #{pid}\n\nUser ID: {cq.from_user.id}\nUsername: @{cq.from_user.username}\nStatus: Pending\n\nAsk the user for screenshot/hash if needed."
    )
    await cq.message.edit_text(txt(cq.from_user.id, "paid_sent"), reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()


@dp.callback_query(F.data == "copy_usdt")
async def cb_copy_usdt(cq: CallbackQuery):
    # Telegram bots cannot copy text directly to the user's clipboard.
    # This sends the wallet address alone in a separate message so the user can copy it easily.
    await cq.answer("USDT address sent below")
    await cq.message.answer(
        f"USDT BEP20 Address:\n\n`{USDT_BEP20_ADDRESS}`\n\nTap and hold the address to copy it.",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "faq")
async def cb_faq(cq: CallbackQuery):
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
    await cq.message.edit_text(text, reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "referrals")
async def cb_referrals(cq: CallbackQuery):
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
    await cq.message.edit_text(text, reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "balance")
async def cb_balance(cq: CallbackQuery):
    u = user(cq.from_user.id)
    b = float(u["balance"]) if u else 0.0
    code, discount = get_discount(cq.from_user.id)
    text = txt(cq.from_user.id, "wallet", balance=b)
    if code:
        text += f"\nCoupon: {code} ({discount:.0f}%)"
    text += "\n\n" + txt(cq.from_user.id, "coupon_help")
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=T["topup"][lang(cq.from_user.id)], callback_data="topup")],
        [InlineKeyboardButton(text=T["back"][lang(cq.from_user.id)], callback_data="main")]
    ]))
    await cq.answer()

@dp.callback_query(F.data == "support")
async def cb_support(cq: CallbackQuery):
    text = txt(cq.from_user.id, "pay", wallet=USDT_BEP20_ADDRESS, bybit=BYBIT_ID, support=SUPPORT_USERNAME)
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=SUPPORT_USERNAME, url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}")],
        [InlineKeyboardButton(text=T["channel"][lang(cq.from_user.id)], url=CHANNEL_URL)],
        [InlineKeyboardButton(text=T["back"][lang(cq.from_user.id)], callback_data="main")]
    ]))
    await cq.answer()

@dp.callback_query(F.data == "orders")
async def cb_orders(cq: CallbackQuery):
    with conn() as c:
        rows = c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (cq.from_user.id,)).fetchall()
    if not rows:
        text = txt(cq.from_user.id, "no_orders")
    else:
        text = "My Orders\n\n"
        for r in rows:
            text += f"#{r['id']} | {r['product']}\nAmount: {r['price']:.2f} USDT\nStatus: {r['status']}\n\n"
    await cq.message.edit_text(text, reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data == "latest")
async def cb_latest(cq: CallbackQuery):
    with conn() as c:
        rows = c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 10").fetchall()
    if not rows:
        text = txt(cq.from_user.id, "no_latest")
    else:
        text = "Latest Purchases\n\n"
        for r in rows:
            text += f"Someone purchased {r['product']}\nAmount: {r['price']:.2f} USDT\nStatus: {r['status']}\n\n"
    await cq.message.edit_text(text, reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data.startswith("cat:"))
async def cb_cat(cq: CallbackQuery):
    cat_key = cq.data.split(":")[1]
    await cq.message.edit_text(cat_name(cat_key, lang(cq.from_user.id)), reply_markup=kb_items(cq.from_user.id, cat_key))
    await cq.answer()

@dp.callback_query(F.data.startswith("view:"))
async def cb_view(cq: CallbackQuery):
    _, cat_key, pid = cq.data.split(":")
    item = get_item(cat_key, pid)
    if not item:
        return await cq.answer("Product not found", show_alert=True)
    l = lang(cq.from_user.id)
    text = f"{product_name(cat_key, item, l)}\n\nPrice: {price_text(item['price'])}\nValidity: 1 Year\nDelivery: Instant"
    await cq.message.edit_text(text, reply_markup=kb_product_actions(cq.from_user.id, cat_key, pid))
    await cq.answer()

@dp.callback_query(F.data.startswith("addcart:"))
async def cb_addcart(cq: CallbackQuery):
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
    l = lang(cq.from_user.id)
    with conn() as c:
        rows = c.execute("SELECT * FROM favorites WHERE user_id=? ORDER BY created_at DESC", (cq.from_user.id,)).fetchall()
    if not rows:
        return await cq.message.edit_text(txt(cq.from_user.id, "empty_fav"), reply_markup=main_back_keyboard(cq.from_user.id))
    buttons = []
    for r in rows:
        item = get_item(r["cat_key"], r["product_id"])
        if item:
            buttons.append([InlineKeyboardButton(text=product_name(r["cat_key"], item, l), callback_data=f"view:{r['cat_key']}:{r['product_id']}")])
    buttons.append([InlineKeyboardButton(text=T["back"][l], callback_data="main")])
    await cq.message.edit_text(T["favorites"][l], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await cq.answer()

@dp.callback_query(F.data == "cart")
async def cb_cart(cq: CallbackQuery):
    l = lang(cq.from_user.id)
    with conn() as c:
        rows = c.execute("SELECT * FROM cart WHERE user_id=? ORDER BY id DESC", (cq.from_user.id,)).fetchall()
    if not rows:
        return await cq.message.edit_text(txt(cq.from_user.id, "empty_cart"), reply_markup=main_back_keyboard(cq.from_user.id))
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
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=T["checkout"][l], callback_data="checkout")],
        [InlineKeyboardButton(text=T["clear_cart"][l], callback_data="clearcart")],
        [InlineKeyboardButton(text=T["back"][l], callback_data="main")]
    ]))
    await cq.answer()

@dp.callback_query(F.data == "clearcart")
async def cb_clearcart(cq: CallbackQuery):
    with conn() as c:
        c.execute("DELETE FROM cart WHERE user_id=?", (cq.from_user.id,))
        c.commit()
    await cq.message.edit_text(txt(cq.from_user.id, "empty_cart"), reply_markup=main_back_keyboard(cq.from_user.id))
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
    u = user(cq.from_user.id)
    balance = float(u["balance"]) if u else 0.0
    l = lang(cq.from_user.id)

    if balance <= 0:
        return await cq.message.edit_text(txt(cq.from_user.id, "need_balance"), reply_markup=main_back_keyboard(cq.from_user.id))
    if balance < get_min_order(cq.from_user.id):
        return await cq.message.edit_text(txt(cq.from_user.id, "min_order", min_order=get_min_order(cq.from_user.id)), reply_markup=main_back_keyboard(cq.from_user.id))

    with conn() as c:
        rows = c.execute("SELECT * FROM cart WHERE user_id=? ORDER BY id", (cq.from_user.id,)).fetchall()

    if not rows:
        return await cq.message.edit_text(txt(cq.from_user.id, "empty_cart"), reply_markup=main_back_keyboard(cq.from_user.id))

    total = 0.0
    names = []
    for r in rows:
        item = get_item(r["cat_key"], r["product_id"])
        if item:
            total += float(item["price"] or 0.0)
            names.append(product_name(r["cat_key"], item, l))
    final, code, percent = apply_discount(cq.from_user.id, total)

    if balance < final:
        return await cq.message.edit_text(txt(cq.from_user.id, "need_balance"), reply_markup=main_back_keyboard(cq.from_user.id))

    await create_order(cq, "Cart: " + ", ".join(names), final)
    with conn() as c:
        c.execute("DELETE FROM cart WHERE user_id=?", (cq.from_user.id,))
        c.commit()

    await cq.message.edit_text(txt(cq.from_user.id, "order_done"), reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data.startswith("buy:"))
async def cb_buy(cq: CallbackQuery):
    _, cat_key, pid = cq.data.split(":")
    item = get_item(cat_key, pid)
    if not item:
        return await cq.answer("Product not found", show_alert=True)

    u = user(cq.from_user.id)
    b = float(u["balance"]) if u else 0.0
    l = lang(cq.from_user.id)

    if b <= 0:
        return await cq.message.edit_text(txt(cq.from_user.id, "need_balance"), reply_markup=main_back_keyboard(cq.from_user.id))
    if b < get_min_order(cq.from_user.id):
        return await cq.message.edit_text(txt(cq.from_user.id, "min_order", min_order=get_min_order(cq.from_user.id)), reply_markup=main_back_keyboard(cq.from_user.id))

    price_val = float(item["price"] or 0.0)
    final, code, percent = apply_discount(cq.from_user.id, price_val)

    if b < final:
        return await cq.message.edit_text(txt(cq.from_user.id, "need_balance"), reply_markup=main_back_keyboard(cq.from_user.id))

    pname = product_name(cat_key, item, l)
    price_line = f"{final:.2f} USDT"
    if code:
        price_line += f"\nCoupon: {code} - {percent:.0f}%"

    text = f"{T['confirm'][l]}\n\nProduct: {pname}\nPrice: {price_line}\nBalance: {b:.2f} USDT"
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=T["confirm"][l], callback_data=f"confirm:{cat_key}:{pid}")],
        [InlineKeyboardButton(text=T["back"][l], callback_data=f"view:{cat_key}:{pid}")]
    ]))
    await cq.answer()

@dp.callback_query(F.data.startswith("gift:"))
async def cb_gift(cq: CallbackQuery):
    _, cat_key, pid = cq.data.split(":")
    item = get_item(cat_key, pid)
    if not item:
        return await cq.answer("Product not found", show_alert=True)
    l = lang(cq.from_user.id)
    pname = product_name(cat_key, item, l)
    await cq.message.edit_text(
        f"{T['gift'][l]}\n\n{pname}\n\nTo send this as a gift, confirm the purchase then send the recipient details to support.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=T["confirm"][l], callback_data=f"confirmgift:{cat_key}:{pid}")],
            [InlineKeyboardButton(text=T["back"][l], callback_data=f"view:{cat_key}:{pid}")]
        ])
    )
    await cq.answer()

@dp.callback_query(F.data.startswith("confirmgift:"))
async def cb_confirm_gift(cq: CallbackQuery):
    _, cat_key, pid = cq.data.split(":")
    item = get_item(cat_key, pid)
    if not item:
        return await cq.answer("Product not found", show_alert=True)
    u = user(cq.from_user.id)
    b = float(u["balance"]) if u else 0.0
    if b <= 0:
        return await cq.message.edit_text(txt(cq.from_user.id, "need_balance"), reply_markup=main_back_keyboard(cq.from_user.id))
    if b < get_min_order(cq.from_user.id):
        return await cq.message.edit_text(txt(cq.from_user.id, "min_order", min_order=get_min_order(cq.from_user.id)), reply_markup=main_back_keyboard(cq.from_user.id))
    price_val = float(item["price"] or 0.0)
    final, code, percent = apply_discount(cq.from_user.id, price_val)
    if b < final:
        return await cq.message.edit_text(txt(cq.from_user.id, "need_balance"), reply_markup=main_back_keyboard(cq.from_user.id))
    pname = product_name(cat_key, item, lang(cq.from_user.id))
    await create_order(cq, pname, final, gift_to="Recipient details will be sent to support")
    await cq.message.edit_text(txt(cq.from_user.id, "order_done"), reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

@dp.callback_query(F.data.startswith("confirm:"))
async def cb_confirm(cq: CallbackQuery):
    _, cat_key, pid = cq.data.split(":")
    item = get_item(cat_key, pid)
    if not item:
        return await cq.answer("Product not found", show_alert=True)

    u = user(cq.from_user.id)
    b = float(u["balance"]) if u else 0.0

    if b <= 0:
        return await cq.message.edit_text(txt(cq.from_user.id, "need_balance"), reply_markup=main_back_keyboard(cq.from_user.id))
    if b < get_min_order(cq.from_user.id):
        return await cq.answer(f"Minimum order is {get_min_order(cq.from_user.id):.0f} USDT", show_alert=True)

    price_val = float(item["price"] or 0.0)
    final, code, percent = apply_discount(cq.from_user.id, price_val)

    if b < final:
        return await cq.answer("Not enough balance", show_alert=True)

    pname = product_name(cat_key, item, lang(cq.from_user.id))
    await create_order(cq, pname, final)
    await cq.message.edit_text(txt(cq.from_user.id, "order_done"), reply_markup=main_back_keyboard(cq.from_user.id))
    await cq.answer()

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
