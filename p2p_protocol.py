import socket
import threading
import json
import os
import hashlib
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import logging.handlers
from config import get_p2p_address, get_transfer_address, BOOTSTRAP_NODES

# =============================================================================
# Logging Configuration, 19"02
# =============================================================================

def setup_logging():
    """Configure logging to both console and file"""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create a logger
    logger = logging.getLogger('p2p_protocol')
    logger.setLevel(logging.DEBUG)  # Changed to DEBUG for more detailed logging
    
    # Remove any existing handlers to prevent duplicate logging
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'p2p.log',
        maxBytes=1024*1024,  # 1MB
        backupCount=5
    )
    
    # Create formatters and add it to handlers
    log_format = logging.Formatter('%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s')
    console_handler.setFormatter(log_format)
    file_handler.setFormatter(log_format)
    
    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

# Add rate limiting for logging
class RateLimitedLogger:
    def __init__(self, logger, rate_limit_seconds=5):
        self.logger = logger
        self.rate_limit_seconds = rate_limit_seconds
        self.last_log_time = {}
    
    def _should_log(self, message):
        current_time = time.time()
        if message not in self.last_log_time:
            self.last_log_time[message] = current_time
            return True
        
        if current_time - self.last_log_time[message] >= self.rate_limit_seconds:
            self.last_log_time[message] = current_time
            return True
        
        return False
    
    def debug(self, message):
        if self._should_log(message):
            self.logger.debug(message)
    
    def info(self, message):
        if self._should_log(message):
            self.logger.info(message)
    
    def warning(self, message):
        if self._should_log(message):
            self.logger.warning(message)
    
    def error(self, message):
        if self._should_log(message):
            self.logger.error(message)

# Create rate-limited logger
logger = RateLimitedLogger(logger)

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
    
    def __init__(self, host=None, port=None, bootstrap_nodes=None):
        # Use configuration values if not specified
        if host is None or port is None:
            host, port = get_p2p_address()
        
        logger.debug(f"Initializing P2P Protocol with host={host}, port={port}, bootstrap_nodes={bootstrap_nodes}")
        
        # Input validation
        assert isinstance(host, str), "Host must be a string"
        assert isinstance(port, int) and 1024 <= port <= 65535, "Port must be an integer between 1024 and 65535"
        assert bootstrap_nodes is None or isinstance(bootstrap_nodes, list), "Bootstrap nodes must be a list or None"
        
        # Get the actual IP address if host is 0.0.0.0
        if host == '0.0.0.0':
            self.host = self._get_local_ip()
            logger.debug(f"Got local IP: {self.host}")
        else:
            self.host = host
            
        self.port = port
        self.bootstrap_nodes = bootstrap_nodes or BOOTSTRAP_NODES
        logger.debug(f"Using bootstrap nodes: {self.bootstrap_nodes}")
        
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
        logger.debug("Setting up network sockets")
        try:
            # UDP socket for peer discovery
            self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.discovery_socket.bind((self.host, self.port))
            logger.debug(f"Discovery socket bound to {self.host}:{self.port}")
            
            # TCP socket for file transfers
            self.transfer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.transfer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.transfer_socket.bind((self.host, self.port + 1))
            self.transfer_socket.listen(5)
            logger.debug(f"Transfer socket bound to {self.host}:{self.port + 1}")
        except Exception as e:
            logger.error(f"Error setting up sockets: {e}")
            raise
    
    def _start_threads(self):
        """Start background threads for peer discovery and file transfers"""
        self.discovery_thread = threading.Thread(target=self._discovery_loop)
        self.transfer_thread = threading.Thread(target=self._transfer_loop)
        self.periodic_discovery_thread = threading.Thread(target=self._periodic_discovery)
        
        self.discovery_thread.daemon = True
        self.transfer_thread.daemon = True
        self.periodic_discovery_thread.daemon = True
        
        self.discovery_thread.start()
        self.transfer_thread.start()
        self.periodic_discovery_thread.start()
    
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
        logger.debug("Starting peer discovery")
        message = {
            'type': 'hello',
            'host': self.host,
            'port': self.port
        }
        
        # Send to bootstrap nodes
        for node in self.bootstrap_nodes:
            try:
                self.discovery_socket.sendto(json.dumps(message).encode('utf-8'), node)
                logger.debug(f"Sent hello to bootstrap node {node}")
            except Exception as e:
                logger.error(f"Error connecting to bootstrap node {node}: {e}")
        
        # Broadcast to local network
        try:
            broadcast_addr = ('<broadcast>', self.port)
            self.discovery_socket.sendto(json.dumps(message).encode('utf-8'), broadcast_addr)
            logger.debug("Broadcasted hello message")
        except Exception as e:
            logger.error(f"Error broadcasting: {e}")
    
    def _get_local_ip(self) -> str:
        """Get the actual local IP address of the machine."""
        try:
            # Create a temporary socket to get the local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"
    
    def _handle_hello_message(self, addr: Tuple[str, int], message: dict):
        logger.debug(f"Handling hello message from {addr}")
        # Don't add ourselves as a peer
        if addr[0] == self.host and addr[1] == self.port:
            logger.debug("Ignoring hello from self")
            return
            
        # Add the peer
        self.peers[addr] = time.time()
        logger.info(f"New peer discovered: {addr}")
        
        # Send response with our shared files
        response = {
            'type': 'hello_response',
            'host': self.host,
            'port': self.port,
            'files': {hash: info['name'] for hash, info in self.local_files.items()}
        }
        try:
            self.discovery_socket.sendto(json.dumps(response).encode('utf-8'), addr)
            logger.debug(f"Sent hello response to {addr}")
        except Exception as e:
            logger.error(f"Error sending hello response to {addr}: {e}")
    
    def _handle_hello_response(self, addr: Tuple[str, int], message: dict):
        logger.debug(f"Handling hello response from {addr}")
        # Don't add ourselves as a peer
        if addr[0] == self.host and addr[1] == self.port:
            logger.debug("Ignoring hello response from self")
            return
            
        # Add the peer
        self.peers[addr] = time.time()
        logger.info(f"Received hello response from: {addr}")
        
        # Update shared files
        if 'files' in message:
            logger.debug(f"Processing {len(message['files'])} files from {addr}")
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
            files_to_remove = []  # Keep track of files to remove
            for file_hash, file_info in self.shared_files.items():
                if peer in file_info['peers']:
                    file_info['peers'].remove(peer)
                    # If no more peers have this file, mark it for removal
                    if not file_info['peers']:
                        files_to_remove.append(file_hash)
            
            # Remove files with no peers after iteration is complete
            for file_hash in files_to_remove:
                del self.shared_files[file_hash]
    
    def _cleanup_peers(self):
        current_time = time.time()
        inactive_threshold = 30
        
        peers_to_remove = []
        for peer, last_seen in self.peers.items():
            if current_time - last_seen > inactive_threshold:
                peers_to_remove.append(peer)
                logger.debug(f"Marking peer {peer} for removal (inactive for {current_time - last_seen:.1f} seconds)")
                
        for peer in peers_to_remove:
            self._remove_peer(peer)
            logger.info(f"Removed inactive peer: {peer}")
    
    def _periodic_discovery(self):
        logger.debug("Starting periodic discovery")
        while self.running:
            self.discover_peers()
            time.sleep(30)
            logger.debug("Performing periodic peer discovery")
    
    def _discovery_loop(self):
        logger.debug("Starting discovery loop")
        while self.running:
            try:
                data, addr = self.discovery_socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                logger.debug(f"Received message from {addr}: {message['type']}")
                
                assert 'type' in message, "Message must have a type field"
                
                if message['type'] == 'hello':
                    self._handle_hello_message(addr, message)
                elif message['type'] == 'hello_response':
                    self._handle_hello_response(addr, message)
                elif message['type'] == 'announce_file':
                    self._handle_file_announcement(addr, message)
                elif message['type'] == 'goodbye':
                    self._remove_peer(addr)
                    logger.info(f"Peer {addr} has left the network")
                
                # Cleanup inactive peers periodically
                self._cleanup_peers()
            
            except Exception as e:
                logger.error(f"Error in discovery loop: {e}")
    
    # =========================================================================
    # File Transfer and Management
    # =========================================================================
    
    def share_file(self, file_path: str) -> str:
        logger.debug(f"Sharing file: {file_path}")
        assert isinstance(file_path, str), "File path must be a string"
        assert os.path.exists(file_path), f"File not found: {file_path}"
        
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        logger.debug(f"File hash: {file_hash}")
        
        file_name = os.path.basename(file_path)
        self.local_files[file_hash] = {'path': file_path, 'name': file_name}
        
        # Announce the file to all peers
        self._announce_file(file_hash, file_name)
        
        # Also add it to our own shared files
        if file_hash not in self.shared_files:
            self.shared_files[file_hash] = {'peers': [], 'name': file_name}
        if (self.host, self.port) not in self.shared_files[file_hash]['peers']:
            self.shared_files[file_hash]['peers'].append((self.host, self.port))
        
        logger.info(f"Shared file {file_name} ({file_hash})")
        return file_hash
    
    def request_file(self, file_hash: str, save_as: str = None) -> str:
        """Request a file from the network and return the path where it was saved"""
        assert isinstance(file_hash, str), "File hash must be a string"
        assert file_hash in self.shared_files, f"File with hash {file_hash} not found in network"
        
        # Get list of peers that have this file
        peers = list(self.shared_files[file_hash]['peers'])  # Create a copy of the peers list
        if not peers:
            raise Exception("No peers available with this file")
        
        # Try to download from each peer until successful
        last_error = None
        failed_peers = []  # Keep track of failed peers
        
        for peer in peers:
            try:
                logger.info(f"Attempting to download from peer {peer}")
                return self._download_from_peer(peer, file_hash, save_as)
            except Exception as e:
                last_error = e
                logger.error(f"Failed to download from peer {peer}: {e}")
                # Only add to failed peers if it's a permanent error
                if not isinstance(e, socket.timeout):
                    failed_peers.append(peer)
        
        # Remove failed peers after iteration is complete
        for peer in failed_peers:
            if peer in self.peers:
                self._remove_peer(peer)
        
        raise Exception(f"Failed to download file from any peer: {last_error}")
    
    def _download_from_peer(self, peer: Tuple[str, int], file_hash: str, save_as: str = None, max_retries: int = 2) -> str:
        """Download a file from a specific peer"""
        assert isinstance(peer, tuple) and len(peer) == 2, "Peer must be a tuple of (host, port)"
        assert isinstance(file_hash, str), "File hash must be a string"
        
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                # Create a TCP connection to the peer with timeout
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(30)  # Increased timeout to 30 seconds
                
                # Try to connect to the peer
                logger.debug(f"Attempting to connect to peer {peer} (attempt {attempt + 1}/{max_retries + 1})")
                sock.connect(peer)
                
                # Send file request
                request = {
                    'type': 'file_request',
                    'file_hash': file_hash
                }
                sock.sendall(json.dumps(request).encode('utf-8'))
                
                # Receive initial response with timeout
                response_data = sock.recv(1024)
                if not response_data:
                    raise Exception("No response received from peer")
                    
                response = json.loads(response_data.decode('utf-8'))
                if response['type'] != 'file_data':
                    raise Exception(f"Unexpected response type: {response['type']}")
                
                # Create save directory if it doesn't exist
                save_dir = os.path.join(os.path.expanduser('~'), 'Downloads', 'P2P_Files')
                os.makedirs(save_dir, exist_ok=True)
                
                # Determine save path
                if save_as is None:
                    save_as = self.shared_files[file_hash]['name']
                save_path = os.path.join(save_dir, save_as)
                
                # Receive and save file with progress tracking
                total_bytes = 0
                with open(save_path, 'wb') as f:
                    while True:
                        try:
                            data = sock.recv(8192)
                            if not data:
                                break
                            f.write(data)
                            total_bytes += len(data)
                            logger.debug(f"Downloaded {total_bytes} bytes from {peer}")
                        except socket.timeout:
                            if total_bytes == 0:
                                raise Exception("Timeout while receiving file data")
                            # If we've received some data, continue
                            continue
                
                if total_bytes == 0:
                    raise Exception("No data received from peer")
                
                # Verify file hash
                with open(save_path, 'rb') as f:
                    received_hash = hashlib.sha256(f.read()).hexdigest()
                
                if received_hash != file_hash:
                    os.remove(save_path)
                    raise Exception("File hash verification failed")
                
                logger.info(f"Successfully downloaded file from {peer}")
                return save_path
                
            except socket.timeout:
                last_error = Exception(f"Connection to peer {peer} timed out")
                logger.error(f"Timeout on attempt {attempt + 1}/{max_retries + 1} for peer {peer}")
                if attempt < max_retries:
                    time.sleep(1)  # Wait a bit before retrying
                    continue
            except ConnectionRefusedError:
                last_error = Exception(f"Connection to peer {peer} was refused")
                break  # Don't retry on connection refused
            except Exception as e:
                last_error = e
                logger.error(f"Error downloading from peer {peer}: {e}")
                break  # Don't retry on other errors
            finally:
                try:
                    sock.close()
                except:
                    pass
        
        raise last_error
    
    def _transfer_loop(self):
        """Handle incoming file transfer requests"""
        while self.running:
            try:
                client_socket, addr = self.transfer_socket.accept()
                threading.Thread(target=self._handle_transfer_request, 
                               args=(client_socket, addr)).start()
            except Exception as e:
                if self.running:
                    logger.error(f"Error in transfer loop: {e}")
    
    def _handle_transfer_request(self, client_socket: socket.socket, addr: Tuple[str, int]):
        """Handle an incoming file transfer request"""
        try:
            # Receive request
            data = client_socket.recv(1024)
            if not data:
                return
            
            request = json.loads(data.decode('utf-8'))
            assert 'type' in request, "Request must have a type field"
            
            if request['type'] == 'file_request':
                self._handle_file_request(client_socket, addr, request)
            else:
                logger.error(f"Unknown request type: {request['type']}")
        
        except Exception as e:
            logger.error(f"Error handling transfer request from {addr}: {e}")
        finally:
            client_socket.close()
    
    def _handle_file_request(self, client_socket: socket.socket, addr: Tuple[str, int], request: dict):
        """Handle a file request from a peer"""
        assert 'file_hash' in request, "File request must include file_hash"
        
        try:
            file_hash = request['file_hash']
            if file_hash not in self.local_files:
                response = {'type': 'error', 'message': 'File not found'}
                client_socket.sendall(json.dumps(response).encode('utf-8'))
                return
            
            # Send file data response
            response = {'type': 'file_data'}
            client_socket.sendall(json.dumps(response).encode('utf-8'))
            
            # Send file contents with progress tracking
            total_bytes = 0
            with open(self.local_files[file_hash]['path'], 'rb') as f:
                while True:
                    data = f.read(8192)
                    if not data:
                        break
                    try:
                        client_socket.sendall(data)
                        total_bytes += len(data)
                        logger.debug(f"Sent {total_bytes} bytes to {addr}")
                    except socket.timeout:
                        # If we've sent some data, continue
                        if total_bytes > 0:
                            continue
                        raise
            
            logger.info(f"Successfully sent file to {addr}")
            
        except Exception as e:
            logger.error(f"Error handling file request from {addr}: {e}")
            try:
                response = {'type': 'error', 'message': str(e)}
                client_socket.sendall(json.dumps(response).encode('utf-8'))
            except:
                pass
    
    def _announce_file(self, file_hash: str, file_name: str):
        logger.debug(f"Announcing file {file_name} ({file_hash})")
        message = {
            'type': 'announce_file',
            'file_hash': file_hash,
            'file_name': file_name,
            'host': self.host,
            'port': self.port
        }
        
        # Announce to all peers
        for peer in self.peers:
            try:
                self.discovery_socket.sendto(json.dumps(message).encode('utf-8'), peer)
                logger.debug(f"Announced file to peer {peer}")
            except Exception as e:
                logger.error(f"Error announcing file to peer {peer}: {e}")
        
        # Also announce to bootstrap nodes
        for node in self.bootstrap_nodes:
            if node not in self.peers:
                try:
                    self.discovery_socket.sendto(json.dumps(message).encode('utf-8'), node)
                    logger.debug(f"Announced file to bootstrap node {node}")
                except Exception as e:
                    logger.error(f"Error announcing file to bootstrap node {node}: {e}") 