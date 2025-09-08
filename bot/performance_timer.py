"""
Performance timing decorator and logger for Facebook Comment Bot
Tracks method execution times to identify bottlenecks during post navigation.
"""

import time
import functools
import logging
from typing import Dict, List, Tuple
from pathlib import Path

class PerformanceTimer:
    """Singleton class to manage performance timing and logging"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.setup_logger()
            self.timing_data: Dict[str, List[float]] = {}
            self.slow_threshold = 2.0  # seconds
            self.session_start = time.time()
            PerformanceTimer._initialized = True
    
    def setup_logger(self):
        """Set up dedicated performance logger"""
        # Ensure logs directory exists
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Create performance logger
        self.logger = logging.getLogger('performance')
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            logs_dir / 'performance.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3
        )
        
        # Format for performance logs
        formatter = logging.Formatter(
            '%(asctime)s - PERF - %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Log session start
        self.logger.info("=" * 60)
        self.logger.info("PERFORMANCE TIMING SESSION STARTED")
        self.logger.info("=" * 60)
    
    def record_timing(self, method_name: str, duration: float, class_name: str = None):
        """Record timing data for a method"""
        full_name = f"{class_name}.{method_name}" if class_name else method_name
        
        # Store timing data
        if full_name not in self.timing_data:
            self.timing_data[full_name] = []
        self.timing_data[full_name].append(duration)
        
        # Log the timing
        status_icon = "SLOW" if duration >= self.slow_threshold else "FAST"
        self.logger.info(f"[{status_icon}] {full_name}: {duration:.3f}s")
        
        # Log warning for slow methods
        if duration >= self.slow_threshold:
            self.logger.warning(f"SLOW METHOD DETECTED: {full_name} took {duration:.3f}s (threshold: {self.slow_threshold}s)")
    
    def log_summary(self):
        """Log performance summary for the session"""
        if not self.timing_data:
            return
        
        self.logger.info("-" * 60)
        self.logger.info("PERFORMANCE SUMMARY")
        self.logger.info("-" * 60)
        
        slow_methods = []
        fast_methods = []
        total_time = 0
        
        for method_name, timings in self.timing_data.items():
            avg_time = sum(timings) / len(timings)
            max_time = max(timings)
            call_count = len(timings)
            total_method_time = sum(timings)
            total_time += total_method_time
            
            method_info = {
                'name': method_name,
                'avg': avg_time,
                'max': max_time,
                'count': call_count,
                'total': total_method_time
            }
            
            if avg_time >= self.slow_threshold:
                slow_methods.append(method_info)
            else:
                fast_methods.append(method_info)
        
        # Sort by total time (most time-consuming first)
        slow_methods.sort(key=lambda x: x['total'], reverse=True)
        fast_methods.sort(key=lambda x: x['total'], reverse=True)
        
        # Log slow methods
        if slow_methods:
            self.logger.info("SLOW METHODS (>=2.0s avg):")
            for method in slow_methods:
                self.logger.info(f"   {method['name']}: avg={method['avg']:.3f}s, max={method['max']:.3f}s, calls={method['count']}, total={method['total']:.3f}s")
        
        # Log top 5 fast methods by total time
        if fast_methods:
            self.logger.info("TOP FAST METHODS by total time:")
            for method in fast_methods[:5]:
                self.logger.info(f"   {method['name']}: avg={method['avg']:.3f}s, max={method['max']:.3f}s, calls={method['count']}, total={method['total']:.3f}s")
        
        session_duration = time.time() - self.session_start
        self.logger.info(f"SESSION DURATION: {session_duration:.1f}s")
        self.logger.info(f"TOTAL MEASURED TIME: {total_time:.1f}s")
        self.logger.info(f"TOTAL METHOD CALLS: {sum(len(timings) for timings in self.timing_data.values())}")
        self.logger.info("=" * 60)

# Global timer instance
perf_timer = PerformanceTimer()

def time_method(func):
    """Decorator to time method execution"""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            # Still record timing even if method fails
            duration = time.time() - start_time
            class_name = args[0].__class__.__name__ if args and hasattr(args[0], '__class__') else None
            perf_timer.record_timing(func.__name__, duration, class_name)
            perf_timer.logger.error(f"ERROR: {class_name}.{func.__name__} FAILED after {duration:.3f}s: {e}")
            raise
        finally:
            # Record timing
            duration = time.time() - start_time
            class_name = args[0].__class__.__name__ if args and hasattr(args[0], '__class__') else None
            perf_timer.record_timing(func.__name__, duration, class_name)
    
    return wrapper

def log_performance_summary():
    """Utility function to log performance summary"""
    perf_timer.log_summary()