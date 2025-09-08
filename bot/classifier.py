from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
import logging

KEYWORD_WEIGHTS = {
    "negative": -100,
    "brand_blacklist": -50,
    "service": 8,
    "iso": 6,
    "general": 3,
    "modifier": 15,
}

POST_TYPE_THRESHOLDS = {
    "service": 15,
    "iso": 10,
    "general": 8,
    "skip": -25,
}

@dataclass
class PostClassification:
    post_type: str
    confidence_score: float
    keyword_matches: Dict[str, List[str]]
    reasoning: List[str]
    should_skip: bool

class PostClassifier:
    def __init__(self, config: Dict):
        self.config = config
        self.processed_posts: Set[str] = set()

    def calculate_keyword_score(self, text: str, keyword_list: List[str], weight: float) -> Tuple[float, List[str]]:
        text_lower = text.lower()
        matches = []
        score = 0.0
        for keyword in keyword_list:
            if keyword.lower() in text_lower:
                matches.append(keyword)
                score += weight
        return score, matches

    def check_brand_blacklist(self, text: str) -> Tuple[float, List[str], List[str]]:
        brand_score, brand_matches = self.calculate_keyword_score(
            text, self.config["brand_blacklist"], KEYWORD_WEIGHTS["brand_blacklist"]
        )
        modifier_score, modifier_matches = self.calculate_keyword_score(
            text, self.config["allowed_brand_modifiers"], KEYWORD_WEIGHTS["modifier"]
        )
        if brand_matches and not modifier_matches:
            brand_score = -100
        return brand_score, brand_matches, modifier_matches

    def classify_post(self, text: str) -> PostClassification:
        logger = logging.getLogger(__name__)
        logger.info(f"Classifying post text: {text[:100]}...")
        total_score = 0.0
        keyword_matches = {}
        reasoning = []
        neg_score, neg_matches = self.calculate_keyword_score(
            text, self.config["negative_keywords"], KEYWORD_WEIGHTS["negative"]
        )
        if neg_matches:
            keyword_matches["negative"] = neg_matches
            reasoning.append(f"Negative keywords found: {neg_matches}")
            return PostClassification(
                post_type="skip",
                confidence_score=abs(neg_score),
                keyword_matches=keyword_matches,
                reasoning=reasoning,
                should_skip=True
            )
        brand_score, brand_matches, modifier_matches = self.check_brand_blacklist(text)
        total_score += brand_score
        if brand_matches:
            keyword_matches["brand_blacklist"] = brand_matches
            if modifier_matches:
                keyword_matches["modifiers"] = modifier_matches
                reasoning.append(f"Blacklisted brands found but allowed modifiers present: {modifier_matches}")
            else:
                reasoning.append(f"Blacklisted brands found without modifiers: {brand_matches}")
                return PostClassification(
                    post_type="skip",
                    confidence_score=abs(brand_score),
                    keyword_matches=keyword_matches,
                    reasoning=reasoning,
                    should_skip=True
                )
        service_score, service_matches = self.calculate_keyword_score(
            text, self.config["service_keywords"], KEYWORD_WEIGHTS["service"]
        )
        iso_score, iso_matches = self.calculate_keyword_score(
            text, self.config["iso_keywords"], KEYWORD_WEIGHTS["iso"]
        )
        general_score, general_matches = self.calculate_keyword_score(
            text, self.config["general_keywords"], KEYWORD_WEIGHTS["general"]
        )
        if service_matches:
            keyword_matches["service"] = service_matches
            reasoning.append(f"Service keywords found: {service_matches[:5]}...")
        if iso_matches:
            keyword_matches["iso"] = iso_matches
            reasoning.append(f"ISO keywords found: {iso_matches[:5]}...")
        if general_matches:
            keyword_matches["general"] = general_matches
            reasoning.append(f"General keywords found: {general_matches[:5]}...")
        post_type = "skip"
        iso_indicators = ["iso", "in stock", "who makes", "who manufactures", "supplier"]
        starts_with_iso = any(text.lower().startswith(indicator) for indicator in iso_indicators)
        service_threshold = self.config.get("post_type_thresholds", {}).get("service", POST_TYPE_THRESHOLDS["service"])
        iso_threshold = self.config.get("post_type_thresholds", {}).get("iso", POST_TYPE_THRESHOLDS["iso"])
        general_threshold = self.config.get("post_type_thresholds", {}).get("general", POST_TYPE_THRESHOLDS["general"])
        if starts_with_iso and iso_score >= iso_threshold:
            post_type = "iso"
            total_score = iso_score
        elif service_score >= service_threshold:
            post_type = "service"
            total_score = service_score
        elif iso_score >= iso_threshold:
            post_type = "iso"
            total_score = iso_score
        elif general_score >= general_threshold:
            post_type = "general"
            total_score = general_score
        logger.info(f"Classification score: {total_score}")
        logger.info(f"Post type: {post_type}")
        logger.info(f"Reasoning: {'; '.join(reasoning)}")
        return PostClassification(
            post_type=post_type,
            confidence_score=total_score,
            keyword_matches=keyword_matches,
            reasoning=reasoning,
            should_skip=(post_type == "skip" or total_score <= self.config.get("post_type_thresholds", {}).get("skip", POST_TYPE_THRESHOLDS["skip"]))
        )

    def detect_jewelry_categories(self, text: str, classification: PostClassification) -> List[str]:
        """
        Detect specific jewelry categories from post text and existing classification.
        
        Args:
            text: The original post text
            classification: Existing PostClassification result
            
        Returns:
            List of relevant image pack categories
        """
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 JEWELRY CATEGORY DETECTION START")
        logger.info(f"📝 Input text: '{text[:100]}...'")
        logger.info(f"📊 Classification: type='{classification.post_type}', score={classification.confidence_score}")
        logger.info(f"🏷️  Classification keywords: {classification.keyword_matches}")
        
        categories = []
        text_lower = text.lower()
        matched_keywords = []
        
        # Enhanced keyword to category mapping with variations
        keyword_to_category = {
            # Jewelry Types - Enhanced with plurals and variations
            # Ring variations - comprehensive
            "ring": "RINGS", "rings": "RINGS",
            "wedding ring": "RINGS", "wedding rings": "RINGS",
            "engagement ring": "RINGS", "engagement rings": "RINGS", 
            "anniversary ring": "RINGS", "anniversary rings": "RINGS",
            "band": "RINGS", "bands": "RINGS",
            "wedding band": "RINGS", "wedding bands": "RINGS",
            "promise ring": "RINGS", "promise rings": "RINGS",
            "signet ring": "RINGS", "signet rings": "RINGS",
            "eternity ring": "RINGS", "eternity rings": "RINGS",
            "class ring": "RINGS", "class rings": "RINGS",
            "cocktail ring": "RINGS", "cocktail rings": "RINGS",
            "solitaire": "RINGS", "solitaires": "RINGS",
            
            "necklace": "NECKLACES", "necklaces": "NECKLACES",
            "pendant": "NECKLACES", "pendants": "NECKLACES",
            "chain": "NECKLACES", "chains": "NECKLACES",
            "choker": "NECKLACES", "chokers": "NECKLACES",
            "locket": "NECKLACES", "lockets": "NECKLACES",
            
            "bracelet": "BRACELETS", "bracelets": "BRACELETS",
            "bangle": "BRACELETS", "bangles": "BRACELETS",
            "tennis bracelet": "BRACELETS", "tennis bracelets": "BRACELETS",
            "charm bracelet": "BRACELETS", "charm bracelets": "BRACELETS",
            
            "earring": "EARRINGS", "earrings": "EARRINGS",
            "stud": "EARRINGS", "studs": "EARRINGS",
            "hoop": "EARRINGS", "hoops": "EARRINGS",
            "drop earring": "EARRINGS", "drop earrings": "EARRINGS",
            "dangle earring": "EARRINGS", "dangle earrings": "EARRINGS",
            
            # Services - Enhanced
            "casting": "CASTING", "cast": "CASTING", 
            "lost wax": "CASTING", "lost wax casting": "CASTING",
            "investment casting": "CASTING",
            
            "cad": "CAD", "3d design": "CAD",
            "stl": "CAD", "3dm": "CAD",
            "matrix": "CAD", "rhino": "CAD",
            "design": "CAD", "3d model": "CAD",
            "computer aided": "CAD",
            
            "stone setting": "SETTING", "setting": "SETTING",
            "prong": "SETTING", "prongs": "SETTING",
            "pavé": "SETTING", "pave": "SETTING",
            "bezel": "SETTING", "bezels": "SETTING",
            "channel": "SETTING", "channel setting": "SETTING",
            "micro setting": "SETTING", "micro pave": "SETTING",
            
            "engraving": "ENGRAVING", "engrave": "ENGRAVING",
            "laser engraving": "ENGRAVING", "hand engraving": "ENGRAVING",
            
            "enamel": "ENAMEL", "enameling": "ENAMEL",
            "color fill": "ENAMEL", "rhodium": "ENAMEL",
            "plating": "ENAMEL", "gold plating": "ENAMEL"
        }
        
        # Enhanced matching: Check for direct keyword matches AND partial matches
        logger.info(f"🔎 Starting keyword matching against {len(keyword_to_category)} keywords")
        
        import re
        for keyword, category in keyword_to_category.items():
            # Direct match
            if keyword in text_lower:
                categories.append(category)
                matched_keywords.append(f"'{keyword}' -> {category}")
                logger.info(f"✅ Direct match: '{keyword}' -> {category}")
            # Word boundary match for better detection
            elif re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                if category not in categories:
                    categories.append(category)
                    matched_keywords.append(f"'{keyword}' (boundary) -> {category}")
                    logger.info(f"✅ Boundary match: '{keyword}' -> {category}")
        
        logger.info(f"🎯 Direct keyword matches found: {len(matched_keywords)}")
        if matched_keywords:
            logger.info(f"📋 Matched keywords: {matched_keywords[:5]}...")  # Show first 5
        
        # Enhanced fallback logic based on classification and keyword analysis  
        if not categories:
            # Analyze the classification's keyword matches for better fallback
            matched_keywords = classification.keyword_matches
            
            # Check if any service-related keywords were found in classification
            service_detected = any(key in matched_keywords for key in ['service', 'general'])
            
            if classification.post_type == "service" or service_detected:
                # For service posts, try to detect specific service types from classification keywords
                service_categories = []
                
                # Check for specific service keywords in the matched keywords
                all_matched = []
                for key_list in matched_keywords.values():
                    all_matched.extend(key_list)
                
                matched_text = " ".join(all_matched).lower()
                
                if any(word in matched_text for word in ['cad', '3d', 'design', 'model']):
                    service_categories.append("CAD")
                if any(word in matched_text for word in ['casting', 'cast', 'wax']):
                    service_categories.append("CASTING") 
                if any(word in matched_text for word in ['setting', 'stone', 'prong', 'bezel']):
                    service_categories.append("SETTING")
                if any(word in matched_text for word in ['engraving', 'engrave', 'laser']):
                    service_categories.append("ENGRAVING")
                    
                # Default service categories if none detected
                categories = service_categories if service_categories else ["CAD", "CASTING", "SETTING"]
                
            elif classification.post_type == "iso":
                # ISO posts - try to detect what they're looking for
                categories = ["RINGS", "NECKLACES", "BRACELETS", "EARRINGS"] # Show all jewelry types
            else:
                # General posts - broader category selection
                categories = ["RINGS", "NECKLACES"] # Most common requests
        
        # Always include GENERIC as fallback for broader selection
        if "GENERIC" not in categories:
            categories.append("GENERIC")
            logger.info("➕ Added GENERIC as fallback category")
        
        # Remove duplicates and return
        final_categories = list(set(categories))
        
        logger.info(f"🏁 FINAL RESULT: {len(final_categories)} categories detected: {final_categories}")
        logger.info(f"🔍 JEWELRY CATEGORY DETECTION END")
        
        return final_categories
