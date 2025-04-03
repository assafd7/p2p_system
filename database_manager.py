import sqlite3
import hashlib
from datetime import datetime

class DatabaseManager:
    """Manages all database operations for the P2P system."""

    def __init__(self, db_name='p2p_system.db'):
        self.db_name = db_name
        self.setup_database()

    def setup_database(self):
        """Initialize the database with necessary tables."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at TEXT NOT NULL,
            last_login TEXT
        )
        ''')

        # Create files index table (for future use)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            file_id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES users (user_id)
        )
        ''')

        # Create shared_fidles table (for future use)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS shared_files (
            share_id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            shared_with_id INTEGER NOT NULL,
            shared_at TEXT NOT NULL,
            FOREIGN KEY (file_id) REFERENCES files (file_id),
            FOREIGN KEY (shared_with_id) REFERENCES users (user_id)
        )
        ''')

        conn.commit()
        conn.close()
        print("Database setup complete.")

    def hash_password(self, password):
        """Convert password to secure hash."""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password, email=None):
        """Register a new user in the database."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            hashed_password = self.hash_password(password)
            created_at = datetime.now().isoformat()

            cursor.execute(
                "INSERT INTO users (username, password_hash, email, created_at) VALUES (?, ?, ?, ?)",
                (username, hashed_password, email, created_at)
            )

            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Username or email already exists
            conn.close()
            return False
        except Exception as e:
            print(f"Error registering user: {e}")
            conn.close()
            return False

    def authenticate_user(self, username, password):
        """Authenticate a user based on username and password."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            hashed_password = self.hash_password(password)

            cursor.execute(
                "SELECT user_id FROM users WHERE username = ? AND password_hash = ?",
                (username, hashed_password)
            )

            result = cursor.fetchone()

            if result:
                # Update last login time
                cursor.execute(
                    "UPDATE users SET last_login = ? WHERE user_id = ?",
                    (datetime.now().isoformat(), result[0])
                )
                conn.commit()

            conn.close()
            return result is not None
        except Exception as e:
            print(f"Error authenticating user: {e}")
            conn.close()
            return False

