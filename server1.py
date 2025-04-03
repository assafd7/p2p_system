import socket
import threading
import json
from database_manager import DatabaseManager


class P2PServer:
    """Manages the P2P server operations including client connections and request handling."""
    
    def __init__(self, host='127.0.0.1', port=9000, db_name='p2p_system.db'):
        self.host = host
        self.port = port
        self.db_manager = DatabaseManager(db_name)
        self.server_socket = None
    
    def handle_client(self, client_socket, addr):
        """Handle client connections and process commands."""
        print(f"Connected to {addr}")
        
        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                try:
                    request = json.loads(data)
                    command = request.get('command')
                    
                    if command == 'register':
                        username = request.get('username')
                        password = request.get('password')
                        email = request.get('email')
                        
                        if self.db_manager.register_user(username, password, email):
                            response = {'status': 'success', 'message': 'User registered successfully'}
                        else:
                            response = {'status': 'error', 'message': 'Username or email already exists'}
                    
                    elif command == 'login':
                        username = request.get('username')
                        password = request.get('password')
                        
                        if self.db_manager.authenticate_user(username, password):
                            response = {'status': 'success', 'message': 'Login successful'}
                        else:
                            response = {'status': 'error', 'message': 'Invalid username or password'}
                    
                    else:
                        response = {'status': 'error', 'message': 'Unknown command'}
                    
                    client_socket.send(json.dumps(response).encode('utf-8'))
                    
                except json.JSONDecodeError:
                    response = {'status': 'error', 'message': 'Invalid JSON format'}
                    client_socket.send(json.dumps(response).encode('utf-8'))
        
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        
        finally:
            client_socket.close()
            print(f"Connection with {addr} closed")
    
    def start(self):
        """Start the server and listen for connections."""
        # Create a socket object
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Set socket option to reuse address
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind the socket to the address and port
        self.server_socket.bind((self.host, self.port))
        
        # Start listening for connections (5 is the max backlog of connections)
        self.server_socket.listen(5)
        
        print(f"Server started on {self.host}:{self.port}")
        
        try:
            while True:
                # Accept a connection
                client_socket, addr = self.server_socket.accept()
                
                # Create a new thread to handle the client
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                client_thread.daemon = True  # Thread will close when main program exits
                client_thread.start()
                
        except KeyboardInterrupt:
            print("Server shutting down...")
        
        finally:
            if self.server_socket:
                self.server_socket.close()


class P2PClient:
    """Example client to test the P2P server."""
    
    def __init__(self, host='127.0.0.1', port=9000):
        self.host = host
        self.port = port
        self.client_socket = None
    
    def connect(self):
        """Connect to the P2P server."""
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))
        return self
    
    def send_request(self, request):
        """Send a request to the server and return the response."""
        if not self.client_socket:
            raise Exception("Not connected to server")
            
        self.client_socket.send(json.dumps(request).encode('utf-8'))
        response = json.loads(self.client_socket.recv(1024).decode('utf-8'))
        return response
    
    def register(self, username, password, email=None):
        """Register a new user."""
        request = {
            'command': 'register',
            'username': username,
            'password': password,
            'email': email
        }
        return self.send_request(request)
    
    def login(self, username, password):
        """Login with credentials."""
        request = {
            'command': 'login',
            'username': username,
            'password': password
        }
        return self.send_request(request)
    
    def close(self):
        """Close the connection."""
        if self.client_socket:
            self.client_socket.close()
            self.client_socket = None


def run_example_client():
    """Run an example client to test the server."""
    client = P2PClient().connect()
    
    # register new user
    register_response = client.register('testuser', 'password123', 'test@example.com')
    print(f"Register response: {register_response}")
    
    # Example: Login
    login_response = client.login('testuser', 'password123')
    print(f"Login response: {login_response}")
    
    client.close()


if __name__ == "__main__":
    # Start the server
    server = P2PServer()
    server.start()
    
