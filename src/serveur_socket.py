import socket
import json
import sys
import io
from contextlib import redirect_stdout, redirect_stderr

# ============= SERVEUR =============
class RemoteExecutor:
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.server = None
    
    def execute_code(self, code):
        """Exécute du code et capture stdout/stderr"""
        namespace = {}
        output = io.StringIO()
        error_output = io.StringIO()
        
        try:
            with redirect_stdout(output), redirect_stderr(error_output):
                exec(code, namespace)
            
            return {
                'status': 'success',
                'output': output.getvalue(),
                'namespace': {k: str(v) for k, v in namespace.items() 
                             if not k.startswith('_')}
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'output': output.getvalue()
            }
    
    def start(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(1)
        print(f"Serveur écoutant sur {self.host}:{self.port}")
        
        try:
            while True:
                client, addr = self.server.accept()
                print(f"Connexion de {addr}")
                
                data = client.recv(4096).decode()
                code = data.strip()
                
                result = self.execute_code(code)
                response = json.dumps(result)
                
                client.send(response.encode())
                client.close()
        except KeyboardInterrupt:
            print("Serveur arrêté")
        finally:
            self.server.close()


# ============= CLIENT =============
class RemoteClient:
    def __init__(self, host, port=5555):
        self.host = host
        self.port = port
    
    def execute(self, code):
        """Envoie du code au serveur et récupère le résultat"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.host, self.port))
            
            sock.send(code.encode())
            
            response = sock.recv(8192).decode()
            result = json.loads(response)
            
            sock.close()
            return result
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


# ============= UTILISATION =============
if __name__ == "__main__":
    """Usage:
    - Start server (default host 0.0.0.0, port 5555):
        python serveur_socket.py server [host] [port]

    - Run client (default host 127.0.0.1, port 5555):
        python serveur_socket.py client [host] [port] [code]

    If [code] is omitted, a short test snippet is executed.
    """

    if len(sys.argv) > 1 and sys.argv[1] == "server":
        # Démarrer le serveur. Optional: host, port
        host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 5555
        executor = RemoteExecutor(host=host, port=port)
        executor.start()

    elif len(sys.argv) > 1 and sys.argv[1] == "client":
        # Mode client - optional: host, port, code
        host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 5555

        # If code supplied as 4th arg, use it; else use default snippet
        if len(sys.argv) > 4:
            code = sys.argv[4]
        else:
            code = """
x = 10
y = 20
z = x + y
print(f"Résultat: {z}")
"""

        client = RemoteClient(host, port=port)
        result = client.execute(code)
        print(result)

    else:
        print(__doc__ if '__doc__' in globals() and globals()['__doc__'] else "Usage: serveur_socket.py server|client")