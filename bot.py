import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from datetime import datetime

from config import BOT_TOKEN, ADMIN_ID, SERVER_IP, API_PORT, API_SECRET_KEY
from database import (
    init_db, get_or_create_user, update_balance, get_balance,
    add_deposit_request, get_pending_deposit_requests, approve_deposit, reject_deposit,
    add_purchase_record,
    get_purchases_last_week, get_all_steam_ids, get_stats,
    add_admin, remove_admin, get_admins, save_steam_id, get_steam_id,
    set_referrer, get_referral_code, get_referrer_code, get_referrals_list, get_referral_bonus_total
)
from parser import PRIVILEGES, fetch_prices

CARD_NUMBER = "2200700538676841"

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# ------------------ FSM состояния ------------------
class PurchaseStates(StatesGroup):
    waiting_steam_id = State()
    waiting_period_choice = State()
    waiting_level_count = State()
    waiting_sponsor_level = State()

class DepositStates(StatesGroup):
    waiting_amount = State()
    waiting_screenshot = State()

class AdminAddBalanceStates(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()

class ReferralCodeStates(StatesGroup):
    waiting_code = State()

# ------------------ Вспомогательные функции ------------------
async def execute_on_server(command: str) -> bool:
    url = f"http://{SERVER_IP}:{API_PORT}/"
    headers = {"X-Api-Key": API_SECRET_KEY, "Content-Type": "application/json"}
    data = {"command": command}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=5) as resp:
                return resp.status == 200
    except Exception as e:
        await bot.send_message(ADMIN_ID, f"❌ Ошибка соединения с сервером: {e}\nКоманда: {command}")
        return False

def is_admin(user_id: int) -> bool:
    return user_id in get_admins() or user_id == ADMIN_ID

def get_main_keyboard(is_admin_user: bool = False):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📜 Каталог", callback_data="show_catalog"),
        InlineKeyboardButton("💰 Профиль", callback_data="profile"),
        InlineKeyboardButton("➕ Пополнить баланс", callback_data="deposit_start"),
        InlineKeyboardButton("❓ Помощь", callback_data="help")
    )
    if is_admin_user:
        keyboard.add(InlineKeyboardButton("👑 Админ-панель", callback_data="admin_panel"))
    return keyboard

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📊 Покупки за неделю", callback_data="admin_week"),
        InlineKeyboardButton("🆔 Все Steam ID", callback_data="admin_steam_ids"),
        InlineKeyboardButton("💳 Заявки на пополнение", callback_data="admin_deposits"),
        InlineKeyboardButton("📈 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("➕ Начислить баланс", callback_data="admin_add_balance"),
        InlineKeyboardButton("👥 Управление админами", callback_data="admin_manage"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
    )
    return keyboard

def get_manage_admins_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("➕ Добавить админа", callback_data="admin_add"),
        InlineKeyboardButton("➖ Удалить админа", callback_data="admin_remove"),
        InlineKeyboardButton("📋 Список админов", callback_data="admin_list"),
        InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_panel")
    )
    return keyboard

def get_categories_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("👑 Привилегии (VIP, PREMIUM, DELUXE, ELITE, CEZAR)", callback_data="cat_privileges"),
        InlineKeyboardButton("⚡ Улучшения (Доп ХП, Доп урон, Регенерация)", callback_data="cat_upgrades"),
        InlineKeyboardButton("⭐ Спонсор", callback_data="cat_sponsor"),
        InlineKeyboardButton("🛠️ Инструменты и наборы", callback_data="cat_tools"),
        InlineKeyboardButton("🔫 Оружие и защита", callback_data="cat_weapons"),
        InlineKeyboardButton("🏆 Король сервера", callback_data="cat_king"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")
    )
    return keyboard

# ------------------ Обработчики команд ------------------
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user = get_or_create_user(message.from_user.id)
    welcome_text = (
        "✨ **Добро пожаловать в магазин Old Crom!** ✨\n\n"
        "Здесь вы можете приобрести привилегии и уникальные возможности на нашем Rust-сервере.\n\n"
        "🔹 **Как сделать покупку:**\n"
        "1️⃣ Выберите товар в каталоге\n"
        "2️⃣ Укажите ваш Steam ID\n"
        "3️⃣ Товар будет куплен за счёт вашего баланса\n"
        "4️⃣ Если баланса не хватает, пополните его через кнопку «➕ Пополнить баланс»\n\n"
        "📌 По всем вопросам: @nonuks\n\n"
        "👇 Нажмите кнопку ниже, чтобы начать."
    )
    photo_url = "https://gspics.org/images/2026/04/19/IA3Ulv.png"
    await bot.send_photo(message.chat.id, photo=photo_url, caption=welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard(is_admin(message.from_user.id)))

@dp.message_handler(commands=['catalog'])
async def cmd_catalog(message: types.Message):
    await message.answer("📁 **Выберите категорию товаров:**", parse_mode="Markdown", reply_markup=get_categories_keyboard())

@dp.callback_query_handler(lambda c: c.data == "show_catalog")
async def show_catalog(callback: types.CallbackQuery):
    await callback.message.answer("📁 **Выберите категорию товаров:**", parse_mode="Markdown", reply_markup=get_categories_keyboard())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "profile")
async def profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = get_or_create_user(user_id)
    balance = user['balance']
    code = get_referral_code(user_id)
    referrer_code = get_referrer_code(user_id)
    referrals = get_referrals_list(user_id)
    bonus_total = get_referral_bonus_total(user_id)
    steam_id = get_steam_id(user_id) or "не указан"
    text = (
        f"👤 **Ваш профиль**\n\n"
        f"💰 **Баланс:** {balance} ₽\n"
        f"🆔 **Steam ID:** `{steam_id}`\n"
        f"🔑 **Ваш реферальный код:** `{code}`\n"
        f"👥 **Приглашено друзей:** {len(referrals)}\n"
        f"🎁 **Заработано с рефералов:** {bonus_total} ₽\n"
    )
    keyboard = InlineKeyboardMarkup(row_width=1)
    if not referrer_code:
        keyboard.add(InlineKeyboardButton("🔗 Ввести код друга", callback_data="enter_referral_code"))
    else:
        text += f"\n🔗 **Вы приглашены пользователем с кодом:** `{referrer_code}`"
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "enter_referral_code")
async def ask_referral_code(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите **реферальный код** друга (6 символов):")
    await ReferralCodeStates.waiting_code.set()
    await callback.answer()

@dp.message_handler(state=ReferralCodeStates.waiting_code)
async def process_referral_code(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    user_id = message.from_user.id
    if set_referrer(user_id, code):
        await message.answer(f"✅ Реферальный код `{code}` успешно привязан! Теперь вы будете получать 10% от пополнений друга.")
    else:
        await message.answer("❌ Неверный код или вы уже привязаны к другому рефереру. Проверьте код и попробуйте снова.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == "deposit_start")
async def deposit_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("💸 **Введите сумму пополнения в рублях** (целое число):")
    await DepositStates.waiting_amount.set()
    await callback.answer()

@dp.message_handler(state=DepositStates.waiting_amount)
async def deposit_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError
    except:
        await message.answer("❌ Введите положительное число (сумму в рублях).")
        return
    await state.update_data(amount=amount)
    await message.answer(
        f"💳 **Для пополнения баланса на {amount} ₽**\n\n"
        f"Переведите сумму на карту:\n`{CARD_NUMBER}`\n\n"
        f"После перевода нажмите кнопку «✅ Я оплатил» и отправьте скриншот чека.",
        parse_mode="Markdown"
    )
    kb = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("✅ Я оплатил", callback_data="deposit_paid"))
    await message.answer("Нажмите кнопку после оплаты:", reply_markup=kb)
    await DepositStates.waiting_screenshot.set()

@dp.callback_query_handler(lambda c: c.data == "deposit_paid", state=DepositStates.waiting_screenshot)
async def deposit_paid(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📸 Отправьте **скриншот чека** (фото или файл).")
    await callback.answer()

@dp.message_handler(content_types=['photo', 'document'], state=DepositStates.waiting_screenshot)
async def deposit_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    amount = data['amount']
    user_id = message.from_user.id
    file_id = message.photo[-1].file_id if message.photo else message.document.file_id
    request_id = add_deposit_request(user_id, amount, file_id)
    admin_text = (
        f"💳 Новая заявка на пополнение\n"
        f"👤 Пользователь: @{message.from_user.username or 'нет'} (ID: {user_id})\n"
        f"💰 Сумма: {amount} ₽\n"
        f"📝 № заявки: {request_id}"
    )
    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("✅ Одобрить", callback_data=f"deposit_approve_{request_id}"),
        InlineKeyboardButton("❌ Отказать", callback_data=f"deposit_reject_{request_id}")
    )
    if message.photo:
        await bot.send_photo(ADMIN_ID, file_id, caption=admin_text, reply_markup=kb, parse_mode=None)
    else:
        await bot.send_document(ADMIN_ID, file_id, caption=admin_text, reply_markup=kb, parse_mode=None)
    await message.answer("✅ Заявка на пополнение отправлена администратору. После проверки деньги поступят на баланс.")
    await state.finish()

# ------------------ Покупка товара ------------------
@dp.callback_query_handler(lambda c: c.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery, state: FSMContext):
    product_name = callback.data.replace("buy_", "")
    product = (await fetch_prices()).get(product_name)
    if not product:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return
    await state.update_data(product_name=product_name, product=product)
    if product['type'] == 'simple':
        await callback.message.answer(
            f"🛒 **{product_name}**\n💰 Цена: {product['price']} ₽\n\n"
            "📝 Введите ваш **Steam ID** (64-битный):",
            parse_mode="Markdown"
        )
        await PurchaseStates.waiting_steam_id.set()
    elif product['type'] == 'period':
        kb = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("📅 1 месяц", callback_data="period_month"),
            InlineKeyboardButton("♾️ Навсегда", callback_data="period_forever")
        )
        await callback.message.answer(
            f"🛒 **{product_name}**\n\n🗓️ Выберите срок действия:",
            parse_mode="Markdown", reply_markup=kb
        )
        await PurchaseStates.waiting_period_choice.set()
    elif product['type'] == 'level':
        desc = product.get('description', f"⚡ Цена за уровень: {product['price_per_level']} ₽")
        await callback.message.answer(
            f"🛒 **{product_name}**\n\n{desc}\n\n"
            "🔢 Введите количество уровней (целое число):",
            parse_mode="Markdown"
        )
        await PurchaseStates.waiting_level_count.set()
    elif product['type'] == 'sponsor':
        await callback.message.answer(
            f"🛒 **{product_name}**\n⭐ Цена за уровень: {product['price_per_level']} ₽\n"
            f"📊 Доступные уровни: 1 — {product['max_level']}\n\n"
            "🔢 Введите желаемый уровень:",
            parse_mode="Markdown"
        )
        await PurchaseStates.waiting_sponsor_level.set()
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data in ['period_month', 'period_forever'], state=PurchaseStates.waiting_period_choice)
async def process_period(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product = data['product']
    if callback.data == 'period_month':
        amount = product['price']['month']
        cmd = product['cmd']['month']
        period = "1 месяц"
    else:
        amount = product['price']['forever']
        cmd = product['cmd']['forever']
        period = "навсегда"
    await state.update_data(amount=amount, cmd_template=cmd, period=period)
    await callback.message.answer(
        f"💰 Сумма к оплате: {amount} ₽\n\n📝 Введите ваш **Steam ID**:",
        parse_mode="Markdown"
    )
    await PurchaseStates.waiting_steam_id.set()
    await callback.answer()

@dp.message_handler(state=PurchaseStates.waiting_level_count)
async def process_level(message: types.Message, state: FSMContext):
    try:
        levels = int(message.text.strip())
        if levels <= 0:
            raise ValueError
    except:
        await message.answer("❌ Введите **положительное целое число**.", parse_mode="Markdown")
        return
    data = await state.get_data()
    amount = levels * data['product']['price_per_level']
    cmd = data['product']['cmd']
    await state.update_data(amount=amount, levels=levels, cmd_template=cmd)
    await message.answer(f"💰 Сумма к оплате: {amount} ₽\n\n📝 Введите ваш **Steam ID**:", parse_mode="Markdown")
    await PurchaseStates.waiting_steam_id.set()

@dp.message_handler(state=PurchaseStates.waiting_sponsor_level)
async def process_sponsor(message: types.Message, state: FSMContext):
    try:
        level = int(message.text.strip())
        data = await state.get_data()
        if level < 1 or level > data['product']['max_level']:
            await message.answer(f"❌ Уровень должен быть от 1 до {data['product']['max_level']}.", parse_mode="Markdown")
            return
    except:
        await message.answer("❌ Введите число.", parse_mode="Markdown")
        return
    amount = level * data['product']['price_per_level']
    cmd = data['product']['cmd']
    await state.update_data(amount=amount, sponsor_level=level, cmd_template=cmd)
    await message.answer(f"💰 Сумма к оплате: {amount} ₽\n\n📝 Введите ваш **Steam ID**:", parse_mode="Markdown")
    await PurchaseStates.waiting_steam_id.set()

@dp.message_handler(state=PurchaseStates.waiting_steam_id)
async def process_steam_id(message: types.Message, state: FSMContext):
    steam_id = message.text.strip()
    data = await state.get_data()
    amount = data['amount']
    cmd_template = data['cmd_template']
    if 'levels' in data:
        cmd = cmd_template.format(steam_id=steam_id, level=data['levels'])
        product_detail = f"{data['product_name']} {data['levels']} ур."
    elif 'sponsor_level' in data:
        cmd = cmd_template.format(steam_id=steam_id, level=data['sponsor_level'])
        product_detail = f"{data['product_name']} {data['sponsor_level']} ур."
    elif 'period' in data:
        cmd = cmd_template.format(steam_id=steam_id)
        product_detail = f"{data['product_name']} ({data['period']})"
    else:
        cmd = cmd_template.format(steam_id=steam_id)
        product_detail = data['product_name']
    user_id = message.from_user.id
    balance = get_balance(user_id)
    if balance < amount:
        await message.answer(
            f"❌ **Недостаточно средств!**\n"
            f"💰 Ваш баланс: {balance} ₽\n"
            f"🛒 Стоимость: {amount} ₽\n\n"
            f"Пополните баланс через кнопку «➕ Пополнить баланс» в главном меню."
        )
        await state.finish()
        return
    update_balance(user_id, -amount, "purchase", f"Покупка {product_detail}")
    success = await execute_on_server(cmd)
    if success:
        add_purchase_record(user_id, product_detail, steam_id, amount)
        await message.answer(
            f"✅ **{product_detail}** успешно активирована!\n"
            f"🆔 Steam ID: `{steam_id}`\n"
            f"💰 Остаток на балансе: {get_balance(user_id)} ₽\n\n"
            f"🎉 Приятной игры на **Old Crom**!",
            parse_mode="Markdown"
        )
    else:
        update_balance(user_id, amount, "purchase", f"Возврат за {product_detail} (ошибка выдачи)")
        await message.answer("❌ Произошла ошибка при выдаче. Средства возвращены на баланс. Администратор уведомлён.")
    await state.finish()

# ------------------ Админ-панель ------------------
@dp.message_handler(commands=['admin'])
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа.")
        return
    await message.answer("👑 **Админ-панель**", parse_mode="Markdown", reply_markup=get_admin_keyboard())

@dp.callback_query_handler(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет доступа.", show_alert=True)
        return
    await callback.message.answer("👑 **Админ-панель**", parse_mode="Markdown", reply_markup=get_admin_keyboard())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_week")
async def admin_week(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    purchases = get_purchases_last_week()
    if not purchases:
        text = "📊 За последнюю неделю покупок не было."
    else:
        text = "📊 **Покупки за последнюю неделю:**\n\n"
        for p in purchases:
            text += f"• {p['created_at'][:10]} | {p['privilege']} | {p['amount']}₽ | {p['steam_id']}\n"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_steam_ids")
async def admin_steam_ids(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    ids = get_all_steam_ids()
    text = "🆔 **Список Steam ID:**\n\n" + "\n".join(ids) if ids else "Нет сохранённых Steam ID."
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_deposits")
async def admin_deposits(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    requests = get_pending_deposit_requests()
    if not requests:
        await callback.message.answer("💳 Нет ожидающих заявок на пополнение.")
        await callback.answer()
        return
    for req in requests:
        text = (
            f"💳 **Заявка #{req['request_id']}**\n"
            f"👤 Пользователь: {req['user_id']}\n"
            f"💰 Сумма: {req['amount']} ₽\n"
            f"📅 Дата: {req['created_at']}"
        )
        kb = InlineKeyboardMarkup(row_width=2).add(
            InlineKeyboardButton("✅ Одобрить", callback_data=f"deposit_approve_{req['request_id']}"),
            InlineKeyboardButton("❌ Отказать", callback_data=f"deposit_reject_{req['request_id']}")
        )
        if req['screenshot_file_id']:
            try:
                await bot.send_photo(callback.from_user.id, req['screenshot_file_id'], caption=text, reply_markup=kb, parse_mode=None)
            except:
                await callback.message.answer(text, reply_markup=kb)
        else:
            await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("deposit_approve_"))
async def deposit_approve(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав.", show_alert=True)
        return
    request_id = int(callback.data.split("_")[2])
    user_id, amount = approve_deposit(request_id)
    if user_id:
        await bot.send_message(user_id, f"✅ Ваш баланс пополнен на {amount} ₽!")
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ **ОДОБРЕНО**", reply_markup=None)
        await callback.answer("Пополнение одобрено.")
    else:
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ **ЗАЯВКА НЕ НАЙДЕНА**", reply_markup=None)
        await callback.answer("Ошибка.")

@dp.callback_query_handler(lambda c: c.data.startswith("deposit_reject_"))
async def deposit_reject(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав.", show_alert=True)
        return
    request_id = int(callback.data.split("_")[2])
    reject_deposit(request_id)
    await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ **ОТКЛОНЕНО**", reply_markup=None)
    await callback.answer("Заявка отклонена.")

@dp.callback_query_handler(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    count, total = get_stats()
    text = f"📈 **Статистика магазина**\n\nВсего покупок: {count}\nОбщая сумма: {total} ₽"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_add_balance")
async def admin_add_balance_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("➕ Введите **Telegram ID** пользователя, которому хотите начислить баланс:")
    await AdminAddBalanceStates.waiting_user_id.set()
    await callback.answer()

@dp.message_handler(state=AdminAddBalanceStates.waiting_user_id)
async def admin_add_balance_user_id(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
    except:
        await message.answer("❌ Некорректный ID.")
        await state.finish()
        return
    await state.update_data(target_user_id=user_id)
    await message.answer("💰 Введите **сумму** для начисления (в рублях):")
    await AdminAddBalanceStates.waiting_amount.set()

@dp.message_handler(state=AdminAddBalanceStates.waiting_amount)
async def admin_add_balance_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError
    except:
        await message.answer("❌ Введите положительное число.")
        return
    data = await state.get_data()
    target_user_id = data['target_user_id']
    get_or_create_user(target_user_id)
    update_balance(target_user_id, amount, "admin", f"Начисление от администратора")
    await bot.send_message(target_user_id, f"💰 Администратор начислил вам {amount} ₽ на баланс!")
    await message.answer(f"✅ Пользователю {target_user_id} начислено {amount} ₽.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == "admin_manage")
async def admin_manage(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("👥 **Управление администраторами**", parse_mode="Markdown", reply_markup=get_manage_admins_keyboard())
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_add")
async def admin_add_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("Введите Telegram ID пользователя, которого хотите сделать администратором:")
    await state.set_state("waiting_add_admin")
    await callback.answer()

@dp.message_handler(state="waiting_add_admin")
async def process_add_admin(message: types.Message, state: FSMContext):
    try:
        admin_id = int(message.text.strip())
    except:
        await message.answer("❌ Некорректный ID.")
        await state.finish()
        return
    if add_admin(admin_id):
        await message.answer(f"✅ Пользователь {admin_id} добавлен в администраторы.")
    else:
        await message.answer(f"⚠️ Пользователь уже администратор.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == "admin_remove")
async def admin_remove_prompt(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id): return
    await callback.message.answer("Введите Telegram ID администратора для удаления:")
    await state.set_state("waiting_remove_admin")
    await callback.answer()

@dp.message_handler(state="waiting_remove_admin")
async def process_remove_admin(message: types.Message, state: FSMContext):
    try:
        admin_id = int(message.text.strip())
    except:
        await message.answer("❌ Некорректный ID.")
        await state.finish()
        return
    if admin_id == ADMIN_ID:
        await message.answer("❌ Нельзя удалить главного администратора.")
        await state.finish()
        return
    if remove_admin(admin_id):
        await message.answer(f"✅ Администратор {admin_id} удалён.")
    else:
        await message.answer(f"⚠️ Администратор не найден.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == "admin_list")
async def admin_list(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id): return
    admins = get_admins()
    text = "👥 **Список администраторов:**\n\n"
    text += f"• Главный: {ADMIN_ID}\n"
    for a in admins:
        text += f"• {a}\n"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# ------------------ Остальные обработчики ------------------
@dp.callback_query_handler(lambda c: c.data == "help")
async def show_help(callback: types.CallbackQuery):
    help_text = (
        "❓ **Помощь**\n\n"
        "1️⃣ **Как купить привилегию?**\n"
        "   • Выберите товар в каталоге\n"
        "   • Укажите ваш Steam ID\n"
        "   • Если баланса достаточно, товар активируется сразу\n"
        "   • Если недостаточно – пополните баланс через кнопку «➕ Пополнить баланс»\n\n"
        "2️⃣ **Как пополнить баланс?**\n"
        "   • Нажмите «➕ Пополнить баланс»\n"
        "   • Введите сумму\n"
        "   • Переведите деньги на карту и отправьте скриншот\n"
        "   • После проверки администратором деньги поступят на баланс\n\n"
        "3️⃣ **Реферальная программа**\n"
        "   • Ваш уникальный код можно найти в профиле\n"
        "   • Друг вводит ваш код в своём профиле (кнопка «Ввести код друга»)\n"
        "   • Вы будете получать 10% от каждого пополнения друга\n\n"
        "4️⃣ **Где взять Steam ID?**\n"
        "   • Откройте свой профиль Steam → щёлкните правой кнопкой мыши → «Копировать URL»\n"
        "   • Или используйте сайт steamid.io\n\n"
        "📌 По всем вопросам: @nonuks"
    )
    keyboard = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))
    await callback.message.answer(help_text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    welcome_text = (
        "✨ **Добро пожаловать в магазин Old Crom!** ✨\n\n"
        "Используйте кнопки ниже для навигации."
    )
    await callback.message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard(is_admin(callback.from_user.id)))
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("cat_"))
async def handle_category(callback: types.CallbackQuery):
    category = callback.data.replace("cat_", "")
    prices = await fetch_prices()
    keyboard = InlineKeyboardMarkup(row_width=1)
    items_map = {
        "privileges": ["VIP", "PREMIUM", "DELUXE", "ELITE", "CEZAR"],
        "upgrades": ["Доп ХП", "Доп урон", "Регенерация"],
        "sponsor": ["SPONSOR"],
        "tools": ["Телепорт по карте", "Бесконечные патроны", "Radar", "Кастомный набор (3 кита)", "Набор Локи", "Набор Тор", "Набор Зевс", "UberTool", "Волшебный рюкзак"],
        "weapons": ["Черная винтовка (7 дней)", "Игнор черной винтовки (30 дней)"],
        "king": ["King"]
    }
    items = items_map.get(category, [])
    for name in items:
        data = prices.get(name)
        if not data:
            continue
        if data['type'] == 'simple':
            price_text = f"{data['price']} ₽"
        elif data['type'] == 'period':
            price_text = f"📅 месяц {data['price']['month']} ₽ / ♾️ навсегда {data['price']['forever']} ₽"
        elif data['type'] == 'level':
            price_text = f"⚡ {data['price_per_level']} ₽ за уровень"
        elif data['type'] == 'sponsor':
            price_text = f"⭐ {data['price_per_level']} ₽ за уровень (до {data['max_level']})"
        else:
            price_text = "цена по запросу"
        keyboard.add(InlineKeyboardButton(f"{name} — {price_text}", callback_data=f"buy_{name}"))
    keyboard.add(InlineKeyboardButton("🔙 Назад к категориям", callback_data="show_catalog"))
    await callback.message.answer(f"📦 **Категория:** {category}", parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

if __name__ == '__main__':
    init_db()
    executor.start_polling(dp, skip_updates=True)