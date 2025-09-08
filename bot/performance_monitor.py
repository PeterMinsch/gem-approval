"""
Performance Monitor for Facebook Comment Bot
Adds detailed timing and performance tracking to identify bottlenecks
"""

import time
import logging
import os
from functools import wraps
from typing import Dict, List
from datetime import datetime

# Try to import psutil, fall back to basic monitoring if not available
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("Warning: psutil not available. Basic monitoring only.")

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Tracks timing and performance metrics for the bot"""
    
    def __init__(self):
        self.timings: Dict[str, List[float]] = {}
        self.slow_operations: List[Dict] = []
        self.start_time = time.time()
        
    def timing_decorator(self, operation_name: str, slow_threshold: float = 10.0):
        """Decorator to time function execution"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    self._record_timing(operation_name, duration, slow_threshold)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    logger.error(f"❌ {operation_name} failed after {duration:.2f}s: {e}")
                    self._record_timing(f"{operation_name}_FAILED", duration, slow_threshold)
                    raise
            return wrapper
        return decorator
    
    def _record_timing(self, operation: str, duration: float, slow_threshold: float):
        """Record timing data"""
        # Store in timings dict
        if operation not in self.timings:
            self.timings[operation] = []
        self.timings[operation].append(duration)
        
        # Log timing
        if duration > slow_threshold:
            logger.warning(f"🐌 SLOW: {operation} took {duration:.2f}s (threshold: {slow_threshold}s)")
            self.slow_operations.append({
                'operation': operation,
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            })
        else:
            logger.info(f"⏱️ {operation}: {duration:.2f}s")
    
    def time_operation(self, operation_name: str):
        """Context manager for timing operations"""
        class TimingContext:
            def __init__(self, monitor, name):
                self.monitor = monitor
                self.name = name
                self.start_time = None
                
            def __enter__(self):
                self.start_time = time.time()
                logger.info(f"🚀 Starting: {self.name}")
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                if exc_type:
                    self.monitor._record_timing(f"{self.name}_FAILED", duration, 5.0)
                else:
                    self.monitor._record_timing(self.name, duration, 5.0)
        
        return TimingContext(self, operation_name)
    
    def get_system_metrics(self) -> Dict:
        """Get current system resource usage"""
        if HAS_PSUTIL:
            try:
                process = psutil.Process(os.getpid())
                return {
                    'memory_mb': process.memory_info().rss / 1024 / 1024,
                    'cpu_percent': process.cpu_percent(),
                    'uptime_minutes': (time.time() - self.start_time) / 60,
                    'chrome_processes': self._count_chrome_processes()
                }
            except:
                pass
        
        # Fallback basic metrics
        return {
            'memory_mb': 0,
            'cpu_percent': 0,
            'uptime_minutes': (time.time() - self.start_time) / 60,
            'chrome_processes': 0
        }
    
    def _count_chrome_processes(self) -> int:
        """Count running Chrome processes"""
        count = 0
        if HAS_PSUTIL:
            try:
                for proc in psutil.process_iter(['name']):
                    if 'chrome' in proc.info['name'].lower():
                        count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return count
    
    def print_performance_summary(self):
        """Print comprehensive performance summary"""
        print("\n" + "="*60)
        print("📊 PERFORMANCE SUMMARY")
        print("="*60)
        
        # System metrics
        metrics = self.get_system_metrics()
        print(f"💾 Memory Usage: {metrics['memory_mb']:.1f}MB")
        print(f"🖥️ CPU Usage: {metrics['cpu_percent']:.1f}%")
        print(f"⏰ Runtime: {metrics['uptime_minutes']:.1f} minutes")
        print(f"🌐 Chrome Processes: {metrics['chrome_processes']}")
        
        print("\n📈 TIMING STATISTICS:")
        for operation, times in self.timings.items():
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                min_time = min(times)
                print(f"  {operation}:")
                print(f"    - Avg: {avg_time:.2f}s | Max: {max_time:.2f}s | Min: {min_time:.2f}s | Count: {len(times)}")
        
        print(f"\n🐌 SLOW OPERATIONS ({len(self.slow_operations)} total):")
        for slow_op in self.slow_operations[-5:]:  # Show last 5
            print(f"  - {slow_op['operation']}: {slow_op['duration']:.2f}s at {slow_op['timestamp']}")
        
        print("="*60 + "\n")

# Global performance monitor instance
perf_monitor = PerformanceMonitor()

def time_facebook_operation(operation_name: str, slow_threshold: float = 5.0):
    """Decorator specifically for Facebook operations"""
    return perf_monitor.timing_decorator(operation_name, slow_threshold)

def diagnose_webdriver_performance(driver):
    """Diagnose WebDriver and browser performance"""
    print("\n🔍 WEBDRIVER DIAGNOSIS")
    print("-" * 40)
    
    try:
        caps = driver.capabilities
        print(f"Browser: {caps.get('browserName', 'Unknown')} {caps.get('browserVersion', '')}")
        print(f"Driver: {caps.get('chrome', {}).get('chromedriverVersion', 'Unknown')}")
        
        # Test basic operations
        with perf_monitor.time_operation("Navigate to Facebook"):
            driver.get("https://facebook.com")
        
        with perf_monitor.time_operation("Find page elements"):
            elements = driver.find_elements("tag name", "div")
            print(f"Found {len(elements)} div elements")
        
        # Check for performance-impacting factors
        handles = driver.window_handles
        print(f"Open browser tabs/windows: {len(handles)}")
        
    except Exception as e:
        logger.error(f"WebDriver diagnosis failed: {e}")

def diagnose_network_performance():
    """Test network connectivity to Facebook"""
    print("\n🌐 NETWORK DIAGNOSIS")
    print("-" * 40)
    
    import requests
    import socket
    
    try:
        # Test Facebook connectivity
        with perf_monitor.time_operation("HTTP Request to Facebook"):
            response = requests.get("https://facebook.com", timeout=10)
            print(f"Status Code: {response.status_code}")
        
        # Test DNS resolution
        with perf_monitor.time_operation("DNS Resolution"):
            ip = socket.gethostbyname("facebook.com")
            print(f"Facebook IP: {ip}")
            
    except Exception as e:
        logger.error(f"Network diagnosis failed: {e}")

def create_performance_test_post_processor():
    """Create a single post processor for performance testing"""
    
    @time_facebook_operation("Full Post Processing", slow_threshold=30.0)
    def process_single_post_for_testing(bot, post_url: str):
        """Process a single post with detailed timing"""
        
        with perf_monitor.time_operation("Navigate to Post"):
            bot.driver.get(post_url)
        
        with perf_monitor.time_operation("Extract Post Text"):
            if bot.post_extractor:
                post_text = bot.post_extractor.get_post_text()
            else:
                post_text = "No post extractor available"
        
        with perf_monitor.time_operation("Extract Author"):
            if bot.post_extractor:
                author = bot.post_extractor.get_post_author()
            else:
                author = "No post extractor available"
        
        with perf_monitor.time_operation("Extract Images"):
            if bot.post_extractor:
                image_url = bot.post_extractor.extract_first_image_url()
            else:
                image_url = None
        
        # System resource check
        metrics = perf_monitor.get_system_metrics()
        if metrics['memory_mb'] > 300:
            logger.warning(f"🚨 High memory usage: {metrics['memory_mb']:.1f}MB")
        
        return {
            'post_text': post_text,
            'author': author, 
            'image_url': image_url,
            'metrics': metrics
        }
    
    return process_single_post_for_testing

if __name__ == "__main__":
    # Example usage
    print("Performance Monitor initialized")
    print("Use perf_monitor.print_performance_summary() to see results")
    print("Use @time_facebook_operation('Operation Name') decorator on functions")
    print("Use 'with perf_monitor.time_operation('Name'):' for code blocks")