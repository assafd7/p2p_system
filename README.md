# P2P File Sharing System

A peer-to-peer file sharing system that allows users to share and download files directly between peers without a central server.

## Features

- User authentication and account management
- Real-time peer discovery
- File sharing and downloading
- File search functionality
- Secure file transfer with hash verification
- Modern and intuitive user interface

## Requirements

- Python 3.7 or higher
- Required Python packages (install using `pip install -r requirements.txt`):
  - tkinter
  - pathlib
  - typing

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd p2p_project
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
python main_app.py
```

2. Log in with your credentials or create a new account.

3. Main Features:
   - **Upload File**: Click "File" -> "Upload File" to share a file with the network
   - **Download File**: Double-click on a file in the list or use "File" -> "Download File"
   - **Search Files**: Use "File" -> "Search Files" to find specific files
   - **Refresh**: Click the "Refresh" button to update the peer and file lists

4. File Management:
   - Shared files are stored in your local files
   - Downloaded files are saved to `~/Downloads/P2P_Files/`
   - File integrity is verified using SHA-256 hashing

## Network Protocol

The system uses a custom P2P protocol for:
- Peer discovery (UDP)
- File transfer (TCP)
- File announcements
- Network status updates

## Security

- File integrity is verified using SHA-256 hashing
- User authentication is required for all operations
- File transfers are direct between peers

## Troubleshooting

1. If peers are not discovered:
   - Check your network connection
   - Ensure the application is not blocked by a firewall
   - Try clicking the "Refresh" button

2. If file transfers fail:
   - Verify that the source peer is still online
   - Check available disk space
   - Ensure you have write permissions in the download directory

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 