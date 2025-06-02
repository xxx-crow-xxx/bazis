import logging

from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials


def auth_google_sheets():
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        'credentials.json', scope
    )
    client = gspread.authorize(creds)
    return client


# Пример: Получить доступные даты
async def get_available_dates():
    client = auth_google_sheets()
    sheet = client.open("Мебельщик").worksheet("Расписание")
    records = sheet.get_all_records()

    dates = []
    for row in records:
        if int(row["Кол-во свободных мест"]) >= 1:
            dates.append(row["Дата"])
    return sorted(list(set(dates)))  # Уникальные даты


async def write_to_sheet(name, contact, date, time):
    try:
        client = auth_google_sheets()
        spreadsheet = client.open("Мебельщик")

        # 1. Получаем данные из листа "Расписание"
        schedule_sheet = spreadsheet.worksheet("Расписание")
        records = schedule_sheet.get_all_records()

        # Ищем нужную запись
        target_row = None
        for i, row in enumerate(records, start=2):  # start=2 учитывая заголовок
            if str(row["Дата"]) == date and str(row["Время"]) == time:
                target_row = i
                current_seats = int(row["Кол-во свободных мест"])  # Получаем текущее количество мест
                break

        if target_row is None:
            logging.error(f"Не найдена запись для даты {date} и времени {time}")
            return False

        # Проверяем, есть ли свободные места
        if current_seats <= 0:
            logging.error(f"Нет свободных мест на {date} в {time}")
            return False

        # Уменьшаем количество мест на 1
        updated_seats = current_seats - 1
        schedule_sheet.update_cell(target_row, 3, updated_seats)  # Предполагаем, что "Количество мест" в 4 колонке

        # 2. Добавляем запись в лист "Записи"
        records_sheet = spreadsheet.worksheet("Записи")
        records_sheet.append_row([name, contact, date, time])

        return True

    except Exception as e:
        logging.error(f"Error in write_to_sheet: {e}")
        return False
