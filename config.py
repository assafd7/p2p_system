"""
Configuration settings for the P2P file sharing system.
"""

# Network Configuration
DEFAULT_HOST = '0.0.0.0'  # Allow connections from any IP
DEFAULT_SERVER_PORT = 9000
DEFAULT_P2P_PORT = 9001

# Server Configuration
SERVER_HOST = DEFAULT_HOST  # Server should listen on all interfaces
SERVER_PORT = DEFAULT_SERVER_PORT

# P2P Protocol Configuration
P2P_HOST = DEFAULT_HOST  # P2P should also listen on all interfaces
P2P_PORT = DEFAULT_P2P_PORT

# Database Configuration
DATABASE_NAME = 'p2p_system.db' 