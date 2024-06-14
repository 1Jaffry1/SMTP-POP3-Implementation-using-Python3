import hashlib
import logging
import os
import socket
import threading

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


EMAILS_STORAGE_DIR = "emails"
PASSWORDS_FILE = "passwords.txt"

if not os.path.isfile(PASSWORDS_FILE):
    open(PASSWORDS_FILE, 'w').close()

if not os.path.exists(EMAILS_STORAGE_DIR):
    os.makedirs(EMAILS_STORAGE_DIR)


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
                logging.info(msg=f"Connection from {client_address}")
                self.handle_client(client_socket)

    def handle_client(self, client_socket):
        client_socket.sendall(b"220 Welcome to SMTP Server\r\n")
        recipients = []
        sender = None
        data_mode = False
        message_data = ""
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
                    self.store_email(sender, recipients, message_data)
                    client_socket.sendall(b"250 OK: Message accepted for delivery\r\n")
                    message_data = ""
                else:
                    message_data+= data + "\r\n"
                continue

# COMMANDS SECTION, FIRST CHECK FOR QUIT
            if data == "QUIT":
                client_socket.sendall(b"221 Bye\r\n")
                break

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
                if len(split_data) != 3:
                    client_socket.sendall(f"501 1 params expected, got {len(split_data) - 2}\r\n".encode())
                    continue
                recipients.append(data.split(":")[1].strip())
                response = "250 Recipient OK\r\n"

            elif split_data[0] == "DATA":
                if data != "DATA":
                    client_socket.sendall(b'500 Syntax error: Did you mean "DATA"?\r\n')
                    continue
                data_mode = True
                response = "354 End data with <CR><LF>.<CR><LF>\r\n"


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
                        self.client_socket.sendall(f"250 Hello {user}, enter your password please:\r\n".encode())
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
                        logging.info(msg=f"New user {user} created and logged in")

            else:
                response = "502 Command not recognized\r\n"


            client_socket.sendall(response.encode())

        client_socket.close()


    def store_email(self, sender, recipients, message_data):
        email_id = len(os.listdir(EMAILS_STORAGE_DIR))
        email_path = os.path.join(EMAILS_STORAGE_DIR, f"email_{email_id}.txt")
        with open(email_path, "w") as email_file:
            email_file.write(f"From: {sender}\n")
            email_file.write(f"To: {recipients}\n")
            email_file.write(message_data)
        logging.info(msg=f"Stored email {email_id} from {sender} to {recipients}")

if __name__ == "__main__":
    server = SMTPServer()
    server.start_server()


