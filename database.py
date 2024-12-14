import sqlite3
from typing import List

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect("meme_bot.db")
    cursor = conn.cursor()

    # Создаем таблицу для хранения групп
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()

# Сохранение группы в базу данных
async def save_group_to_db(group_name: str):
    conn = sqlite3.connect("meme_bot.db")
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO groups (name) VALUES (?)", (group_name,))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Группа с именем '{group_name}' уже существует в базе данных.")
    finally:
        conn.close()

# Получение всех групп из базы данных
async def get_all_groups_from_db() -> List[str]:
    conn = sqlite3.connect("meme_bot.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM groups")
    groups = [row for row in cursor.fetchall()]

    conn.close()
    return groups

# Инициализация базы данных при запуске скрипта
init_db()
