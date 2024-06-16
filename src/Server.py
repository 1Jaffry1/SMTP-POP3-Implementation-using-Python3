import logging
import socket
import threading


class ServerClass:
    def __init__(self, name, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket = None
        self.name = name
        logging.basicConfig(level=logging.DEBUG, format=f'%(asctime)s - {name} -- %(levelname)s - %(message)s')

    def start_server(self):
        host = self.host
        port = self.port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host, port))
            server_socket.listen(5)
            logging.info(msg=f"{self.name} server listening on port {port}...")

            while True:
                client_socket, client_address = server_socket.accept()
                logging.info(f"Connection from {client_address}")
                threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self):
        pass
