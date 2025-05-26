"""
Configuration settings for the P2P File Sharing System.
This file centralizes all IP address and port configurations.
"""

# Server Configuration
SERVER_HOST = '127.0.0.1'  # Default to localhost
SERVER_PORT = 9000

# P2P Protocol Configuration
P2P_DISCOVERY_PORT = 9001
P2P_TRANSFER_PORT = 9002  # P2P_DISCOVERY_PORT + 1

# Bootstrap nodes (optional)
BOOTSTRAP_NODES = []  # List of (host, port) tuples for bootstrap nodes

def get_server_address():
    """Returns the server address as a tuple (host, port)"""
    return (SERVER_HOST, SERVER_PORT)

def get_p2p_address():
    """Returns the P2P discovery address as a tuple (host, port)"""
    return (SERVER_HOST, P2P_DISCOVERY_PORT)

def get_transfer_address():
    """Returns the P2P transfer address as a tuple (host, port)"""
    return (SERVER_HOST, P2P_TRANSFER_PORT) 