import socket
import os
import threading


EMAILS_STORAGE_DIR = "emails"

if not os.path.exists(EMAILS_STORAGE_DIR):
    os.makedirs(EMAILS_STORAGE_DIR)


class SMTPServer:
    def __init__(self, host="0.0.0.0", port=25):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start_server(self, host='0.0.0.0', port=25):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host, port))
            server_socket.listen(5)
            print(f"SMTP server listening on port {port}...")

            while True:
                client_socket, client_address = server_socket.accept()
                print(f"Connection from {client_address}")
                self.handle_client(client_socket)

    def handle_client(self, client_socket):
        client_socket.sendall(b"220 Welcome to SMTP Server\r\n")
        recipients = []
        sender = None
        data_mode = False
        message_data = ""
        response = None

        while True:
            data = client_socket.recv(1024).decode().strip()
            if not data:
                break
            print(f"Received: << {data} >>")

            if data_mode:
                if data == ".":
                    data_mode = False
                    self.store_email(sender, recipients, message_data)
                    client_socket.sendall(b"250 OK: Message accepted for delivery\r\n")
                    message_data = ""

                else:
                    message_data+= data + "\r\n"
                continue

            if data.startswith("HELO"):
                domain = data.split()[1]
                response = f"250 Hello {domain}\r\n"

            elif data.startswith("MAIL FROM"):
                sender = data.split(":")[1].strip()
                response = "250 Sender OK\r\n"

            elif data.startswith("RCPT TO"):
                recipients.append(data.split(":")[1].strip())
                response = "250 Recipient OK\r\n"

            elif data == "DATA":
                data_mode = True
                response = "354 End data with <CR><LF>.<CR><LF>\r\n"

            elif data == "QUIT":
                client_socket.sendall(b"221 Bye\r\n")
                break

            client_socket.sendall(response.encode())

        client_socket.close()


    def store_email(self, sender, recipients, message_data):
        email_id = len(os.listdir(EMAILS_STORAGE_DIR))
        email_path = os.path.join(EMAILS_STORAGE_DIR, f"email_{email_id}.txt")
        with open(email_path, "w") as email_file:
            email_file.write(f"From: {sender}\n")
            email_file.write(f"To: {recipients}\n")
            email_file.write(message_data)
        print(f"Stored email {email_id} from {sender} to {recipients}")

if __name__ == "__main__":
    server = SMTPServer()
    server.start_server()


