import time
from typing import Dict, Any

class ProgressTracker:
    def __init__(self):
        self.operations: Dict[str, Dict[str, Any]] = {}
    
    def start_operation(self, operation_id: str, session_id: str):
        """Start tracking an operation"""
        self.operations[operation_id] = {
            'session_id': session_id,
            'start_time': time.time(),
            'status': 'running',
            'progress': 'Starting...'
        }
    
    def update_progress(self, operation_id: str, progress: str):
        """Update operation progress"""
        if operation_id in self.operations:
            self.operations[operation_id]['progress'] = progress
    
    def complete_operation(self, operation_id: str, success: bool, error: str = None):
        """Mark operation as complete"""
        if operation_id in self.operations:
            op = self.operations[operation_id]
            op['status'] = 'success' if success else 'error'
            op['end_time'] = time.time()
            op['duration'] = op['end_time'] - op['start_time']
            if error:
                op['error'] = error
    
    def get_operation_status(self, operation_id: str):
        """Get current operation status"""
        return self.operations.get(operation_id, {})