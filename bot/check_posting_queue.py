#!/usr/bin/env python3
"""Quick check to see if posting queue is available"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_posting_queue_status():
    """Check if the bot instance has a posting queue"""
    
    print("=== Checking Posting Queue Status ===")
    
    try:
        # Import the API module to access bot_instance
        from api import bot_instance
        
        if not bot_instance:
            print("[FAIL] No bot instance found")
            print("The bot needs to be started first via /bot/start endpoint")
            return False
        
        print("[OK] Bot instance exists")
        
        # Check if posting queue exists
        if hasattr(bot_instance, 'posting_queue'):
            print("[OK] Posting queue attribute exists")
            
            # Check if it's initialized
            if bot_instance.posting_queue:
                print("[OK] Posting queue is initialized")
                print(f"Queue size: {bot_instance.posting_queue.qsize()}")
                return True
            else:
                print("[FAIL] Posting queue is None")
                return False
        else:
            print("[FAIL] No posting_queue attribute found")
            print("The start_posting_thread() method hasn't been called")
            return False
            
    except Exception as e:
        print(f"[FAIL] Error checking posting queue: {e}")
        return False

def suggest_solution():
    """Suggest what to do based on the status"""
    print("\n=== Solution ===")
    print("To fix the posting queue issue:")
    print("1. Stop the current bot if running")
    print("2. Restart the bot via the /bot/start API endpoint")
    print("3. The new code will initialize the posting thread")
    print("4. Then try approving comments for posting")
    
    print("\nYou can restart the bot by:")
    print("- Stopping current bot: POST /bot/stop")  
    print("- Starting new bot: POST /bot/start")
    print("- Or restart the entire API server")

if __name__ == "__main__":
    success = check_posting_queue_status()
    
    if success:
        print("\n[SUCCESS] Posting queue is ready!")
    else:
        print("\n[FAIL] Posting queue needs to be initialized")
        suggest_solution()