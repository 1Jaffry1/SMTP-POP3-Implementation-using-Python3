import hashlib
import logging
import os
import socket
import sqlite3
import threading

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
            email_addr TEXT UNIQUE
        );''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_rcpt (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id INTEGER,
            rcpt_id INTEGER,
            FOREIGN KEY(email_id) REFERENCES emails(id),
            FOREIGN KEY(rcpt_id) REFERENCES users(id)
        );''')
    conn.commit()
    conn.close()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

PASSWORDS_FILE = "SMTP_passwords.txt"

if not os.path.isfile(PASSWORDS_FILE):
    open(PASSWORDS_FILE, 'w').close()



class SMTPServer:
    def __init__(self, host="0.0.0.0", port=25):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket = None

    def start_server(self, host='0.0.0.0', port=25):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host, port))
            server_socket.listen(5)
            logging.info(msg=f"SMTP server listening on port {port}...")

            while True:
                client_socket, client_address = server_socket.accept()
                logging.info(f"Connection from {client_address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        client_socket.sendall(b"220 Welcome to SMTP Server\r\n")
        recipients = []
        sender = None
        data_mode = False
        message_data = ""
        message_subject = ""
        response = None
        login = False


        while True:
            data = client_socket.recv(1024).decode().strip()
            if not data:
                client_socket.sendall(b"500 Syntax error: no command provided\r\n")
                continue

            logging.info(msg=f"Received: command << {data} >>")
            split_data = data.split(" ")

            if data_mode:
                if data == ".":
                    data_mode = False
                    self.store_email(sender, recipients, message_data, message_subject)
                    client_socket.sendall(b"250 OK: Message accepted for delivery\r\n")
                    message_data = ""
                elif data.startswith("SUBJECT:"):
                    message_subject = data.split(":")[1].strip()
                else:
                    message_data+= data + "\r\n"
                continue

# COMMANDS SECTION, FIRST CHECK FOR QUIT
            if data == "QUIT":
                client_socket.sendall(b"221 Bye\r\n")
                break

            elif split_data[0].split(":")[0] == "HELO":
                user = data.split()[1]
                response = f"250 Hello {user}\r\n"
                login = True

            elif split_data[0].split(":")[0] == "EHLO":
                if len(split_data) != 2:
                    client_socket.sendall(f"501 2 params expected, got {len(split_data)}\r\n".encode())
                    break
                user = data.split()[1]
                with open(PASSWORDS_FILE, "r+") as passwords_file:
                    passwords = dict([line.strip().split(":") for line in passwords_file.readlines()])

                    if user in passwords:
                        logging.info(f"user {user} attempting login")
                        client_socket.sendall(f"250 Hello {user}, enter your password please:\r\n".encode())
                        login = False

                        for i in range(5):
                            password = client_socket.recv(1024).decode().strip()
                            if hashlib.sha3_224(password.encode()).hexdigest() == passwords[user]:
                                response = "250 OK, Authenticated\r\n"
                                logging.info(msg=f"user {user} logged in")
                                login = True
                                break
                            else:
                                client_socket.sendall(
                                    f"\n500 Invalid password, you have {4 - i} attempts remaining\r\n".encode())
                        if not login:
                            client_socket.sendall(b"500 Too many attempts, closing connection\r\n")
                            break
                    else:
                        logging.info(f"New user {user} attempting to create account")
                        client_socket.sendall(f"250 Hello new user:{user}, enter a password please:\r\n".encode())
                        password = client_socket.recv(1024).decode().strip()
                        passwords_file.write(f"{user}:{hashlib.sha3_224(password.encode()).hexdigest()}\n")
                        response = "250 OK, Password set\r\n"
                        login = True
                        logging.info(msg=f"New user {user} created and logged in")
                sender = user


            elif not login:
                client_socket.sendall(b"500 Authentication error: You must authenticate first\r\n")
                continue

            elif data.split(":")[0] == "MAIL FROM":
                if len(split_data) != 3:
                    client_socket.sendall(f"501 1 params expected, got {len(split_data) - 2}\r\n".encode())
                    continue
                sender = data.split(":")[1].strip()
                response = "250 Sender OK\r\n"

            elif data.split(":")[0] == "RCPT TO":
                recipient = data.split(":")[1].strip()
                if len(split_data) != 3:
                    client_socket.sendall(f"501 1 params expected, got {len(split_data) - 2}\r\n".encode())
                    continue
                if not check_user_exists(recipient):
                    client_socket.sendall(f"550 User {recipient} not found\r\n".encode())
                    continue
                recipients.append(recipient)
                response = "250 Recipient OK\r\n"

            elif split_data[0] == "DATA":
                if data != "DATA":
                    client_socket.sendall(b'500 Syntax error: Did you mean "DATA"?\r\n')
                    continue
                data_mode = True
                response = "354 End data with <CR><LF>.<CR><LF>\r\n"

            else:
                response = "502 Command not recognized\r\n"


            client_socket.sendall(response.encode())

        client_socket.close()

    def store_email(self, sender, recipients, message_data, message_subject):
        conn = sqlite3.connect('email_server.db')
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO emails (sender, subject, body)
                VALUES (?, ?, ?);
            ''', (sender, message_subject, message_data))
            email_id = cursor.lastrowid

            for rcpt in recipients:
                cursor.execute('''
                    INSERT OR IGNORE INTO users (email_addr)
                    VALUES (?);
                ''', (rcpt,))
                cursor.execute('''
                    INSERT INTO email_rcpt (email_id, rcpt_id)
                    VALUES (?, (SELECT id FROM users WHERE email_addr = ?));
                ''', (email_id, rcpt))

            conn.commit()
            logging.info(f"Stored email {email_id} from {sender} to {recipients}")

        except sqlite3.Error as e:
            logging.error(f"Error storing email: {e}")
            conn.rollback()
        finally:
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
    if count == 0:
        return False


if __name__ == "__main__":
    setup_database()
    server = SMTPServer()
    server.start_server()