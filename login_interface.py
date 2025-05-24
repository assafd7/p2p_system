# login_interface.py
import tkinter as tk
from tkinter import ttk, messagebox
import json
import socket
import threading
import sys
from config import SERVER_HOST, SERVER_PORT
# Assume main_app.py is in the same directory and contains MainApplication
import main_app


class LoginInterface:
    def __init__(self, root_prm, host=SERVER_HOST, port=SERVER_PORT):
        self.root = root_prm
        self.host = host
        self.port = port
        self.client_socket = None

        # Set window properties
        root.title("P2P File Sharing System - Login")
        root.geometry("400x500")
        root.resizable(False, False)

        # Create a style
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TButton', background='#4a7abc', foreground='white', font=('Arial', 10, 'bold'))
        self.style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        self.style.configure('Header.TLabel', font=('Arial', 16, 'bold'))

        # Main frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Create header
        self.header_label = ttk.Label(self.main_frame, text="P2P File Sharing System", style='Header.TLabel')
        self.header_label.pack(pady=(0, 20))

        # Notebook for tabs (Login/Register)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Login Frame
        self.login_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.login_frame, text="Login")

        # Register Frame
        self.register_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.register_frame, text="Register")

        # Setup login form
        self.setup_login_form()

        # Setup register form
        self.setup_register_form()

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Not connected")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Try to connect to server
        self.connect_to_server()

    def setup_login_form(self):
        # Username
        ttk.Label(self.login_frame, text="Username:").pack(anchor=tk.W, pady=(10, 0))
        self.login_username = ttk.Entry(self.login_frame, width=40)
        self.login_username.pack(fill=tk.X, pady=(5, 10))

        # Password
        ttk.Label(self.login_frame, text="Password:").pack(anchor=tk.W, pady=(10, 0))
        self.login_password = ttk.Entry(self.login_frame, width=40, show="*")
        self.login_password.pack(fill=tk.X, pady=(5, 10))

        # Login button
        self.login_button = ttk.Button(self.login_frame, text="Login", command=self.login)
        self.login_button.pack(pady=20)

        # Status message
        self.login_status_var = tk.StringVar()
        self.login_status = ttk.Label(self.login_frame, textvariable=self.login_status_var)
        self.login_status.pack(pady=10)

    def setup_register_form(self):
        # Username
        ttk.Label(self.register_frame, text="Username:").pack(anchor=tk.W, pady=(10, 0))
        self.register_username = ttk.Entry(self.register_frame, width=40)
        self.register_username.pack(fill=tk.X, pady=(5, 10))

        # Password
        ttk.Label(self.register_frame, text="Password:").pack(anchor=tk.W, pady=(10, 0))
        self.register_password = ttk.Entry(self.register_frame, width=40, show="*")
        self.register_password.pack(fill=tk.X, pady=(5, 10))

        # Confirm Password
        ttk.Label(self.register_frame, text="Confirm Password:").pack(anchor=tk.W, pady=(10, 0))
        self.register_confirm_password = ttk.Entry(self.register_frame, width=40, show="*")
        self.register_confirm_password.pack(fill=tk.X, pady=(5, 10))

        # Email
        ttk.Label(self.register_frame, text="Email (optional):").pack(anchor=tk.W, pady=(10, 0))
        self.register_email = ttk.Entry(self.register_frame, width=40)
        self.register_email.pack(fill=tk.X, pady=(5, 10))

        # Register button
        self.register_button = ttk.Button(self.register_frame, text="Register", command=self.register)
        self.register_button.pack(pady=20)

        # Status message
        self.register_status_var = tk.StringVar()
        self.register_status = ttk.Label(self.register_frame, textvariable=self.register_status_var)
        self.register_status.pack(pady=10)

    def connect_to_server(self):
        """Connect to the server with better error handling"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5)  # Set a timeout for connection attempts
            self.client_socket.connect((self.host, self.port))
            self.status_var.set(f"Connected to server at {self.host}:{self.port}")
            print(f"Successfully connected to server at {self.host}:{self.port}")
        except socket.timeout:
            error_msg = f"Connection timed out. Could not connect to server at {self.host}:{self.port}"
            self.status_var.set(error_msg)
            messagebox.showerror("Connection Error", error_msg)
            print(error_msg)
        except ConnectionRefusedError:
            error_msg = f"Connection refused. Server at {self.host}:{self.port} is not running or not accessible."
            self.status_var.set(error_msg)
            messagebox.showerror("Connection Error", error_msg)
            print(error_msg)
        except Exception as e:
            error_msg = f"Failed to connect: {str(e)}"
            self.status_var.set(error_msg)
            messagebox.showerror("Connection Error", error_msg)
            print(error_msg)

    def send_request(self, request):
        if not self.client_socket:
            messagebox.showerror("Connection Error", "Not connected to server")
            return None

        try:
            self.client_socket.send(json.dumps(request).encode('utf-8'))
            response = json.loads(self.client_socket.recv(1024).decode('utf-8'))
            return response
        except Exception as e:
            messagebox.showerror("Communication Error", f"Error communicating with server: {str(e)}")
            return None

    def login(self):
        username = self.login_username.get()
        password = self.login_password.get()

        if not username or not password:
            self.login_status_var.set("Please fill in all fields")
            return

        request = {
            'command': 'login',
            'username': username,
            'password': password
        }

        self.login_button.config(state=tk.DISABLED)
        self.login_status_var.set("Logging in...")

        # Use a thread to prevent UI freezing
        threading.Thread(target=self._process_login, args=(request,), daemon=True).start()


    def register(self):
        username = self.register_username.get()
        password = self.register_password.get()
        confirm_password = self.register_confirm_password.get()
        email = self.register_email.get()

        if not username or not password or not confirm_password:
            self.register_status_var.set("Please fill in all required fields")
            return

        if password != confirm_password:
            self.register_status_var.set("Passwords do not match")
            return

        request = {
            'command': 'register',
            'username': username,
            'password': password,
            'email': email if email else None
        }

        self.register_button.config(state=tk.DISABLED)
        self.register_status_var.set("Registering...")

        # Use a thread to prevent UI freezing
        threading.Thread(target=self._process_registration, args=(request,), daemon=True).start()

    def _process_registration(self, request):
        response = self.send_request(request)

        def update_ui():
            self.register_button.config(state=tk.NORMAL)
            if response and response.get('status') == 'success':
                self.register_status_var.set("Registration successful! You can now log in.")
                # Clear the form
                self.register_username.delete(0, tk.END)
                self.register_password.delete(0, tk.END)
                self.register_confirm_password.delete(0, tk.END)
                self.register_email.delete(0, tk.END)
                # Switch to login tab
                self.notebook.select(0)
            else:
                error_msg = response.get('message',
                                         'Unknown error') if response else 'Failed to communicate with server'
                self.register_status_var.set(f"Registration failed: {error_msg}")

        # Schedule UI update from the main thread
        self.root.after(0, update_ui)

    def _process_login(self, request):
        response = self.send_request(request)

        def update_ui():
            self.login_button.config(state=tk.NORMAL)
            if response and response.get('status') == 'success':
                self.login_status_var.set("Login successful!")
                # Build user_info dictionary
                user_info = {
                    "username": self.login_username.get(),
                    # Optionally, include additional info like peer's communication address
                }
                # Close login window and launch main application
                self.root.destroy()
                new_root = tk.Tk()
                # Pass the user_info dictionary to the main application
                main_app.MainApplication(new_root, user_info)
                new_root.mainloop()
            else:
                error_msg = response.get('message',
                                         'Unknown error') if response else 'Failed to communicate with server'
                self.login_status_var.set(f"Login failed: {error_msg}")

        # Schedule UI update from the main thread
        self.root.after(0, update_ui)

    def close(self):
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                print("")
                pass


if __name__ == "__main__":
    root = tk.Tk()
    # Get the server IP from command line or use default
    server_ip = SERVER_HOST  # Default to configured host
    if len(sys.argv) > 1:
        server_ip = sys.argv[1]
    print(f"Attempting to connect to server at {server_ip}:{SERVER_PORT}")
    app = LoginInterface(root, host=server_ip)

    # Handle window close
    def on_closing():
        app.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
