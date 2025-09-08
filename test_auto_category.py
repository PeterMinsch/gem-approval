"""Test script for auto-category functionality"""

def test_category_detection():
    """Test the category detection system"""
    from bot.classifier import PostClassifier
    from bot.bravo_config import CONFIG
    
    classifier = PostClassifier(CONFIG)
    
    test_cases = [
        {
            "text": "Looking for someone to cast this engagement ring design",
            "expected_categories": ["RINGS", "CASTING"]
        },
        {
            "text": "Need help with stone setting on custom necklace",
            "expected_categories": ["NECKLACES", "SETTING"]
        },
        {
            "text": "ISO CAD designer for bracelet project", 
            "expected_categories": ["BRACELETS", "CAD"]
        },
        {
            "text": "Beautiful earrings! Love the engraving work",
            "expected_categories": ["EARRINGS", "ENGRAVING"]
        },
        {
            "text": "Generic jewelry question",
            "expected_categories": ["GENERIC"]
        }
    ]
    
    print("Testing Category Detection System")
    print("=" * 50)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {case['text'][:40]}...")
        
        # Run classification
        classification = classifier.classify_post(case["text"])
        categories = classifier.detect_jewelry_categories(case["text"], classification)
        
        print(f"  Post Type: {classification.post_type}")
        print(f"  Detected: {categories}")
        print(f"  Expected: {case['expected_categories']}")
        
        # Check if any expected category was found
        found_expected = any(cat in categories for cat in case['expected_categories'])
        print(f"  Result: {'PASS' if found_expected else 'FAIL'}")

def test_database_integration():
    """Test database category storage and retrieval"""
    from bot.database import db
    
    print("\nTesting Database Integration")
    print("=" * 50)
    
    # Test adding categories
    categories = ["RINGS", "CASTING"]
    comment_id = db.add_to_comment_queue(
        post_url="https://facebook.com/test",
        post_text="Test ring casting post", 
        comment_text="Test comment",
        post_type="service",
        detected_categories=categories
    )
    
    print(f"Added comment ID: {comment_id}")
    
    # Test retrieving categories
    retrieved = db.get_comment_categories(comment_id)
    
    print(f"Stored: {categories}")
    print(f"Retrieved: {retrieved}")
    print(f"Match: {'PASS' if categories == retrieved else 'FAIL'}")

if __name__ == "__main__":
    test_category_detection()
    test_database_integration()