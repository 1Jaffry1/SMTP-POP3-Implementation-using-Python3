import hashlib
import logging
from Server import ServerClass
from DbCommands import *




class SMTPServer(ServerClass):

    def handle_client(self, client_socket):
        client_socket.sendall(b"220 Welcome to SMTP Server\r\n")
        recipients = []
        user = None
        data_mode = False
        sender = None
        message_data = ""
        message_subject = ""
        response = None
        login = False
        step = 0

        while True:
            if step == 0 and login:
                step = 1
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
                    message_subject = ""
                    recipients = []
                    step = 1
                elif data.startswith("SUBJECT:"):
                    message_subject = data.split(":")[1].strip()
                else:
                    message_data += data + "\r\n"
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

                if not check_user_exists(user):
                    logging.info(f"New user {user} attempting to create account")
                    client_socket.sendall(f"250 Hello new user:{user}, enter a password please:\r\n".encode())
                    password = client_socket.recv(1024).decode().strip()
                    add_user(user, hashlib.sha3_224(password.encode()).hexdigest())
                    client_socket.sendall(b"250 OK, Password set\r\n")
                    login = True
                    logging.info(msg=f"New user {user} created and logged in")
                    continue

                logging.info(f"user {user} attempting login")
                client_socket.sendall(f"250 Hello {user}, enter your password please:\r\n".encode())
                login = False

                for i in range(5):
                    password = client_socket.recv(1024).decode().strip()
                    if hashlib.sha3_224(password.encode()).hexdigest() == get_field("users", "password",
                                                                                    "email_addr", user):
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


            elif not login:
                client_socket.sendall(b"500 Authentication error: You must authenticate first\r\n")
                continue

            elif data.split(":")[0] == "MAIL FROM":
                if step != 1:
                    client_socket.sendall(b"503 Bad sequence of commands\r\n")
                    continue

                if len(split_data) != 3:
                    client_socket.sendall(f"501 1 params expected, got {len(split_data) - 2}\r\n".encode())
                    continue
                sender = data.split(":")[1].strip()
                if not (sender == "@ME" or sender == user):
                    client_socket.sendall(f"501 Invalid sender {sender}, sender must be '@ME' or your username\r\n".encode())
                    continue
                sender = user
                response = "250 Sender OK\r\n"
                step = 2

            elif data.split(":")[0] == "RCPT TO":
                if step != 2 and step != 3:
                    client_socket.sendall(b"503 Bad sequence of commands\r\n")
                    continue

                recipient = data.split(":")[1].strip()
                if len(split_data) != 3:
                    client_socket.sendall(f"501 1 params expected, got {len(split_data) - 2}\r\n".encode())
                    continue
                if not check_user_exists(recipient):
                    client_socket.sendall(f"550 User {recipient} not found\r\n".encode())
                    continue
                recipients.append(recipient)
                response = "250 Recipient OK\r\n"
                step = 3

            elif split_data[0] == "DATA":
                if step != 3:
                    client_socket.sendall(b"503 Bad sequence of commands\r\n")
                    continue

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
                    INSERT INTO email_user(email_id, user_id)
                    VALUES (?, (SELECT id FROM users WHERE email_addr = ?));
                ''', (email_id, rcpt))

            conn.commit()
            logging.info(f"Stored email {email_id} from {sender} to {recipients}")

        except sqlite3.Error as e:
            logging.error(f"Error storing email: {e}")
            conn.rollback()
        finally:
            conn.close()


if __name__ == "__main__":
    setup_database()
    server = SMTPServer("SMTP", "0.0.0.0", 25)
    server.start_server()
