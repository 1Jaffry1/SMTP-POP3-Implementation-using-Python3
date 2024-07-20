import hashlib
import logging

from DbCommands import *
from Server import ServerClass


class POP3Server(ServerClass):

    def handle_client(self, client_socket):
        self.client_socket = client_socket
        self.client_socket.send(b"+OK POP3 server ready\r\n")

        user = None
        login = False
        pass_count = 0

        while True:
            request = self.client_socket.recv(1024).decode().strip()
            command, *args = request.split()
            logging.debug(f"Received request: {request}")
            if command == "USER":
                try:
                    user = request.split()[1]
                    login = False
                    self.client_socket.sendall(b"+OK User accepted\r\n")
                except IndexError:
                    client_socket.sendall(b"-ERR User required\r\n")

            elif command == "PASS":
                try:
                    password = request.split("PASS ")[1]
                except IndexError:
                    self.client_socket.sendall(b"-ERR Password required\r\n")
                    continue

                if check_user_exists(user):
                    if hashlib.sha3_224(password.encode()).hexdigest() == get_field("users", "password", "email_addr", user):
                        login = True
                        self.client_socket.sendall(b"+OK Password accepted\r\n")
                        continue
                    else:
                        pass_count += 1
                        if pass_count == 5:
                            self.client_socket.sendall(b"-ERR Too many invalid login attempts, closing connection\r\n")
                            self.client_socket.close()
                            break
                        self.client_socket.sendall(f"-ERR Invalid login, {5 - pass_count} attempts remaining\r\n".encode())

                else:
                    client_socket.sendall(b"+New user, password set\r\n")
                    add_user(user, hashlib.sha3_224(password.encode()).hexdigest())
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
                for msg_id, sender, subject, size in message_list:
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
        result += f"Message {id}\nFROM: {sender}\nSUBJECT: {subject}\n\n{body}\nEND OF MESSAGE\n\n"
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
        result += f"FROM: {sender}\nSUBJECT: {subject}\n\n{body}\nEND OF MESSAGE\n\n"
    conn.close()
    if result:
        return result
    return None


def delete_message(user, msg_id):
    conn = sqlite3.connect('email_server.db')
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM email_user
        WHERE email_id = ? AND user_id = (SELECT id FROM users WHERE email_addr = ?);
    ''', (msg_id, user));
    conn.commit()
    conn.close()


if __name__ == "__main__":
    setup_database()
    pop3_server = POP3Server("POP3", "0.0.0.0", 110)
    pop3_server.start_server()
