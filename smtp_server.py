from socket import *
from commands import *
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def start_server(host='0.0.0.0', port=25):
    server_socket = socket(AF_INET, SOCK_STREAM)
    # server_socket.close()
    with socket(AF_INET, SOCK_STREAM) as server_socket:
        server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"SMTP server listening on port {port}...")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connection from {client_address}")
            handle_client(client_socket)



def handle_client(client_socket):
    with client_socket:
        client_socket.sendall(b'220 Welcome to SMTP Server\r\n')
        mail_from_address = None
        rcpt_to_addresses = []
        data_mode = False
        data_lines = []

        try:
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                command = data.decode().strip()
                logging.info(f"Received command: {command}")

                if data_mode:
                    if command == ".":
                        response = end_of_data(data_lines)
                        client_socket.sendall(response.encode())
                        data_mode = False
                    else:
                        data_lines.append(command)
                    continue

                if command.startswith("HELO"):
                    try:
                        domain = command.split()[1]
                        response = HELO(domain)
                    except IndexError:
                        response = b'501 Syntax error in parameters or arguments\r\n'

                elif command.startswith("MAIL FROM"):
                    try:
                        sender = email_splitter(command.split(":")[1].strip())
                        response = MAIL_FROM(sender)
                    except IndexError:
                        response = b'501 Syntax error in parameters or arguments\r\n'

                elif command.startswith("RCPT TO"):
                    try:
                        receiver = email_splitter(command.split(":")[1].strip())
                        rcpt_to_addresses.append(receiver)
                        response = RCPT_TO(receiver)
                    except IndexError:
                        response = "501 Syntax error in parameters or arguments\r\n"

                elif command == "DATA":
                    if sender and rcpt_to_addresses:
                        response = DATA()
                        data_mode = True
                        data_lines = []
                    else:
                        response = "503 Bad sequence of commands\r\n"

                elif command == "QUIT":
                    response = QUIT()
                    client_socket.sendall(response.encode())
                    logging.info("Connection closed by client")
                    break

                else:
                    response = "502 Command not implemented\r\n"

                client_socket.sendall(response.encode())

        except Exception as e:
            logging.error(f"Error handling client: {e}")
            client_socket.sendall(b"451 Requested action aborted: local error in processing\r\n")


if __name__ == "__main__":
    start_server()