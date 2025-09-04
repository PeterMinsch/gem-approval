import re
from typing import Dict, List, Set

class DuplicateDetector:
    def __init__(self, config: Dict):
        self.config = config
        self.commented_posts: Set[str] = set()

    def already_commented(self, existing_comments: List[str]) -> bool:
        for comment in existing_comments:
            comment_lower = comment.lower()
            if any(indicator in comment_lower for indicator in [
                "bravo creations",
                self.config["phone"],
                "bravocreations.com",
                "welcome.bravocreations.com"
            ]):
                return True
        return False

    def is_duplicate_post(self, post_text: str, post_url: str) -> bool:
        if post_url in self.commented_posts:
            return True
        post_text_normalized = re.sub(r'\s+', ' ', post_text.lower().strip())
        return False
