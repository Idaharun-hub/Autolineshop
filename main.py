import os
import json
import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import uvicorn

# =============================================
# SOZLAMALAR
# =============================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8797119011:AAE4SjwfZbim9KOKj0OA6XZU3hO_i5aVw_s")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://autolineshop-production.up.railway.app")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================
# MAHSULOTLAR
# =============================================
PRODUCTS = [
    {"id": 1, "name_uz": "SCHOLL S17+ Poliroval Pasta 250ml", "name_ru": "Полировальная паста SCHOLL S17+ 250ml", "price": 145000, "wholesale_price": 120000, "category": "poliroval", "brand": "SCHOLL", "stock": 50, "image_url": "", "description_uz": "Professional poliroval pasta. Chuqur tirnalishlarni olib tashlaydi.", "description_ru": "Профессиональная полировальная паста. Удаляет глубокие царапины."},
    {"id": 2, "name_uz": "SCHOLL S3 Poliroval Pasta 1kg", "name_ru": "Полировальная паста SCHOLL S3 1kg", "price": 380000, "wholesale_price": 320000, "category": "poliroval", "brand": "SCHOLL", "stock": 30, "image_url": "", "description_uz": "Og'ir ishlar uchun kuchli pasta.", "description_ru": "Мощная паста для тяжелых работ."},
    {"id": 3, "name_uz": "FLEX PE 14-2 150 Poliroval Mashina", "name_ru": "Полировальная машина FLEX PE 14-2 150", "price": 3200000, "wholesale_price": 2800000, "category": "asboblar", "brand": "FLEX", "stock": 10, "image_url": "", "description_uz": "Professional poliroval mashina. 1400W quvvat.", "description_ru": "Профессиональная полировальная машина. Мощность 1400W."},
    {"id": 4, "name_uz": "FLEX XFE 7-15 150 Ekssentrik Mashina", "name_ru": "Эксцентриковая машина FLEX XFE 7-15 150", "price": 2800000, "wholesale_price": 2400000, "category": "asboblar", "brand": "FLEX", "stock": 8, "image_url": "", "description_uz": "Ekssentrik poliroval mashina. Yangi boshlovchilar uchun ideal.", "description_ru": "Эксцентриковая полировальная машина. Идеальна для новичков."},
    {"id": 5, "name_uz": "WHOOPSIE Crazy 100 Suv itaruvchi to'plam", "name_ru": "Набор WHOOPSIE Crazy 100 водоотталкивающий", "price": 89000, "wholesale_price": 72000, "category": "deteyling", "brand": "WHOOPSIE", "stock": 40, "image_url": "", "description_uz": "Shisha uchun suv itaruvchi qoplama to'plami.", "description_ru": "Набор водоотталкивающего покрытия для стекол."},
    {"id": 6, "name_uz": "OOPSY Crazy 102 Anti-Yomg'ir 50ml", "name_ru": "OOPSY Crazy 102 Антидождь 50ml", "price": 65000, "wholesale_price": 52000, "category": "deteyling", "brand": "OOPSY", "stock": 60, "image_url": "", "description_uz": "Kvarts asosidagi suv himoya qoplamasi.", "description_ru": "Кварцевая защита от дождя."},
    {"id": 7, "name_uz": "Poliroval Gubkalar to'plami (6 dona)", "name_ru": "Набор полировальных губок (6 шт)", "price": 95000, "wholesale_price": 75000, "category": "aksessuarlar", "brand": "SCHOLL", "stock": 100, "image_url": "", "description_uz": "Turli xil yirikllikdagi 6 ta gubka to'plami.", "description_ru": "Набор из 6 губок разной зернистости."},
    {"id": 8, "name_uz": "Mikrofiber Mato 40x40 (10 dona)", "name_ru": "Микрофибра 40x40 (10 шт)", "price": 78000, "wholesale_price": 60000, "category": "aksessuarlar", "brand": "AutoLine", "stock": 200, "image_url": "", "description_uz": "Professional sifatli mikrofiber matolar.", "description_ru": "Профессиональные микрофибровые салфетки."},
]

CATEGORIES = [
    {"id": "all", "name_uz": "Hammasi", "name_ru": "Все", "emoji": "🛍️"},
    {"id": "poliroval", "name_uz": "Poliroval", "name_ru": "Полировка", "emoji": "✨"},
    {"id": "asboblar", "name_uz": "Asboblar", "name_ru": "Инструменты", "emoji": "🔧"},
    {"id": "deteyling", "name_uz": "Deteyling", "name_ru": "Детейлинг", "emoji": "🚗"},
    {"id": "aksessuarlar", "name_uz": "Aksessuarlar", "name_ru": "Аксессуары", "emoji": "🎁"},
]

orders_db = []
users_db = {}

# =============================================
# FASTAPI APP
# =============================================
app = FastAPI(title="AutoLine Shop API")

# Telegram Application (webhook uchun)
bot_app = Application.builder().token(BOT_TOKEN).build()

def get_html():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

# =============================================
# STARTUP / SHUTDOWN — Webhook ro'yxatdan o'tkazish
# =============================================
@app.on_event("startup")
async def startup():
    await bot_app.initialize()
    webhook_url = f"{WEBAPP_URL}/webhook"
    try:
        await bot_app.bot.set_webhook(webhook_url, drop_pending_updates=True)
        logger.info(f"✅ Webhook o'rnatildi: {webhook_url}")
    except Exception as e:
        logger.error(f"❌ Webhook xatosi: {e}")

@app.on_event("shutdown")
async def shutdown():
    await bot_app.bot.delete_webhook()
    await bot_app.shutdown()
    logger.info("Bot to'xtatildi")

# =============================================
# WEBHOOK ENDPOINT — Telegram xabarlarini qabul qilish
# =============================================
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, bot_app.bot)
        await bot_app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return {"ok": True}

# =============================================
# HTML SAHIFALAR
# =============================================
@app.get("/", response_class=HTMLResponse)
async def root():
    return get_html()

@app.get("/app", response_class=HTMLResponse)
async def webapp():
    return get_html()

# =============================================
# API ENDPOINTLAR
# =============================================
@app.get("/api/products")
async def get_products(category: str = "all", search: str = ""):
    products = PRODUCTS
    if category != "all":
        products = [p for p in products if p["category"] == category]
    if search:
        s = search.lower()
        products = [p for p in products if s in p["name_uz"].lower() or s in p["name_ru"].lower() or s in p["brand"].lower()]
    return JSONResponse(products)

@app.get("/api/categories")
async def get_categories():
    return JSONResponse(CATEGORIES)

@app.post("/api/order")
async def create_order(request: Request):
    try:
        data = await request.json()
        order_id = len(orders_db) + 1
        order = {
            "id": order_id,
            "user_id": data.get("user_id"),
            "user_name": data.get("user_name"),
            "phone": data.get("phone"),
            "company": data.get("company", ""),
            "items": data.get("items", []),
            "total": data.get("total"),
            "discount": data.get("discount", 0),
            "payment_method": data.get("payment_method", "cash"),
            "address": data.get("address", ""),
            "note": data.get("note", ""),
            "status": "yangi",
        }
        orders_db.append(order)
        if ADMIN_CHAT_ID:
            await send_order_notification(order)
        return JSONResponse({"success": True, "order_id": order_id})
    except Exception as e:
        logger.error(f"Order error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/api/orders")
async def get_orders():
    return JSONResponse(orders_db)

@app.get("/api/dealer/{user_id}")
async def get_dealer_info(user_id: str):
    user = users_db.get(user_id, {
        "user_id": user_id,
        "total_purchases": 0,
        "dealer_level": "bronze",
        "discount": 5,
        "referral_code": f"AL{user_id[-4:].upper()}",
        "referral_count": 0,
        "commission": 0,
    })
    return JSONResponse(user)

@app.get("/api/webhook-info")
async def webhook_info():
    """Webhook holatini tekshirish"""
    try:
        info = await bot_app.bot.get_webhook_info()
        return JSONResponse({
            "url": info.url,
            "pending_updates": info.pending_update_count,
            "last_error": info.last_error_message,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)})

# =============================================
# ADMIN GA XABAR YUBORISH
# =============================================
async def send_order_notification(order: dict):
    try:
        items_text = "\n".join([
            f"  • {item['name']} x{item['qty']} = {item['total']:,} so'm"
            for item in order["items"]
        ])
        message = (
            f"🛒 <b>YANGI BUYURTMA #{order['id']}</b>\n"
            f"{'─'*25}\n"
            f"👤 Mijoz: {order['user_name']}\n"
            f"📱 Telefon: {order['phone']}\n"
            f"🏢 Kompaniya: {order.get('company', '—')}\n"
            f"📍 Manzil: {order.get('address', '—')}\n"
            f"{'─'*25}\n"
            f"📦 Mahsulotlar:\n{items_text}\n"
            f"{'─'*25}\n"
            f"💰 Jami: <b>{order['total']:,} so'm</b>\n"
            f"🏷️ Chegirma: {order['discount']}%\n"
            f"💳 To'lov: {order['payment_method']}\n"
            f"📝 Izoh: {order.get('note', '—')}\n"
        )
        await bot_app.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Notification error: {e}")

# =============================================
# BOT HANDLERLAR
# =============================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    if user_id not in users_db:
        users_db[user_id] = {
            "user_id": user_id,
            "name": user.full_name,
            "username": user.username,
            "total_purchases": 0,
            "dealer_level": "bronze",
            "discount": 5,
            "referral_code": f"AL{user_id[-4:].upper()}",
            "referral_count": 0,
            "commission": 0,
        }
    keyboard = [
        [InlineKeyboardButton("🛍️ Do'konni ochish", web_app=WebAppInfo(url=f"{WEBAPP_URL}/app?user_id={user_id}"))],
        [InlineKeyboardButton("📦 Buyurtmalarim", callback_data="my_orders"),
         InlineKeyboardButton("👤 Profilim", callback_data="my_profile")],
        [InlineKeyboardButton("📞 Bog'lanish", callback_data="contact")],
    ]
    await update.message.reply_text(
        f"👋 Salom, <b>{user.first_name}</b>!\n\n"
        f"🚗 <b>AutoLine Shop</b>'ga xush kelibsiz!\n\n"
        f"✨ Professional deteyling mahsulotlari\n"
        f"💼 B2B narxlar va chegirmalar\n"
        f"🤖 AI maslahatchi\n"
        f"🎁 Diler tizimi\n\n"
        f"👇 Do'konni ochish uchun tugmani bosing:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    keyboard = [[InlineKeyboardButton("🛍️ Do'konni ochish", web_app=WebAppInfo(url=f"{WEBAPP_URL}/app?user_id={user_id}"))]]
    await update.message.reply_text("👇 Do'konni ochish:", reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 <b>Buyruqlar:</b>\n\n"
        "/start — Botni ishga tushirish\n"
        "/shop — Do'konni ochish\n"
        "/contact — Bog'lanish\n",
        parse_mode="HTML"
    )

async def contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 <b>Bog'lanish:</b>\n\n"
        "☎️ +994 97 780 70 07\n"
        "📧 allautolab@gmail.com\n"
        "📍 Kybray tumani, Ohun Boboev ko'chasi 54A\n\n"
        "🕐 Ish vaqti: 9:00 — 18:00",
        parse_mode="HTML"
    )

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.message.web_app_data.data)
        if data.get("type") == "order":
            order = data.get("order", {})
            await update.message.reply_text(
                f"✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n"
                f"📦 Buyurtma #{order.get('id', '—')}\n"
                f"💰 Jami: {order.get('total', 0):,} so'm\n\n"
                f"Tez orada siz bilan bog'lanamiz! 📞",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"WebApp data error: {e}")

# Handler larni q'oshish
bot_app.add_handler(CommandHandler("start", start_command))
bot_app.add_handler(CommandHandler("help", help_command))
bot_app.add_handler(CommandHandler("shop", shop_command))
bot_app.add_handler(CommandHandler("contact", contact_command))
bot_app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

# =============================================
# ISHGA TUSHIRISH
# =============================================
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
