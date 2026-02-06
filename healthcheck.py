import socket
import os

def check_port():
    """Проверяет доступность порта 8080"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('localhost', 8080))
    sock.close()
    return result == 0

if __name__ == "__main__":
    if check_port():
        print("✅ Healthcheck passed")
        exit(0)
    else:
        print("❌ Healthcheck failed")
        exit(1)