#!/usr/bin/env python3
"""
Clear test data from comment queue
"""
from database import db

def clear_test_data():
    """Clear all pending comments from the queue"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM comment_queue WHERE status = 'pending'")
            deleted_count = cursor.rowcount
            conn.commit()
            print(f"Cleared {deleted_count} pending comments from queue")
    except Exception as e:
        print(f"Error clearing test data: {e}")

if __name__ == "__main__":
    clear_test_data()