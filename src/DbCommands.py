import sqlite3

def setup_database():
    conn = sqlite3.connect('email_server.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            subject TEXT,
            body TEXT
        );''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_addr TEXT UNIQUE,
            password TEXT
        );''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id INTEGER,
            user_id INTEGER,
            FOREIGN KEY(email_id) REFERENCES emails(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );''')
    conn.commit()
    conn.close()


def check_user_exists(username):
    conn = sqlite3.connect('email_server.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*)
        FROM users
        WHERE email_addr = ?;
    ''', (username,))
    count = cursor.fetchone()[0]
    conn.close()
    if count == 0:
        return False
    return True

def set_field(table, field, value, condition_field, condition_value):
    conn = sqlite3.connect('email_server.db')
    cursor = conn.cursor()
    cursor.execute(f'''
        UPDATE {table}
        SET {field} = ?
        WHERE {condition_field} = ?;
    ''', (value, condition_value))

    conn.commit()
    conn.close()


def get_field(table, field, condition_field, condition_value):
    conn = sqlite3.connect('email_server.db')
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT {field}
        FROM {table}
        WHERE {condition_field} = ?;
    ''', (condition_value,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def add_user(email_addr, password):
    conn = sqlite3.connect('email_server.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (email_addr, password)
        VALUES (?,?);
    ''', (email_addr, password,))
    conn.commit()
    conn.close()