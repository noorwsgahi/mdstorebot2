# MD STORE Telegram Bot

بوت متجر تيليجرام جاهز للاختبار يحتوي على:

- 3 لغات: Arabic / English / Russian
- متجر منتجات MD STORE
- محفظة رصيد لكل مستخدم
- إضافة رصيد من الأدمن
- حذف وتعديل الرصيد
- حد أدنى للطلب 50 USDT
- رسالة رصيد غير كافٍ إذا الرصيد 0
- إرسال الطلبات للأدمن
- دعم Telegram: @MD_SUPPORTT
- قناة رسمية: https://t.me/MD_WEBSITE
- دفع يدوي: USDT BEP20 و Bybit ID

## تشغيل البوت

```bash
pip install -r requirements.txt
python bot.py
```

## أوامر الأدمن

```text
/admin
/addbalance USER_ID AMOUNT
/removebalance USER_ID AMOUNT
/setbalance USER_ID AMOUNT
/check USER_ID
/orders
/broadcast MESSAGE
```

مثال:

```text
/addbalance 8491908169 50
```

## ملفات مهمة

- `.env` إعدادات البوت والتوكن والدفع.
- `products.json` المنتجات والأسعار.
- `bot.py` ملف البوت الرئيسي.
- `md_store_bot.db` ينشأ تلقائياً عند أول تشغيل.

