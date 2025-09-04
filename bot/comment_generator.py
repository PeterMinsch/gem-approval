import os
import random
import logging
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class CommentTemplate:
    text: str
    variations: List[str]
    use_count: int = 0

class CommentGenerator:
    def __init__(self, config: Dict, database=None):
        self.config = config
        self.database = database
        self.template_usage = {}
        self._initialize_templates()
        self.openai_client = None
        if self.config.get("openai", {}).get("enabled", False):
            try:
                import openai
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    openai.api_key = api_key
                    self.openai_client = openai
                    logging.getLogger(__name__).info("✅ OpenAI client initialized successfully")
                else:
                    logging.getLogger(__name__).warning("⚠️ OPENAI_API_KEY not found in environment variables")
            except ImportError:
                logging.getLogger(__name__).warning("⚠️ OpenAI package not installed. Install with: pip install openai")
            except Exception as e:
                logging.getLogger(__name__).error(f"❌ Failed to initialize OpenAI client: {e}")

    def _initialize_templates(self):
        # Get unified templates (database + config fallback)
        templates_dict = self._get_unified_templates()
        
        for post_type, templates in templates_dict.items():
            self.template_usage[post_type] = []
            for template in templates:
                self.template_usage[post_type].append(CommentTemplate(
                    text=template,
                    variations=self._generate_variations(template),
                    use_count=0
                ))
    
    def _get_unified_templates(self) -> Dict[str, List[str]]:
        """Get templates from database first, fallback to config"""
        # Try to get templates from database
        if self.database:
            try:
                config_templates = self.config.get("templates", {})
                db_templates = self.database.get_unified_templates(config_templates)
                if db_templates:
                    # Convert database format to the expected dict format
                    templates_dict = {}
                    
                    # Map database categories back to post types
                    category_to_type = {
                        "GENERIC": "general",
                        "ISO_PIVOT": "iso", 
                        "SERVICE_REQUEST": "service"
                    }
                    
                    for post_type in ["service", "iso", "general"]:
                        templates_dict[post_type] = []
                    
                    # Add database templates
                    for template in db_templates:
                        post_type = category_to_type.get(template.get("category"), "general")
                        templates_dict[post_type].append(template["body"])
                    
                    # If we got templates from database, return them
                    if any(templates_dict.values()):
                        logging.getLogger(__name__).info(f"✅ Using unified templates from database: {sum(len(t) for t in templates_dict.values())} total")
                        return templates_dict
                        
            except Exception as e:
                logging.getLogger(__name__).warning(f"⚠️ Failed to get templates from database, using config fallback: {e}")
        
        # Fallback to config templates
        logging.getLogger(__name__).info("ℹ️ Using config templates as fallback")
        return self.config.get("templates", {})
    
    def refresh_templates(self):
        """Refresh templates from database (for real-time updates)"""
        try:
            logging.getLogger(__name__).info("🔄 Refreshing templates from database...")
            self._initialize_templates()
            logging.getLogger(__name__).info("✅ Templates refreshed successfully")
        except Exception as e:
            logging.getLogger(__name__).warning(f"⚠️ Failed to refresh templates: {e}")
    
    def get_template_statistics(self) -> Dict:
        """Get statistics about current templates"""
        stats = {}
        total_templates = 0
        
        for post_type, templates in self.template_usage.items():
            template_count = len(templates)
            total_usage = sum(t.use_count for t in templates)
            stats[post_type] = {
                "count": template_count,
                "total_usage": total_usage,
                "templates": [
                    {"text": t.text[:50] + "...", "use_count": t.use_count} 
                    for t in templates[:3]  # Show first 3 templates
                ]
            }
            total_templates += template_count
        
        stats["total_templates"] = total_templates
        return stats

    def _generate_variations(self, template: str) -> List[str]:
        variations = []
        if "!" in template:
            variations.append(template.replace("!", "."))
        if "." in template:
            variations.append(template.replace(".", "!"))
        if " — " in template:
            variations.append(template.replace(" — ", " • "))
        if " • " in template:
            variations.append(template.replace(" • ", " — "))
        words = template.split()
        if len(words) > 10:
            for i in range(len(words) - 1):
                if random.random() < 0.3:
                    words[i], words[i+1] = words[i+1], words[i]
            variations.append(" ".join(words))
        return variations

    def _generate_llm_comment(self, post_type: str, post_text: str = "", author_name: str = "") -> str:
        try:
            if not self.openai_client:
                return None
            prompt = self.config.get("llm_prompts", {}).get(post_type)
            if not prompt:
                return None
            first_name = self.extract_first_name(author_name) if author_name else ""
            if post_text:
                prompt += f"\n\nPost content: {post_text[:200]}..."
            if first_name:
                prompt += f"\n\nAuthor's first name: {first_name}"
            else:
                prompt += f"\n\nAuthor's first name: not available"
            openai_config = self.config.get("openai", {})
            response = self.openai_client.ChatCompletion.create(
                model=openai_config.get("model", "gpt-4o-mini"),
                messages=[{"role": "system", "content": prompt}],
                max_tokens=openai_config.get("max_tokens", 150),
                temperature=openai_config.get("temperature", 0.7)
            )
            comment = response.choices[0].message['content'].strip() if hasattr(response.choices[0], 'message') else response.choices[0].text.strip()
            return comment
        except Exception:
            return None

    def select_template(self, post_type: str) -> str:
        if post_type not in self.template_usage:
            return None
        templates = self.template_usage[post_type]
        min_usage = min(template.use_count for template in templates)
        candidates = [t for t in templates if t.use_count == min_usage]
        selected = random.choice(candidates)
        selected.use_count += 1
        if selected.variations and random.random() < 0.4:
            return random.choice(selected.variations)
        else:
            return selected.text

    def extract_first_name(self, full_name: str) -> str:
        if not full_name or not isinstance(full_name, str):
            return ""
        full_name = full_name.strip()
        skip_indicators = [
            'sponsored', 'admin', 'moderator', 'page', 'business', 'group',
            'like', 'comment', 'share', 'follow', 'unfollow', 'report',
            'see more', 'hide', 'block', 'message', 'add friend'
        ]
        if any(indicator in full_name.lower() for indicator in skip_indicators):
            return ""
        name_parts = full_name.split()
        if not name_parts:
            return ""
        
        # Skip common titles/prefixes to find the actual first name
        titles = ['dr.', 'dr', 'mr.', 'mr', 'mrs.', 'mrs', 'ms.', 'ms', 'miss', 'prof.', 'prof', 'rev.', 'rev']
        first_name_index = 0
        
        # Skip titles at the beginning
        while first_name_index < len(name_parts) and name_parts[first_name_index].lower().rstrip('.') in titles:
            first_name_index += 1
            
        if first_name_index >= len(name_parts):
            return ""
            
        first_name = name_parts[first_name_index]
        if len(first_name) < 2 or len(first_name) > 20:
            return ""
        if not all(c.isalpha() or c in "'-." for c in first_name):
            return ""
        first_name = first_name.strip("'-.")
        non_names = ['the', 'and', 'or', 'but', 'for', 'with', 'from', 'to', 'at', 'by']
        if first_name.lower() in non_names:
            return ""
        return first_name

    def personalize_comment(self, template: str, author_name: str = "") -> str:
        first_name = self.extract_first_name(author_name) if author_name else ""
        if first_name:
            return template.replace("{{author_name}}", first_name)
        else:
            return template.replace("{{author_name}}", "there")

    def generate_comment(self, post_type: str, post_text: str = "", author_name: str = "") -> str:
        if self.openai_client and self.config.get("openai", {}).get("enabled", False):
            llm_comment = self._generate_llm_comment(post_type, post_text, author_name)
            if llm_comment:
                return self.personalize_comment(llm_comment, author_name)
        if self.config.get("openai", {}).get("fallback_to_templates", True):
            comment = self.select_template(post_type)
            if comment:
                return self.personalize_comment(comment, author_name)
        return None
