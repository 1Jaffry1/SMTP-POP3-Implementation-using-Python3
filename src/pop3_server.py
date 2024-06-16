import hashlib
import logging
import os
import socket
import sqlite3
import threading
from smtp_server import setup_database


logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


PASSWORDS_FILE = "POP3_passwords.txt"

if not os.path.isfile(PASSWORDS_FILE):
    open(PASSWORDS_FILE, 'w').close()



class POP3Server:
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
            logging.info(msg=f"POP3 server listening on port {port}...")

            while True:
                client_socket, client_address = server_socket.accept()
                logging.info(f"Connection from {client_address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()


    def handle_client(self, client_socket):
        self.client_socket = client_socket
        self.client_socket.send(b"+OK POP3 server ready\r\n")

        user = None
        login = False
        pass_count = 0

        while True:
            request = self.client_socket.recv(1024).decode().strip()
            command, *args= request.split()
            logging.debug(f"Received request: {request}")
            if command == "USER":
                user = request.split()[1]
                self.client_socket.sendall(b"+OK User accepted\r\n")

            elif command == "PASS":
                try:
                    password = request.split()[1]
                except IndexError:
                    self.client_socket.sendall(b"-ERR Password required\r\n")
                    continue
                with open(PASSWORDS_FILE, "r+") as passwords_file:
                    passwords = dict([line.strip().split(":") for line in passwords_file.readlines()])

                    if user in passwords:
                        if hashlib.sha3_224(password.encode()).hexdigest() == passwords[user]:
                            login = True
                            self.client_socket.sendall(b"+OK Password accepted\r\n")
                            continue
                        else:
                            pass_count += 1
                            if pass_count == 5:
                                self.client_socket.sendall(b"-ERR Too many invalid login attempts, closing connection\r\n")
                                self.client_socket.close()
                                break
                            self.client_socket.sendall(b"-ERR Invalid login\r\n")

                    else:
                        client_socket.sendall(b"+New user, password set\r\n")
                        passwords_file.write(f"{user}:{hashlib.sha3_224(password.encode()).hexdigest()}\n")
                        add_user(user)
                        login = True
                        logging.info(msg=f"New user {user} created and logged in")


            elif command == "QUIT":
                self.client_socket.sendall(b"+OK POP3 server signing off\r\n")
                self.client_socket.close()
                break


            elif not login:
                self.client_socket.sendall(b"-ERR Not authenticated\r\n")
                continue

            elif command == "STAT":
                num_messages, total_size = stat_mailbox(user)
                client_socket.sendall(f"+OK {num_messages} {total_size}\r\n".encode())

            elif command == "LIST":
                message_list = list_messages(user)
                client_socket.sendall(f"+OK {len(message_list)} messages\r\n".encode())
                for msg_id, sender, subject,size in message_list:
                    client_socket.sendall(f"id:{msg_id} {sender} {subject} {size}\r\n".encode())
                client_socket.sendall(b"\r\n")

            elif command == "RETR":
                if args:
                    message = retrieve_with_id(user, int(args[0]))
                else:
                    message = retrieve_message(user)
                if message:
                    client_socket.sendall(b"+OK messages follow\r\n\n")
                    client_socket.sendall(message.encode() + b"\r\n")
                else:
                    client_socket.sendall(b"-ERR No such message\r\n")


            elif command == "DELE":
                if not login:
                    client_socket.sendall(b"-ERR Not authenticated\r\n")
                    continue
                msg_id = int(args[0])
                delete_message(user, msg_id)
                client_socket.sendall(b"+OK message deleted\r\n")


            else:
                client_socket.sendall(b"-ERR Unknown command\r\n")


def add_user(email_addr):
    conn = sqlite3.connect('email_server.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (email_addr)
        VALUES (?);
    ''', (email_addr,))
    conn.commit()
    conn.close()
    
    
def stat_mailbox(user):
    conn = sqlite3.connect('email_server.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(e.id), SUM(LENGTH(e.body))
        FROM emails e
        JOIN users r ON e.id = r.id
        WHERE r.email_addr = ?;
    ''', (user,))
    num_messages, total_size = cursor.fetchone()
    conn.close()
    return num_messages, total_size


def list_messages(user):
    conn = sqlite3.connect('email_server.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT E.ID, E.SENDER, E.subject, LENGTH(E.body)
        FROM users u
        JOIN email_user r ON u.id = r.user_id
        JOIN emails e ON r.email_id = e.id
        WHERE U.email_addr = ?;
''', (user,))
    message_list = cursor.fetchall()
    conn.close()
    return message_list


def retrieve_with_id(user, id):
    conn = sqlite3.connect('email_server.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.id, e.sender, e.subject, e.body
        FROM users u
        JOIN email_user r ON u.id = r.user_id
        JOIN emails e ON r.email_id = e.id
        WHERE U.email_addr = ? and e.id = ?
''', (user, id))
    result = ""
    get = cursor.fetchall()
    for id, sender, subject, body in get:
        result+=f"Message {id}\nFROM: {sender}\nSUBJECT: {subject}\n\n{body}\nEND OF MESSAGE\n\n"
    conn.close()
    if result:
        return result
    return None


def retrieve_message(user):
    conn = sqlite3.connect('email_server.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT e.sender, e.subject, e.body
        FROM users u
        JOIN email_user r ON u.id = r.user_id
        JOIN emails e ON r.email_id = e.id
        WHERE U.email_addr = ?;
''', (user,))
    result = ""
    get = cursor.fetchall()
    for sender, subject, body in get:
        result+=f"FROM: {sender}\nSUBJECT: {subject}\n\n{body}\nEND OF MESSAGE\n\n"
    conn.close()
    if result:
        return result
    return None

def delete_message(user, msg_id):
    conn = sqlite3.connect('email_server.db')
    cursor = conn.cursor()
    cursor.execute('''
           DELETE FROM emails
           WHERE id = ? AND sender IN (
               SELECT email_addr
               FROM users
               WHERE email_addr = ?
           );
       ''', (msg_id, user))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    setup_database()
    pop3_server = POP3Server()
    pop3_server.start_server()