import os
import logging
from datetime import datetime

def setup_logger():
    os.makedirs('logs', exist_ok=True)
    log_filename = f'logs/facebook_comment_bot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)
