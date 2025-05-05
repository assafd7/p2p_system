import socket
import threading
import json
import os
import hashlib
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple

# =============================================================================
# Logging Configuration
# =============================================================================

def setup_logging():
    """Configure logging to both console and file"""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create a logger
    logger = logging.getLogger('p2p_protocol')
    logger.setLevel(logging.INFO)
    
    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler(log_dir / 'p2p.log')
    
    # Create formatters and add it to handlers
    log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(log_format)
    file_handler.setFormatter(log_format)
    
    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

# =============================================================================
# P2P Protocol Class
# =============================================================================

class P2PProtocol:
    """
    A peer-to-peer file sharing protocol implementation.
    Handles peer discovery, file sharing, and file transfers.
    """
    
    # =========================================================================
    # Initialization and Cleanup
    # =========================================================================
    
    def __init__(self, host: str = '0.0.0.0', port: int = 9001, 
                 bootstrap_nodes: List[Tuple[str, int]] = None):
        """
        Initialize the P2P protocol.
        
        Args:
            host: The host address to bind to
            port: The port to listen on
            bootstrap_nodes: List of known peers to connect to initially
        """
        # Input validation
        assert isinstance(host, str), "Host must be a string"
        assert isinstance(port, int) and 1024 <= port <= 65535, "Port must be an integer between 1024 and 65535"
        assert bootstrap_nodes is None or isinstance(bootstrap_nodes, list), "Bootstrap nodes must be a list or None"
        
        # Initialize instance variables
        self.host = host
        self.port = port
        self.bootstrap_nodes = bootstrap_nodes or [('127.0.0.1', 9001)]
        self.peers: Dict[Tuple[str, int], float] = {}
        self.shared_files: Dict[str, Dict] = {}
        self.local_files: Dict[str, Dict] = {}
        self.running = True
        
        # Set up network sockets
        self._setup_sockets()
        
        # Start background threads
        self._start_threads()
        
        # Begin peer discovery
        self.discover_peers()
        logger.info(f"P2P Protocol initialized on {self.host}:{self.port}")
    
    def _setup_sockets(self):
        """Set up UDP and TCP sockets for peer discovery and file transfers"""
        # UDP socket for peer discovery
        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.discovery_socket.bind((self.host, self.port))
        
        # TCP socket for file transfers
        self.transfer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.transfer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.transfer_socket.bind((self.host, self.port + 1))
        self.transfer_socket.listen(5)
    
    def _start_threads(self):
        """Start background threads for peer discovery and file transfers"""
        self.discovery_thread = threading.Thread(target=self._discovery_loop)
        self.transfer_thread = threading.Thread(target=self._transfer_loop)
        
        self.discovery_thread.start()
        self.transfer_thread.start()
    
    def stop(self):
        """Stop all background threads and close sockets"""
        # Send goodbye message to all peers
        message = {'type': 'goodbye'}
        for peer in self.peers:
            try:
                self.discovery_socket.sendto(json.dumps(message).encode('utf-8'), peer)
                logger.info(f"Sent goodbye to peer {peer}")
            except Exception as e:
                logger.error(f"Error sending goodbye to {peer}: {e}")
        
        # Stop threads and close sockets
        self.running = False
        self.discovery_socket.close()
        self.transfer_socket.close()
        
        if self.discovery_thread.is_alive():
            self.discovery_thread.join()
        if self.transfer_thread.is_alive():
            self.transfer_thread.join()
        
        logger.info("P2P Protocol stopped")
    
    # =========================================================================
    # Peer Discovery and Management
    # =========================================================================
    
    def discover_peers(self):
        """Discover peers in the network by contacting bootstrap nodes"""
        message = {'type': 'hello'}
        for node in self.bootstrap_nodes:
            try:
                self.discovery_socket.sendto(json.dumps(message).encode('utf-8'), node)
                logger.info(f"Sent hello to bootstrap node {node}")
            except Exception as e:
                logger.error(f"Error connecting to bootstrap node {node}: {e}")
    
    def _discovery_loop(self):
        """Handle peer discovery messages"""
        while self.running:
            try:
                data, addr = self.discovery_socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                
                assert 'type' in message, "Message must have a type field"
                
                if message['type'] == 'hello':
                    self._handle_hello_message(addr)
                elif message['type'] == 'hello_response':
                    self._handle_hello_response(addr, message)
                elif message['type'] == 'announce_file':
                    self._handle_file_announcement(addr, message)
                elif message['type'] == 'goodbye':
                    self._remove_peer(addr)
                    logger.info(f"Peer {addr} has left the network")
            
            except Exception as e:
                logger.error(f"Error in discovery loop: {e}")
    
    def _handle_hello_message(self, addr: Tuple[str, int]):
        """Handle a hello message from a new peer"""
        self.peers[addr] = time.time()
        logger.info(f"New peer discovered: {addr}")
        
        # Send response with our shared files
        response = {
            'type': 'hello_response',
            'files': {hash: info['name'] for hash, info in self.local_files.items()}
        }
        self.discovery_socket.sendto(json.dumps(response).encode('utf-8'), addr)
    
    def _handle_hello_response(self, addr: Tuple[str, int], message: dict):
        """Handle a hello response from a peer"""
        self.peers[addr] = time.time()
        logger.info(f"Received hello response from: {addr}")
        
        assert 'files' in message, "Hello response must include files"
        for file_hash, file_name in message['files'].items():
            if file_hash not in self.shared_files:
                self.shared_files[file_hash] = {'peers': [], 'name': file_name}
            if addr not in self.shared_files[file_hash]['peers']:
                self.shared_files[file_hash]['peers'].append(addr)
                logger.info(f"Added file {file_name} ({file_hash}) from peer {addr}")
    
    def _handle_file_announcement(self, addr: Tuple[str, int], message: dict):
        """Handle a file announcement from a peer"""
        assert 'file_hash' in message, "Announce message must include file_hash"
        assert 'file_name' in message, "Announce message must include file_name"
        
        file_hash = message['file_hash']
        file_name = message['file_name']
        
        if file_hash not in self.shared_files:
            self.shared_files[file_hash] = {'peers': [], 'name': file_name}
        if addr not in self.shared_files[file_hash]['peers']:
            self.shared_files[file_hash]['peers'].append(addr)
            logger.info(f"Received file announcement: {file_name} ({file_hash}) from {addr}")
    
    def _remove_peer(self, peer: Tuple[str, int]):
        """Remove a peer from the network"""
        assert isinstance(peer, tuple) and len(peer) == 2, "Peer must be a tuple of (host, port)"
        assert isinstance(peer[0], str), "Peer host must be a string"
        assert isinstance(peer[1], int), "Peer port must be an integer"
        
        if peer in self.peers:
            del self.peers[peer]
            # Remove peer from shared files
            for file_hash in self.shared_files:
                if peer in self.shared_files[file_hash]['peers']:
                    self.shared_files[file_hash]['peers'].remove(peer)
                    # If no more peers have this file, remove it from shared files
                    if not self.shared_files[file_hash]['peers']:
                        del self.shared_files[file_hash]
    
    # =========================================================================
    # File Transfer and Management
    # =========================================================================
    
    def share_file(self, file_path: str) -> str:
        """Share a file and return its hash"""
        assert isinstance(file_path, str), "File path must be a string"
        assert os.path.exists(file_path), f"File not found: {file_path}"
        
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        file_name = os.path.basename(file_path)
        self.local_files[file_hash] = {'path': file_path, 'name': file_name}
        self._announce_file(file_hash, file_name)
        logger.info(f"Shared file {file_name} ({file_hash})")
        return file_hash
    
    def request_file(self, file_hash: str, save_as: str = None) -> str:
        """Request a file from peers and return the local path"""
        assert isinstance(file_hash, str), "File hash must be a string"
        assert save_as is None or isinstance(save_as, str), "Save as name must be a string or None"
        
        if file_hash in self.local_files:
            return self.local_files[file_hash]['path']
        
        if file_hash not in self.shared_files or not self.shared_files[file_hash]['peers']:
            raise ValueError(f"File not found in network: {file_hash}")
        
        # Try to download from each peer until successful
        for peer in self.shared_files[file_hash]['peers']:
            try:
                file_path = self._download_from_peer(peer, file_hash, save_as)
                return file_path
            except Exception as e:
                logger.error(f"Error downloading from {peer}: {e}")
                continue
        
        raise Exception("Failed to download file from any peer")
    
    def _download_from_peer(self, peer: Tuple[str, int], file_hash: str, save_as: str = None) -> str:
        """Download a file from a specific peer"""
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((peer[0], peer[1] + 1))  # Connect to transfer port
        
        request = {
            'type': 'request_file',
            'file_hash': file_hash
        }
        client_socket.send(json.dumps(request).encode('utf-8'))
        
        file_name = save_as if save_as else self.shared_files[file_hash]['name']
        file_path = os.path.join('downloads', file_name)
        os.makedirs('downloads', exist_ok=True)
        
        logger.info(f"Downloading file {file_name} ({file_hash}) from {peer}")
        with open(file_path, 'wb') as f:
            while True:
                data = client_socket.recv(8192)
                if not data:
                    break
                f.write(data)
        
        self.local_files[file_hash] = {'path': file_path, 'name': file_name}
        return file_path
    
    def _transfer_loop(self):
        """Handle file transfer requests"""
        while self.running:
            try:
                client_socket, addr = self.transfer_socket.accept()
                threading.Thread(target=self._handle_transfer_request, 
                               args=(client_socket, addr)).start()
            except Exception as e:
                logger.error(f"Error in transfer loop: {e}")
    
    def _handle_transfer_request(self, client_socket: socket.socket, addr: Tuple[str, int]):
        """Handle a single file transfer request"""
        try:
            request = json.loads(client_socket.recv(1024).decode('utf-8'))
            assert 'type' in request, "Request must have a type field"
            
            if request['type'] == 'request_file':
                self._handle_file_request(client_socket, addr, request)
            elif request['type'] == 'send_file':
                self._handle_file_receive(client_socket, addr, request)
        
        except Exception as e:
            logger.error(f"Error handling transfer request: {e}")
        
        finally:
            client_socket.close()
    
    def _handle_file_request(self, client_socket: socket.socket, addr: Tuple[str, int], 
                           request: dict):
        """Handle a request to send a file"""
        assert 'file_hash' in request, "Request file message must include file_hash"
        file_hash = request['file_hash']
        
        if file_hash in self.local_files:
            file_path = self.local_files[file_hash]['path']
            logger.info(f"Sending file {self.local_files[file_hash]['name']} ({file_hash}) to {addr}")
            with open(file_path, 'rb') as f:
                while True:
                    data = f.read(8192)
                    if not data:
                        break
                    client_socket.send(data)
    
    def _handle_file_receive(self, client_socket: socket.socket, addr: Tuple[str, int], 
                           request: dict):
        """Handle receiving a file"""
        assert 'file_hash' in request, "Send file message must include file_hash"
        assert 'file_name' in request, "Send file message must include file_name"
        assert 'file_size' in request, "Send file message must include file_size"
        
        file_hash = request['file_hash']
        file_name = request['file_name']
        file_size = request['file_size']
        file_path = os.path.join('downloads', file_name)
        
        os.makedirs('downloads', exist_ok=True)
        logger.info(f"Receiving file {file_name} ({file_hash}) from {addr}")
        
        with open(file_path, 'wb') as f:
            remaining = file_size
            while remaining > 0:
                data = client_socket.recv(min(8192, remaining))
                if not data:
                    break
                f.write(data)
                remaining -= len(data)
        
        self.local_files[file_hash] = {'path': file_path, 'name': file_name}
        self._announce_file(file_hash, file_name)
    
    def _announce_file(self, file_hash: str, file_name: str):
        """Announce a new file to all known peers"""
        assert isinstance(file_hash, str), "File hash must be a string"
        assert isinstance(file_name, str), "File name must be a string"
        
        message = {
            'type': 'announce_file',
            'file_hash': file_hash,
            'file_name': file_name
        }
        
        for peer in self.peers:
            try:
                self.discovery_socket.sendto(json.dumps(message).encode('utf-8'), peer)
                logger.info(f"Announced file {file_name} ({file_hash}) to {peer}")
            except Exception as e:
                logger.error(f"Error announcing file to {peer}: {e}") 