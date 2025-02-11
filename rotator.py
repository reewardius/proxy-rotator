import socket
import threading
import argparse
import ssl
from http_parser.parser import HttpParser
from http.client import HTTPResponse
from io import BytesIO
from itertools import cycle
import datetime

class ProxyRotator:
    def __init__(self, port, verbose=False):
        self.port = port
        self.verbose = verbose
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
        self.user_agent_cycle = cycle(self.user_agents)
        self.ua_lock = threading.Lock()

    def log(self, message):
        if self.verbose:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] {message}")

    def get_next_user_agent(self):
        with self.ua_lock:
            return next(self.user_agent_cycle)

    def handle_connect(self, client_socket, hostname, port):
        try:
            # Создаём соединение с целевым сервером
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((hostname, port))
            
            # Отправляем клиенту подтверждение установки туннеля
            client_socket.send(b'HTTP/1.1 200 Connection established\r\n\r\n')
            
            # Создаём два потока для пересылки данных в обоих направлениях
            def forward(src, dst):
                try:
                    while True:
                        data = src.recv(4096)
                        if not data:
                            break
                        dst.send(data)
                except:
                    pass
                finally:
                    src.close()
                    dst.close()

            threading.Thread(target=forward, args=(client_socket, server_socket)).start()
            threading.Thread(target=forward, args=(server_socket, client_socket)).start()
            
        except Exception as e:
            self.log(f"Error in CONNECT tunnel: {e}")
            client_socket.close()

    def handle_client(self, client_socket, client_address):
        request_data = b''
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            request_data += chunk
            if b'\r\n\r\n' in request_data:
                break

        try:
            # Парсим HTTP запрос
            parser = HttpParser()
            parser.execute(request_data, len(request_data))
            
            method = parser.get_method()
            headers = {}
            for header in parser.get_headers().items():
                headers[header[0]] = header[1]
            host = headers.get('Host', '')
            path = parser.get_path()

            self.log(f"Request from {client_address[0]}:{client_address[1]}")
            self.log(f"→ {method} {path}")

            # Обработка CONNECT запроса
            if method == 'CONNECT':
                hostname, port = path.split(':')
                self.log(f"→ Establishing CONNECT tunnel to {hostname}:{port}")
                self.handle_connect(client_socket, hostname, int(port))
                return

            # Обычный HTTP/HTTPS запрос
            new_headers = headers.copy()
            new_user_agent = self.get_next_user_agent()
            new_headers['User-Agent'] = new_user_agent
            self.log(f"→ Changed User-Agent to: {new_user_agent}")
            
            is_https = path.startswith('https://')
            if is_https:
                port = 443
                hostname = path.split('/')[2]
                protocol = "HTTPS"
            else:
                port = 80
                hostname = host
                protocol = "HTTP"
            
            # Создаем соединение с целевым сервером
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if is_https:
                context = ssl.create_default_context()
                server_socket = context.wrap_socket(server_socket, server_hostname=hostname)
            
            server_socket.connect((hostname, port))
            self.log(f"→ Connected to {hostname}:{port}")
            
            # Формируем и отправляем новый запрос
            new_request = f"{method} {path} HTTP/1.1\r\n"
            for key, value in new_headers.items():
                new_request += f"{key}: {value}\r\n"
            new_request += "\r\n"
            
            server_socket.send(new_request.encode())
            self.log("→ Request sent to target server")
            
            # Получаем и пересылаем ответ клиенту
            total_bytes = 0
            while True:
                response = server_socket.recv(4096)
                if not response:
                    break
                total_bytes += len(response)
                client_socket.send(response)
            
            self.log(f"← Response received and forwarded ({total_bytes} bytes)")
            self.log("=" * 50)
            
            server_socket.close()
            
        except Exception as e:
            self.log(f"Error handling request: {e}")
        finally:
            client_socket.close()

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.port))
        server.listen(5)
        print(f"Proxy rotator started on port {self.port}")
        if self.verbose:
            print("Verbose logging enabled")
        print("=" * 50)

        while True:
            client_socket, client_address = server.accept()
            client_thread = threading.Thread(
                target=self.handle_client, 
                args=(client_socket, client_address)
            )
            client_thread.start()

def main():
    parser = argparse.ArgumentParser(description='HTTP/HTTPS Proxy Rotator with sequential User-Agent rotation')
    parser.add_argument('-p', '--port', type=int, default=8080, help='Port to listen on (default: 8080)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()

    rotator = ProxyRotator(args.port, args.verbose)
    rotator.start()

if __name__ == "__main__":
    main()
