from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

register = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(
            text='👉 Записаться',
            callback_data='register'
        )
    ]
])

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text='👉 Записаться на пробный урок',
        callback_data='start_registration'
    ))
    return builder.as_markup()