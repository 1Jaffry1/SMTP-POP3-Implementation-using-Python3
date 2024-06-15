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

                password = request.split()[1]
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
                        client_socket.sendall(b"+New user, password set")
                        passwords_file.write(f"{user}:{hashlib.sha3_224(password.encode()).hexdigest()}\n")
                        logging.info(msg=f"New user {user} created")


            elif command == "QUIT":
                self.client_socket.sendall(b"+OK POP3 server signing off\r\n")
                self.client_socket.close()
                break


            elif not login:
                self.client_socket.sendall(b"-ERR Not authenticated\r\n")
                continue

            elif command == "STAT":
                num_messages, total_size = self.stat_mailbox(user)
                client_socket.sendall(f"+OK {num_messages} {total_size}\r\n".encode())

            elif command == "LIST":
                message_list = self.list_messages(user)
                client_socket.sendall(f"+OK {len(message_list)} messages\r\n".encode())
                for msg_id, size in message_list:
                    client_socket.sendall(f"{msg_id} {size}\r\n".encode())
                client_socket.sendall(b".\r\n")

            elif command == "RETR":
                msg_id = int(args[0])
                message = self.retrieve_message(user, msg_id)
                if message:
                    client_socket.sendall(b"+OK message follows\r\n")
                    client_socket.sendall(message.encode() + b"\r\n.\r\n")
                else:
                    client_socket.sendall(b"-ERR No such message\r\n")


            elif command == "DELE":
                if not login:
                    client_socket.sendall(b"-ERR Not authenticated\r\n")
                    continue
                msg_id = int(args[0])
                self.delete_message(user, msg_id)
                client_socket.sendall(b"+OK message deleted\r\n")


            else:
                client_socket.sendall(b"-ERR Unknown command\r\n")

    def stat_mailbox(self, user):
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

    def message_list(self, user):
        conn = sqlite3.connect('email_server.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.id, e.subject, LENGTH(e.body)
            FROM emails e
            JOIN users r ON e.id = r.id
            WHERE r.email_addr = ?;
''', (user,))
        message_list = cursor.fetchall()
        conn.close()
        return message_list

    def retrieve_message(self, user, msg_id):
        conn = sqlite3.connect('email_server.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT e.body
            FROM emails e
            JOIN users r ON e.id = r.id
            WHERE r.email_addr = ? AND e.id = ?;
        ''', (user, msg_id))
        result = cursor.fetchone()
        conn.close()
        if result:
            return result[0]
        return None

    def delete_message(self, user, msg_id):
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