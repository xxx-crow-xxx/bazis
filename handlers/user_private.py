import os
from aiogram import Router
import logging
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart

from keyboards.inline import main_menu
from google_sheets import get_available_dates, write_to_sheet, auth_google_sheets

user_private_router = Router()


class Registration(StatesGroup):
    user_name = State()
    date = State()
    time = State()
    name = State()
    contact = State()


async def handle_error(message: Message, state: FSMContext, error_msg: str):
    """Обработка ошибок с сохранением состояния"""
    logging.error(error_msg)
    await message.answer(
        "⚠️ Произошла ошибка. Пожалуйста, попробуйте еще раз.", reply_markup=main_menu())
    await state.clear()



@user_private_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(f'''🔥 Приветствуем {message.from_user.full_name} в школе мечты для будущих гуру мебели! 🛋️✨

Здесь вы не просто научитесь — вы станете профи, о котором говорят клиенты:

📐 Проектировать корпусную мебель — от шкафов-купе до элитных гардеробных
💻 Работать в «БАЗИС-Мебельщик» и PRO100 — как 90% топовых мастерских
🤖 Автоматизировать расчеты — габариты, материалы, стоимость за 5 минут
🔩 Подбирать фурнитуру — скрытые петли Blum, направляющие Hettich
✂️ Оптимизировать раскрой — экономить до 30% материала
🚀 И много других навыков — от 3D-визуализации до переговоров с клиентами

⏳ Почему ждать?
Бесплатный пробный урок — ваш первый шаг к:
✅ Первым заказам
✅ Высокому доходу за проекты
✅ Портфолио, которое впечатлит даже скептиков''', reply_markup=main_menu())


@user_private_router.callback_query(lambda c: c.data == 'start_registration')
async def start_registration(callback: CallbackQuery, state: FSMContext):
    try:
        dates = await get_available_dates()
        if not dates:
            await callback.message.edit_text("❌ На данный момент нет доступных дат для записи.")
            return

        builder = InlineKeyboardBuilder()
        for date in dates:
            builder.add(InlineKeyboardButton(
                text=date,
                callback_data=f"date_{date}"
            ))
        builder.adjust(2)

        await callback.message.edit_text(
            "📅 Выберите удобную дату:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(Registration.date)
    except Exception as e:
        await handle_error(callback.message, state, f"Error in start_registration: {e}")


# Обработка выбора даты
@user_private_router.callback_query(Registration.date, lambda c: c.data.startswith('date_'))
async def process_date(callback: CallbackQuery, state: FSMContext):
    try:
        date = callback.data.split('_')[1]
        await state.update_data(date=date)
        await state.update_data(user_name=callback.from_user.username)

        # Получаем доступное время для выбранной даты
        client = auth_google_sheets()
        sheet = client.open("Мебельщик").worksheet("Расписание")
        records = sheet.get_all_records()

        available_times = sorted(set([
            row["Время"] for row in records
            if row["Дата"] == date and row["Кол-во свободных мест"] >= 1
        ]))

        if not available_times:
            await callback.message.edit_text(
                "❌ На выбранную дату нет свободных мест.",
                reply_markup=main_menu()
            )
            await state.clear()
            return

        builder = InlineKeyboardBuilder()
        for time in available_times:
            builder.add(InlineKeyboardButton(
                text=time,
                callback_data=f"time_{time}"
            ))
        builder.adjust(2)

        await callback.message.edit_text(
            f"📅 Выбрана дата: {date}\n\n⏰ Выберите удобное время:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(Registration.time)
    except Exception as e:
        await handle_error(callback.message, state, f"Error in process_date: {e}")


# Обработка выбора времени
@user_private_router.callback_query(Registration.time, lambda c: c.data.startswith('time_'))
async def process_time(callback: CallbackQuery, state: FSMContext):
    try:
        time = callback.data.split('_')[1]
        data = await state.get_data()

        # Проверяем что время действительно доступно
        client = auth_google_sheets()
        sheet = client.open("Мебельщик").worksheet("Расписание")
        records = sheet.get_all_records()

        time_valid = any(
            row["Дата"] == data['date'] and
            row["Время"] == time and
            row["Кол-во свободных мест"] >= 1
            for row in records
        )

        if not time_valid:
            await callback.answer("❌ Это время уже занято. Пожалуйста, выберите другое время.", show_alert=True)
            return

        await state.update_data(time=time)
        await callback.message.edit_text(
            f"📅 Дата: {data['date']}\n"
            f"⏰ Время: {time}\n\n"
            "👤 Введите ваше имя:"
        )
        await state.set_state(Registration.name)
    except Exception as e:
        await handle_error(callback.message, state, f"Error in process_time: {e}")


# Обработка имени
@user_private_router.message(Registration.name)
async def process_name(message: Message, state: FSMContext):
    try:
        if len(message.text.strip()) < 2:
            await message.answer("❌ Имя должно содержать минимум 2 символа. Пожалуйста, введите ваше имя:")
            return

        await state.update_data(name=message.text.strip())
        await message.answer("📱 Введите ваш номер телефона для связи (+375 (xx) xxx xx xx)")
        await state.set_state(Registration.contact)
    except Exception as e:
        await handle_error(message, state, f"Error in process_name: {e}")


# Обработка контакта и финальное сохранение
@user_private_router.message(Registration.contact)
async def process_contact(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        phone = message.text.strip()

        # Минимальная валидация телефона
        if len(phone) < 9 or not any(char.isdigit() for char in phone):
            await message.answer("❌ Пожалуйста, введите корректный номер телефона.")
            return


        # Сохраняем в Google Sheets
        success = await write_to_sheet(
            name=data['name'],
            contact=phone,
            date=data['date'],
            time=data['time']
        )

        if not success:
            raise Exception("Failed to write to Google Sheets")

        # Формируем красивое подтверждение
        confirmation_text = f'''
✅ <b>Вы успешно записаны на пробный урок!</b>

📅 <b>Дата:</b> {data['date']}
⏰ <b>Время:</b> {data['time']}
👤 <b>Имя:</b> {data['name']}
📱 <b>Контакт:</b> {phone}
'''
        await message.answer(confirmation_text)

        # Отправляем уведомление администратору
        admin_id = os.getenv("ADMIN_ID")
        if admin_id:
            await message.bot.send_message(
                chat_id=admin_id,
                text=f"📝 <b>Новая запись на пробный урок!</b>\n\n"
                     f"👤 Имя: {data['name']}\n"
                     f"📱 Телефон: {phone}\n"
                     f"📅 Дата: {data['date']}\n"
                     f"⏰ Время: {data['time']}\n"
                     f"🆔 ID: {message.from_user.id}\n"
                     f"📲 Имя аккаунта: {'@' + data['user_name']}"
            )

    except Exception as e:
        await handle_error(message, state, f"Error in process_contact: {e}")
    finally:
        await state.clear()
