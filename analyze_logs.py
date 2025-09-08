"""
Quick log analysis to find what's taking so long
"""

import re
from datetime import datetime

def analyze_timing_from_logs():
    """Find timing patterns in the logs"""
    
    log_file = r"C:\Users\petem\personal\gem-approval\bot\logs\facebook_comment_bot_20250903_112409.log"
    
    print("ANALYZING BOT PERFORMANCE FROM LOGS")
    print("=" * 50)
    
    # Read the log file
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find post processing sequences
    post_starts = []
    post_completions = []
    
    for line in lines:
        if "Processing post:" in line:
            # Extract timestamp 
            timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3}', line)
            if timestamp_match:
                post_starts.append(datetime.strptime(timestamp_match.group(1), "%Y-%m-%d %H:%M:%S"))
        elif "Comment queued for approval" in line or "Post filtered out" in line or "Skipping post" in line:
            timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d{3}', line)
            if timestamp_match:
                post_completions.append(datetime.strptime(timestamp_match.group(1), "%Y-%m-%d %H:%M:%S"))
    
    print(f"Found {len(post_starts)} post starts and {len(post_completions)} completions")
    
    # Calculate processing times
    processing_times = []
    for i in range(min(len(post_starts), len(post_completions))):
        if i < len(post_starts) and i < len(post_completions):
            duration = (post_completions[i] - post_starts[i]).total_seconds()
            processing_times.append(duration)
            print(f"Post {i+1}: {duration:.1f} seconds")
    
    if processing_times:
        avg_time = sum(processing_times) / len(processing_times)
        max_time = max(processing_times)
        min_time = min(processing_times)
        
        print(f"\nTIMING SUMMARY:")
        print(f"  Average: {avg_time:.1f} seconds")
        print(f"  Max: {max_time:.1f} seconds") 
        print(f"  Min: {min_time:.1f} seconds")
        
        if avg_time > 30:
            print(f"\nSTILL TOO SLOW: {avg_time:.1f}s average")
        elif avg_time > 15:
            print(f"\nIMPROVEMENT NEEDED: {avg_time:.1f}s average")
        else:
            print(f"\nGOOD PERFORMANCE: {avg_time:.1f}s average")
    
    # Look for specific bottlenecks
    print(f"\nCHECKING FOR BOTTLENECKS:")
    
    slow_operations = []
    for line in lines[-1000:]:  # Check last 1000 lines
        # Look for operations that might be slow
        if any(keyword in line for keyword in ["timeout", "wait", "slow", "failed", "retry"]):
            if "INFO" in line or "WARNING" in line or "ERROR" in line:
                slow_operations.append(line.strip())
    
    if slow_operations:
        print("  Recent slow operations:")
        for op in slow_operations[-5:]:  # Last 5
            print(f"    - {op}")
    else:
        print("  No obvious slow operations found in recent logs")
    
    # Check for author extraction logs (our optimization)
    author_extractions = []
    for line in lines[-1000:]:
        if "Starting author extraction" in line or "Found author" in line or "No author found" in line:
            author_extractions.append(line.strip())
    
    if author_extractions:
        print(f"\nAUTHOR EXTRACTION STATUS:")
        for extraction in author_extractions[-5:]:
            print(f"    - {extraction}")
    else:
        print(f"\nAUTHOR EXTRACTION: No recent logs found (optimization may not be running)")

if __name__ == "__main__":
    try:
        analyze_timing_from_logs()
    except FileNotFoundError:
        print("Log file not found. Make sure the bot has been running recently.")
    except Exception as e:
        print(f"Analysis failed: {e}")