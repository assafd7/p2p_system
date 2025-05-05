# P2P File Sharing System

A peer-to-peer file sharing system that allows users to share and download files directly between peers.

## Features

- User authentication (login/register)
- File browsing and management
- P2P file sharing
- Peer discovery
- File search across the network
- Real-time status updates

## Requirements

- Python 3.6 or higher
- tkinter (usually comes with Python)
- SQLite3 (usually comes with Python)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd p2p_project
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the server:
```bash
python server1.py
```

2. Start the client application:
```bash
python login_interface.py
```

3. Log in with your credentials or register a new account.

4. Use the interface to:
   - Browse and manage local files
   - Share files with other peers
   - Search for files in the network
   - Download files from other peers

## Architecture

The system consists of several components:

1. **Server (`server1.py`)**: Handles user authentication and peer coordination.
2. **Client Application (`main_app.py`)**: Provides the user interface and file management.
3. **P2P Protocol (`p2p_protocol.py`)**: Implements the peer-to-peer file sharing protocol.
4. **File List Component (`files_index.py`)**: Manages the file browser interface.
5. **Database Manager (`database_manager.py`)**: Handles user data storage.

## P2P Protocol

The P2P protocol uses:
- UDP for peer discovery
- TCP for file transfers
- JSON for message formatting
- SHA-256 for file hashing

## Security

- User authentication is required to access the system
- File transfers are direct between peers
- File integrity is verified using SHA-256 hashes

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 