import http.server
import socketserver
import socket
import os

PORT = 8086
DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build", "web")


class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}", flush=True)


class DualStackServer(socketserver.TCPServer):
    """Listen on both IPv4 and IPv6 so both localhost (::1) and 127.0.0.1 work."""
    address_family = socket.AF_INET6

    def server_bind(self):
        # IPV6_V6ONLY=0  →  dual-stack: IPv6 socket also accepts IPv4 connections
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


if __name__ == '__main__':
    DualStackServer.allow_reuse_address = True
    try:
        with DualStackServer(('::', PORT), NoCacheHTTPRequestHandler) as httpd:
            print(f"Serving {DIRECTORY} at port {PORT} (IPv4 + IPv6) with No-Cache headers...", flush=True)
            httpd.serve_forever()
    except Exception as e:
        # Fallback: IPv4-only jika dual-stack tidak didukung
        print(f"Dual-stack gagal ({e}), fallback ke IPv4...", flush=True)
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(('', PORT), NoCacheHTTPRequestHandler) as httpd:
            print(f"Serving {DIRECTORY} at port {PORT} (IPv4 only) with No-Cache headers...", flush=True)
            httpd.serve_forever()
