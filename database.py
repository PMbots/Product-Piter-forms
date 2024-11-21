import sqlite3
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials

SERVICE_ACCOUNT_FILE = r'C:\qwe\work\pdforms\pdforms-7773c804451d.json'
SPREADSHEET_ID = '1vo916JAwlSsmBJmMR1eyIHAeBBGQOWiKkYy9XYLHgx4'  # Убедитесь, что ID таблицы указан без угловых скобок

def connect_to_google_sheet():
    """
    Подключается к Google таблице и возвращает объект таблицы.
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    return spreadsheet

def add_data_to_sheet(sheet_name, data):
    """
    Добавляет данные в Google таблицу.
    Если листа не существует, создаёт его с нужными заголовками.
    """
    try:
        # Подключение к Google таблице
        spreadsheet = connect_to_google_sheet()

        # Проверяем, существует ли лист
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            # Если листа нет, создаём его и добавляем заголовки
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="8")
            worksheet.append_row(["TelegramUsername", "Имя", "Работа", "Опыт", "Сфера", "Страна и город", "Позиция"])

        # Добавляем данные в лист
        worksheet.append_row([
            data.get("username", ""),
            data.get("name", ""),
            data.get("company", ""),
            data.get("experience", ""),
            data.get("industry", ""),
            data.get("location", ""),
            data.get("position", "")
        ])
        logging.info("Данные успешно добавлены в таблицу!")
    except Exception as e:
        logging.error(f"Ошибка при добавлении данных в таблицу: {e}")

def create_connection(db_name='bot_database.db'):
    """Создает подключение к базе данных"""
    return sqlite3.connect(db_name)

def create_table_users(cursor):
    """таблица Users"""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        UserID INTEGER PRIMARY KEY AUTOINCREMENT,
        TelegramUserID INTEGER UNIQUE NOT NULL,
        TelegramUsername NVARCHAR UNIQUE,
        FirstName NVARCHAR,
        LastName NVARCHAR,
        Country NVARCHAR,
        City NVARCHAR,
        PositionDescription NVARCHAR
    );
    """)

def create_table_responses(cursor):
    """таблица Responses"""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Responses (
        ResponseID INTEGER PRIMARY KEY AUTOINCREMENT,
        UserID INTEGER,
        Question NVARCHAR,
        Answer NVARCHAR,
        IsOtherOption BOOLEAN,
        FOREIGN KEY (UserID) REFERENCES Users(UserID)
    );
    """)

def create_table_reminders(cursor):
    """таблица Reminders"""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Reminders (
        ReminderID INTEGER PRIMARY KEY AUTOINCREMENT,
        UserID INTEGER,
        FirstReminderSent DATETIME,
        SecondReminderSent DATETIME,
        IsActive BOOLEAN,
        FOREIGN KEY (UserID) REFERENCES Users(UserID)
    );
    """)

def create_table_admins(cursor):
    """таблица Admins"""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Admins (
        AdminID INTEGER PRIMARY KEY AUTOINCREMENT,
        TelegramUserID INTEGER UNIQUE NOT NULL,
        TelegramUsername NVARCHAR UNIQUE,
        FirstName NVARCHAR,
        LastName NVARCHAR
    );
    """)

def create_table_logs(cursor):
    """таблица Logs"""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Logs (
        LogID INTEGER PRIMARY KEY AUTOINCREMENT,
        UserID INTEGER,
        Event NVARCHAR,
        Timestamp DATETIME,
        FOREIGN KEY (UserID) REFERENCES Users(UserID)
    );
    """)

def save_user_to_db(telegram_user_id, username, first_name, last_name, country=None, city=None, position=None):
    """
    Сохраняет данные пользователя в базу.
    Если пользователь уже существует, данные не обновляются.
    """
    conn = create_connection('bot_database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO Users (TelegramUserID, TelegramUsername, FirstName, LastName, Country, City, PositionDescription)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (telegram_user_id, username, first_name, last_name, country, city, position))
        conn.commit()
        logging.info(f"User with TelegramUserID={telegram_user_id} saved successfully.")
    except Exception as e:
        logging.error(f"Failed to save user with TelegramUserID={telegram_user_id}: {e}")
    finally:
        conn.close()

def save_response_to_db(telegram_user_id, question, answer, is_other_option=False):
    """Сохраняет ответ пользователя в базу"""
    conn = create_connection()
    cursor = conn.cursor()
    try:
        # Получаем UserID из таблицы Users
        cursor.execute("SELECT UserID FROM Users WHERE TelegramUserID = ?", (telegram_user_id,))
        user = cursor.fetchone()
        if not user:
            raise ValueError(f"No user found with TelegramUserID={telegram_user_id}")
        user_id = user[0]
        # Сохраняем ответ
        cursor.execute("""
            INSERT INTO Responses (UserID, Question, Answer, IsOtherOption)
            VALUES (?, ?, ?, ?)
        """, (user_id, question, answer, is_other_option))
        conn.commit()
        logging.info(f"Response saved for UserID={user_id}, Question='{question}', Answer='{answer}'.")
    except Exception as e:
        logging.error(f"Failed to save response for TelegramUserID={telegram_user_id}: {e}")
    finally:
        conn.close()

def save_log(user_id, event, timestamp):
    """Сохраняет событие в таблицу Logs"""
    conn = create_connection('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Logs (UserID, Event, Timestamp)
        VALUES (?, ?, ?)
    """, (user_id, event, timestamp))
    conn.commit()
    conn.close()

def delete_user_from_db(telegram_user_id):
    """
    Удаляет пользователя из базы данных по TelegramUserID.
    """
    conn = create_connection('bot_database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Users WHERE TelegramUserID = ?", (telegram_user_id,))
        conn.commit()
        logging.info(f"User with TelegramUserID={telegram_user_id} deleted successfully.")
    except Exception as e:
        logging.error(f"Failed to delete user with TelegramUserID={telegram_user_id}: {e}")
    finally:
        conn.close()

def add_reminder(user_id, first_reminder_sent=None, second_reminder_sent=None, is_active=True):
    """
    Добавляет напоминание для пользователя.
    """
    conn = create_connection('bot_database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO Reminders (UserID, FirstReminderSent, SecondReminderSent, IsActive)
            VALUES (?, ?, ?, ?)
        """, (user_id, first_reminder_sent, second_reminder_sent, is_active))
        conn.commit()
        logging.info(f"Reminder added for UserID={user_id}.")
    except Exception as e:
        logging.error(f"Failed to add reminder for UserID={user_id}: {e}")
    finally:
        conn.close()

def update_reminder(user_id, column, value):
    """
    Обновляет указанный столбец для напоминания пользователя.
    """
    conn = create_connection('bot_database.db')
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            UPDATE Reminders
            SET {column} = ?
            WHERE UserID = ?
        """, (value, user_id))
        conn.commit()
        logging.info(f"Reminder updated for UserID={user_id}, column={column}, value={value}.")
    except Exception as e:
        logging.error(f"Failed to update reminder for UserID={user_id}, column={column}: {e}")
    finally:
        conn.close()

def deactivate_reminder(user_id):
    """
    Деактивирует напоминание пользователя.
    """
    conn = create_connection('bot_database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE Reminders
            SET IsActive = 0
            WHERE UserID = ?
        """, (user_id,))
        conn.commit()
        logging.info(f"Reminder deactivated for UserID={user_id}.")
    except Exception as e:
        logging.error(f"Failed to deactivate reminder for UserID={user_id}: {e}")
    finally:
        conn.close()

def create_all_tables(db_name='bot_database.db'):
    """все таблицы в бд"""
    conn = create_connection(db_name)
    cursor = conn.cursor()
    create_table_users(cursor)
    create_table_responses(cursor)
    create_table_reminders(cursor)
    create_table_admins(cursor)
    create_table_logs(cursor)
    conn.commit()
    conn.close()
    print("Все таблицы успешно созданы!")