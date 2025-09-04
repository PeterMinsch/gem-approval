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
