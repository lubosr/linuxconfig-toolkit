"""
Database connection utilities for LinuxConfig Toolkit
Handles connections to both toolkit DB and WordPress staging DB
"""
import os
import MySQLdb
from contextlib import contextmanager


class DatabaseConnection:
    """Manages database connections"""
    
    @staticmethod
    @contextmanager
    def get_toolkit_connection():
        """Get connection to toolkit database"""
        conn = MySQLdb.connect(
            host=os.getenv('TOOLKIT_DB_HOST', 'mariadb'),
            port=int(os.getenv('TOOLKIT_DB_PORT', 3306)),
            user=os.getenv('TOOLKIT_DB_USER', 'toolkit_user'),
            passwd=os.getenv('TOOLKIT_DB_PASSWORD'),
            db=os.getenv('TOOLKIT_DB_NAME', 'linuxconfig_toolkit'),
            charset='utf8mb4'
        )
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    @staticmethod
    @contextmanager
    def get_wordpress_connection():
        """Get connection to WordPress staging database"""
        conn = MySQLdb.connect(
            host=os.getenv('WP_DB_HOST', '192.168.100.3'),
            port=int(os.getenv('WP_DB_PORT', 3306)),
            user=os.getenv('WP_DB_USER'),
            passwd=os.getenv('WP_DB_PASSWORD'),
            db=os.getenv('WP_DB_NAME'),
            charset='utf8mb4'
        )
        try:
            yield conn
        finally:
            conn.close()


def execute_query(conn, query, params=None):
    """Execute a query and return results"""
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(query, params or ())
    results = cursor.fetchall()
    cursor.close()
    return results


def execute_insert(conn, query, params=None):
    """Execute an insert and return last insert ID"""
    cursor = conn.cursor()
    cursor.execute(query, params or ())
    last_id = cursor.lastrowid
    cursor.close()
    return last_id


def execute_update(conn, query, params=None):
    """Execute an update and return affected rows"""
    cursor = conn.cursor()
    affected = cursor.execute(query, params or ())
    cursor.close()
    return affected
