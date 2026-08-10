import socket
import threading

def handle_client(client_socket):
    target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        target_socket.connect(('127.0.0.1', 11434))
        
        def forward(src, dst):
            try:
                while True:
                    data = src.recv(4096)
                    if not data:
                        break
                    dst.sendall(data)
            except:
                pass
            finally:
                src.close()
                dst.close()
                
        t1 = threading.Thread(target=forward, args=(client_socket, target_socket))
        t2 = threading.Thread(target=forward, args=(target_socket, client_socket))
        t1.start()
        t2.start()
    except Exception as e:
        print(f"Failed to connect to target: {e}")
        client_socket.close()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(('0.0.0.0', 11435))
server.listen(5)
print("Proxy listening on 0.0.0.0:11435 -> 127.0.0.1:11434")

while True:
    client, addr = server.accept()
    threading.Thread(target=handle_client, args=(client,)).start()
