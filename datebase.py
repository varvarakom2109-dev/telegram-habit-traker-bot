import sqlite3
from datetime import datetime

def get_connection():
    return sqlite3.connect("habits.db")

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(""" CREATE TABLE IF NOT EXISTS habits ( id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id INTEGER NOT NULL,
                   title TEXT NOT NULL,
                   time TEXT NOT NULL
                   )
            """)
    
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS habits_logs ( id INTEGER PRIMARY KEY AUTOINCREMENT,
                   user_id INTEGER NOT NULL,
                   habit_title TEXT NOT NULL,
                   date TEXT NOT NULL,
                   status TEXT NOT NULL
                   )
            """)
    
    conn.commit()
    conn.close()
    
def add_habit(user_id: int, title: str, time: str):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO habits (user_id, title, time) VALUES (?, ?, ?)",
        (user_id, title, time)
    )
    
    conn.commit()
    conn.close()
    
def get_user_habits(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT title, time FROM habits WHERE user_id = ?", (user_id,)
    )
    
    habits = cursor.fetchall()
    conn.close()
    
    return habits

def delete_habit(user_id: int, title: str):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "DELETE FROM habits WHERE user_id = ? AND title = ?",
        (user_id, title)
    )
    
    cursor.execute(
        "DELETE FROM habits_logs WHERE user_id = ? AND habit_title = ?",
        (user_id, title)
    )
    
    conn.commit()
    conn.close()
    
def log_habit(user_id: int, title: str, status: str):
    conn = get_connection()
    cursor =  conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute(
        """ INSERT INTO habits_logs (user_id, habit_title, date, status)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, title, today, status)
    )
    
    conn.commit()
    conn.close()
    
def get_habit_stats(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT COUNT(*) FROM habits_logs WHERE user_id = ? AND status = 'done' ",
        (user_id,)
    )
    done_count = cursor.fetchone()[0]
    
    cursor.execute(
        "SELECT COUNT(*) FROM habits_logs WHERE user_id = ? AND status = 'miss' ",
        (user_id,)
    )
    miss_count = cursor.fetchone()[0]
    
    total = done_count + miss_count
    percent = round(done_count / total * 100, 1) if total > 0 else 0
    
    conn.close()
    
    return done_count, miss_count, percent

def get_habit_history(user_id: int, days: int = 7):
    """
    Возвращает историю привычек за последние 'days' дней
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        f"""SELECT habit_title, date, status FROM habits_logs
        WHERE user_id = ? AND date >= date('now', '-{days} days')
        ORDER BY date DESC""",
        (user_id,)
    )
    
    history = cursor.fetchall()
    conn.close()
    return history

def clear_history(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "DELETE FROM habits_logs WHERE user_id = ?", 
        (user_id,)
    )
    
    conn.commit()
    conn.close()
    
def was_reminder_send(user_id: int, title: str, date: str):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT 1 FROM habits_logs
        WHERE user_id = ? AND habit_title = ?
        AND date = ?""",
        (user_id, title, date)
    )
    
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_user_habits_full(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, title, time FROM habits WHERE user_id = ?",
        (user_id,)
    )
    
    habits = cursor.fetchall()
    conn.close()
    return habits

def update_habit_time(habit_id: int, new_time: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
         "UPDATE habits SET time = ? WHERE id = ?",
        (new_time, habit_id)
    )
    conn.commit()
    conn.close()

def update_habit_title(habit_id: int, new_title: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE habits SET title = ? WHERE id = ?",
        (new_title, habit_id)
    )
    
    conn.commit()
    conn.close()
    
def delete_habit_by_id(habit_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT user_id, title FROM habits WHERE id = ?", (habit_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return
    user_id, title=row
        
    cursor.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    cursor.execute("DELETE FROM habits_logs WHERE user_id = ? AND habit_title = ?", (user_id, title))
    
    conn.commit()
    conn.close()