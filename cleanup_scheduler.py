import os
import logging
from datetime import datetime
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from google_sheets import auth_google_sheets
from dateutil.parser import parse


async def cleanup_past_dates(bot: Bot = None):
    """Удаляет прошедшие даты из Google Таблицы с улучшенным парсингом"""
    try:
        client = auth_google_sheets()
        spreadsheet = client.open("Мебельщик")
        worksheet = spreadsheet.worksheet("Расписание")
        worksheet_user = spreadsheet.worksheet("Записи")

        records = worksheet.get_all_records()
        records_user = worksheet_user.get_all_records()
        today = datetime.now().date()
        rows_to_delete = []
        date_formats = [
            "%d.%m.%Y",  # 25.04.2025
            "%d-%m-%Y",  # 25-04-2025
            "%Y-%m-%d",  # 2025-04-25
            "%m/%d/%Y"  # 04/25/2025
        ]

        for i, record in enumerate(records, start=2):
            date_str = record.get("Дата", "")
            if not date_str:
                continue
            try:
                # Пробуем автоматически определить формат даты
                record_date = parse(date_str, dayfirst=True).date()

                if record_date < today:
                    rows_to_delete.append(i)
                    logging.info(f"Найдена прошедшая дата: {date_str} (строка {i})")
            except Exception as e:
                logging.warning(f"Не удалось распознать дату '{date_str}' в строке {i}: {e}")
                continue

        for i, record in enumerate(records_user, start=2):
            date_str = record.get("Дата", "")
            if not date_str:
                continue
            try:
                # Пробуем автоматически определить формат даты
                record_date = parse(date_str, dayfirst=True).date()

                if record_date < today:
                    rows_to_delete.append(i)
                    logging.info(f"Найдена прошедшая дата: {date_str} (строка {i})")

            except Exception as e:
                logging.warning(f"Не удалось распознать дату '{date_str}' в строке {i}: {e}")
                continue

        # Удаляем строки снизу вверх
        for row_num in sorted(rows_to_delete, reverse=True):
            try:
                worksheet.delete_rows(row_num)
                worksheet_user.delete_rows(row_num)
            except Exception as e:
                logging.error(f"Ошибка при удалении строки {row_num}: {e}")
        admin_id = os.getenv("ADMIN_ID")

    except Exception as e:
        admin_id = os.getenv("ADMIN_ID")
        logging.error(f"Критическая ошибка: {e}")
        if bot:
            await bot.send_message(admin_id, f"❌ Ошибка очистки: {str(e)}")
        return 0


async def setup_scheduler(bot: Bot):
    """Настройка периодических задач"""
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    # Ежедневная очистка в 3:00
    scheduler.add_job(
        cleanup_past_dates,
        'cron',
        hour=6,
        minute=00,
        kwargs={'bot': bot}
    )

    # Тестовая задача каждые 10 минут (для отладки)
    # scheduler.add_job(
    #     cleanup_past_dates,
    #     'interval',
    #     minutes=10,
    #     kwargs={'bot': bot}
    # )

    scheduler.start()