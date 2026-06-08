import asyncio, json, os, sqlite3
from datetime import datetime
import ssl
from aiogram.client.session.aiohttp import AiohttpSession
from pathlib import Path
from typing import Optional
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN=os.getenv('BOT_TOKEN','').strip()
BOT_NAME=os.getenv('BOT_NAME','MD STORE')
SUPPORT_USERNAME=os.getenv('SUPPORT_USERNAME','@MD_SUPPORTT')
CHANNEL_URL=os.getenv('CHANNEL_URL','https://t.me/MD_WEBSITE')
BYBIT_ID=os.getenv('BYBIT_ID','524739312')
USDT_BEP20_ADDRESS=os.getenv('USDT_BEP20_ADDRESS','0x4e1e1c05CdD0a0De3d02531f81aF46d5fF63d6AC')
MIN_ORDER=float(os.getenv('MIN_ORDER_USDT','50'))
DB=os.getenv('DATABASE_PATH','md_store_bot.db')
ADMIN_IDS={int(x) for x in os.getenv('ADMIN_IDS','').replace(' ','').split(',') if x.isdigit()}
if not BOT_TOKEN: raise RuntimeError('BOT_TOKEN missing in .env')
PRODUCTS=json.loads(Path('products.json').read_text(encoding='utf-8'))
LANGS={'ar':'العربية','en':'English','ru':'Русский'}
T={
 'choose_lang':{'ar':'اختر اللغة:','en':'Choose language:','ru':'Выберите язык:'},
 'welcome':{'ar':'أهلاً بك في MD STORE\nمتجر البطاقات الرقمية للتجار والعملاء.','en':'Welcome to MD STORE\nDigital gift card marketplace.','ru':'Добро пожаловать в MD STORE\nМагазин цифровых карт.'},
 'shop':{'ar':'المتجر','en':'Shop','ru':'Магазин'}, 'balance':{'ar':'الرصيد','en':'Balance','ru':'Баланс'},
 'orders':{'ar':'طلباتي','en':'My Orders','ru':'Мои заказы'}, 'support':{'ar':'الدعم','en':'Support','ru':'Поддержка'},
 'channel':{'ar':'القناة الرسمية','en':'Official Channel','ru':'Официальный канал'}, 'language':{'ar':'اللغة','en':'Language','ru':'Язык'},
 'back':{'ar':'رجوع','en':'Back','ru':'Назад'}, 'main':{'ar':'القائمة الرئيسية','en':'Main Menu','ru':'Главное меню'},
 'category_text':{'ar':'اختر المنتج:','en':'Choose product:','ru':'Выберите товар:'},
 'wallet':{'ar':'رصيدك الحالي: {balance:.2f} USDT','en':'Your balance: {balance:.2f} USDT','ru':'Ваш баланс: {balance:.2f} USDT'},
 'need_balance':{'ar':'رصيدك غير كافي لإجراء عمليات الشراء.\nيرجى شحن رصيد حسابك أولاً.','en':'Your balance is not enough to make purchases.\nPlease top up your account first.','ru':'Недостаточно средств для покупки.\nСначала пополните баланс.'},
 'min_order':{'ar':'الحد الأدنى للطلب هو 50 USDT.','en':'The minimum order amount is 50 USDT.','ru':'Минимальная сумма заказа — 50 USDT.'},
 'pay':{'ar':'لشحن الرصيد، أرسل الدفع ثم تواصل مع الدعم وأرسل لقطة شاشة أو رابط/Hash الدفع.\n\nUSDT BEP20:\n{wallet}\n\nBybit ID:\n{bybit}\n\nالدعم: {support}', 'en':'To top up balance, send payment then contact support with screenshot or payment hash/link.\n\nUSDT BEP20:\n{wallet}\n\nBybit ID:\n{bybit}\n\nSupport: {support}', 'ru':'Для пополнения баланса отправьте оплату и свяжитесь с поддержкой со скриншотом или hash/ссылкой.\n\nUSDT BEP20:\n{wallet}\n\nBybit ID:\n{bybit}\n\nПоддержка: {support}'},
 'confirm':{'ar':'تأكيد الشراء','en':'Confirm Purchase','ru':'Подтвердить покупку'},
 'order_done':{'ar':'تم إنشاء طلبك بنجاح. سيتم التواصل معك للتسليم.','en':'Your order has been created. You will be contacted for delivery.','ru':'Заказ создан. С вами свяжутся для доставки.'},
 'no_orders':{'ar':'لا توجد طلبات حالياً.','en':'No orders yet.','ru':'Заказов пока нет.'},
 'admin_only':{'ar':'هذا الأمر للأدمن فقط.','en':'This command is for admin only.','ru':'Эта команда только для администратора.'}
}
bot=Bot(BOT_TOKEN); dp=Dispatcher()

def conn():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    with conn() as c:
        c.execute('CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, lang TEXT DEFAULT "en", balance REAL DEFAULT 0, created_at TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, product TEXT, price REAL, status TEXT DEFAULT "pending", created_at TEXT)')
        c.commit()

def ensure(u):
    with conn() as c:
        r=c.execute('SELECT user_id FROM users WHERE user_id=?',(u.id,)).fetchone()
        if not r: c.execute('INSERT INTO users VALUES(?,?,?,?,?,?)',(u.id,u.username or '',u.first_name or '', 'en',0.0,datetime.utcnow().isoformat()))
        else: c.execute('UPDATE users SET username=?, first_name=? WHERE user_id=?',(u.username or '',u.first_name or '',u.id))
        c.commit()

def user(uid):
    with conn() as c: return c.execute('SELECT * FROM users WHERE user_id=?',(uid,)).fetchone()

def lang(uid):
    u=user(uid); return (u['lang'] if u and u['lang'] else 'en')

def txt(uid,key,**kw): return T[key][lang(uid)].format(**kw)
def admin(uid): return uid in ADMIN_IDS

def set_lang(uid,l):
    with conn() as c: c.execute('UPDATE users SET lang=? WHERE user_id=?',(l,uid)); c.commit()

def add_balance(uid,amount):
    with conn() as c:
        c.execute('INSERT OR IGNORE INTO users(user_id,username,first_name,lang,balance,created_at) VALUES(?,?,?,?,?,?)',(uid,'','','en',0.0,datetime.utcnow().isoformat()))
        c.execute('UPDATE users SET balance=balance+? WHERE user_id=?',(amount,uid)); c.commit()

def set_balance(uid,amount):
    with conn() as c: c.execute('UPDATE users SET balance=? WHERE user_id=?',(amount,uid)); c.commit()

def remove_balance(uid,amount):
    with conn() as c: c.execute('UPDATE users SET balance=MAX(balance-?,0) WHERE user_id=?',(amount,uid)); c.commit()

def kb_lang(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=v, callback_data=f'lang:{k}')] for k,v in LANGS.items()])
def kb_main(uid):
    l=lang(uid)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=T['shop'][l], callback_data='shop')],
        [InlineKeyboardButton(text=T['balance'][l], callback_data='balance'), InlineKeyboardButton(text=T['orders'][l], callback_data='orders')],
        [InlineKeyboardButton(text=T['support'][l], callback_data='support'), InlineKeyboardButton(text=T['language'][l], callback_data='choose_lang')],
        [InlineKeyboardButton(text=T['channel'][l], url=CHANNEL_URL)]])
def kb_cats(uid):
    l=lang(uid); rows=[]
    for k,v in PRODUCTS.items(): rows.append([InlineKeyboardButton(text=v.get(l,v['en']), callback_data=f'cat:{k}')])
    rows.append([InlineKeyboardButton(text=T['back'][l], callback_data='main')]); return InlineKeyboardMarkup(inline_keyboard=rows)
def kb_items(uid,cat):
    l=lang(uid); rows=[]
    for pid,label,price in PRODUCTS[cat]['items']:
        rows.append([InlineKeyboardButton(text=f"{label} - {'Available' if price is None else f'{price:.2f} USDT'}", callback_data=f'buy:{cat}:{pid}')])
    rows.append([InlineKeyboardButton(text=T['back'][l], callback_data='shop')]); return InlineKeyboardMarkup(inline_keyboard=rows)
def get_item(cat,pid):
    for item in PRODUCTS.get(cat,{}).get('items',[]):
        if item[0]==pid: return item
    return None

@dp.message(CommandStart())
async def start(m:Message):
    ensure(m.from_user); await m.answer(T['choose_lang']['en'], reply_markup=kb_lang())
@dp.message(Command('admin'))
async def ap(m:Message):
    if not admin(m.from_user.id): return await m.answer(T['admin_only']['en'])
    await m.answer('MD STORE Admin Panel\n\n/addbalance USER_ID AMOUNT\n/removebalance USER_ID AMOUNT\n/setbalance USER_ID AMOUNT\n/check USER_ID\n/orders\n/broadcast MESSAGE')
@dp.message(Command('addbalance'))
async def cadd(m:Message):
    if not admin(m.from_user.id): return await m.answer(T['admin_only']['en'])
    p=m.text.split();
    if len(p)!=3: return await m.answer('Usage: /addbalance USER_ID AMOUNT')
    try:
        uid=int(p[1]); amount=float(p[2]); add_balance(uid,amount); await m.answer(f'Added {amount:.2f} USDT to {uid}')
        try: await bot.send_message(uid,f'Your balance has been topped up by {amount:.2f} USDT.')
        except Exception: pass
    except Exception: await m.answer('Invalid input')
@dp.message(Command('removebalance'))
async def crem(m:Message):
    if not admin(m.from_user.id): return await m.answer(T['admin_only']['en'])
    p=m.text.split();
    if len(p)!=3: return await m.answer('Usage: /removebalance USER_ID AMOUNT')
    try: remove_balance(int(p[1]),float(p[2])); await m.answer('Balance removed.')
    except Exception: await m.answer('Invalid input')
@dp.message(Command('setbalance'))
async def cset(m:Message):
    if not admin(m.from_user.id): return await m.answer(T['admin_only']['en'])
    p=m.text.split();
    if len(p)!=3: return await m.answer('Usage: /setbalance USER_ID AMOUNT')
    try: add_balance(int(p[1]),0); set_balance(int(p[1]),float(p[2])); await m.answer('Balance set.')
    except Exception: await m.answer('Invalid input')
@dp.message(Command('check'))
async def check(m:Message):
    if not admin(m.from_user.id): return await m.answer(T['admin_only']['en'])
    p=m.text.split();
    if len(p)!=2: return await m.answer('Usage: /check USER_ID')
    u=user(int(p[1])) if p[1].isdigit() else None
    await m.answer('User not found.' if not u else f"ID: {u['user_id']}\nUsername: @{u['username']}\nBalance: {u['balance']:.2f} USDT\nLang: {u['lang']}")
@dp.message(Command('orders'))
async def admin_orders(m:Message):
    if not admin(m.from_user.id): return await m.answer(T['admin_only']['en'])
    with conn() as c: rows=c.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 20').fetchall()
    await m.answer('No orders.' if not rows else '\n'.join([f"#{r['id']} | {r['user_id']} | {r['product']} | {r['price']:.2f} USDT | {r['status']}" for r in rows]))
@dp.message(Command('broadcast'))
async def broadcast(m:Message):
    if not admin(m.from_user.id): return await m.answer(T['admin_only']['en'])
    msg=m.text.replace('/broadcast','',1).strip()
    if not msg: return await m.answer('Usage: /broadcast MESSAGE')
    with conn() as c: users=c.execute('SELECT user_id FROM users').fetchall()
    sent=0
    for u in users:
        try: await bot.send_message(u['user_id'],msg); sent+=1
        except Exception: pass
    await m.answer(f'Broadcast sent to {sent} users.')
@dp.callback_query(F.data.startswith('lang:'))
async def langcb(cq:CallbackQuery):
    ensure(cq.from_user); set_lang(cq.from_user.id,cq.data.split(':')[1]); await cq.message.edit_text(txt(cq.from_user.id,'welcome'), reply_markup=kb_main(cq.from_user.id)); await cq.answer()
@dp.callback_query(F.data=='choose_lang')
async def choose(cq:CallbackQuery): await cq.message.edit_text(T['choose_lang'][lang(cq.from_user.id)], reply_markup=kb_lang()); await cq.answer()
@dp.callback_query(F.data=='main')
async def maincb(cq:CallbackQuery): await cq.message.edit_text(txt(cq.from_user.id,'welcome'), reply_markup=kb_main(cq.from_user.id)); await cq.answer()
@dp.callback_query(F.data=='shop')
async def shop(cq:CallbackQuery): await cq.message.edit_text(txt(cq.from_user.id,'category_text'), reply_markup=kb_cats(cq.from_user.id)); await cq.answer()
@dp.callback_query(F.data=='balance')
async def balance(cq:CallbackQuery):
    u=user(cq.from_user.id); b=float(u['balance']) if u else 0.0
    l=lang(cq.from_user.id); text=txt(cq.from_user.id,'wallet',balance=b)+'\n\n'+txt(cq.from_user.id,'pay',wallet=USDT_BEP20_ADDRESS,bybit=BYBIT_ID,support=SUPPORT_USERNAME)
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=SUPPORT_USERNAME,url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}")],[InlineKeyboardButton(text=T['back'][l],callback_data='main')]])); await cq.answer()
@dp.callback_query(F.data=='support')
async def support(cq:CallbackQuery):
    l=lang(cq.from_user.id); text=txt(cq.from_user.id,'pay',wallet=USDT_BEP20_ADDRESS,bybit=BYBIT_ID,support=SUPPORT_USERNAME)
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=SUPPORT_USERNAME,url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}")],[InlineKeyboardButton(text=T['channel'][l],url=CHANNEL_URL)],[InlineKeyboardButton(text=T['back'][l],callback_data='main')]])); await cq.answer()
@dp.callback_query(F.data=='orders')
async def orders(cq:CallbackQuery):
    with conn() as c: rows=c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10',(cq.from_user.id,)).fetchall()
    text=txt(cq.from_user.id,'no_orders') if not rows else '\n'.join([f"#{r['id']} | {r['product']} | {r['price']:.2f} USDT | {r['status']}" for r in rows])
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=T['back'][lang(cq.from_user.id)],callback_data='main')]])); await cq.answer()
@dp.callback_query(F.data.startswith('cat:'))
async def cat(cq:CallbackQuery):
    catkey=cq.data.split(':')[1]; l=lang(cq.from_user.id); await cq.message.edit_text(PRODUCTS[catkey].get(l,PRODUCTS[catkey]['en']), reply_markup=kb_items(cq.from_user.id,catkey)); await cq.answer()
@dp.callback_query(F.data.startswith('buy:'))
async def buy(cq:CallbackQuery):
    _,catkey,pid=cq.data.split(':'); item=get_item(catkey,pid); u=user(cq.from_user.id); b=float(u['balance']) if u else 0.0; l=lang(cq.from_user.id)
    if b<=0: return await cq.message.edit_text(txt(cq.from_user.id,'need_balance'), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=T['balance'][l],callback_data='balance')],[InlineKeyboardButton(text=T['back'][l],callback_data=f'cat:{catkey}')]]))
    if b<MIN_ORDER: return await cq.message.edit_text(txt(cq.from_user.id,'min_order'), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=T['balance'][l],callback_data='balance')],[InlineKeyboardButton(text=T['back'][l],callback_data=f'cat:{catkey}')]]))
    product_name=f"{PRODUCTS[catkey].get(l,PRODUCTS[catkey]['en'])} {item[1]}"; price='Available' if item[2] is None else f'{float(item[2]):.2f} USDT'
    text=f"{T['confirm'][l]}\n\n{product_name}\nPrice: {price}\nBalance: {b:.2f} USDT"
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=T['confirm'][l],callback_data=f'confirm:{catkey}:{pid}')],[InlineKeyboardButton(text=T['back'][l],callback_data=f'cat:{catkey}')]])); await cq.answer()
@dp.callback_query(F.data.startswith('confirm:'))
async def confirm(cq:CallbackQuery):
    _,catkey,pid=cq.data.split(':'); item=get_item(catkey,pid); u=user(cq.from_user.id); b=float(u['balance']) if u else 0.0; price=float(item[2] or 0.0); l=lang(cq.from_user.id)
    if b<MIN_ORDER: return await cq.answer('Minimum order is 50 USDT', show_alert=True)
    if price and b<price: return await cq.answer('Not enough balance', show_alert=True)
    product_name=f"{PRODUCTS[catkey].get(l,PRODUCTS[catkey]['en'])} {item[1]}"
    with conn() as c:
        if price: c.execute('UPDATE users SET balance=balance-? WHERE user_id=?',(price,cq.from_user.id))
        cur=c.execute('INSERT INTO orders(user_id,username,product,price,status,created_at) VALUES(?,?,?,?,?,?)',(cq.from_user.id,cq.from_user.username or '',product_name,price,'pending',datetime.utcnow().isoformat()))
        oid=cur.lastrowid; c.commit()
    admin_text=f"New Order #{oid}\nUser ID: {cq.from_user.id}\nUsername: @{cq.from_user.username}\nProduct: {product_name}\nPrice: {price:.2f} USDT\nBalance before: {b:.2f} USDT"
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, admin_text)
        except Exception:
            pass

    await cq.message.edit_text(
        txt(cq.from_user.id, 'order_done'),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=T['orders'][l], callback_data='orders')],
            [InlineKeyboardButton(text=T['main'][l], callback_data='main')]
        ])
    )
    await cq.answer()


async def main():
    init_db()
    print(f'{BOT_NAME} started')
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
