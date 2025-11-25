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
    
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        # Démarrer le serveur
        executor = RemoteExecutor(port=5555)
        executor.start()
    
    else:
        # Mode client - exécuter du code distant
        client = RemoteClient("192.168.1.100")  # Remplacez par l'IP du serveur
        
        code = """
x = 10
y = 20
z = x + y
print(f"Résultat: {z}")
"""
        
        result = client.execute(code)
        print(result)