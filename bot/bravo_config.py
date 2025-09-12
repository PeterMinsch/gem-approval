CONFIG = {
    "phone": "(760) 431-9977",
    "register_url": "https://welcome.bravocreations.com",
    "image_url": "https://your-cdn/bravo-comment-card.png",
    "CHROME_PROFILE": "Default",  # Your actual Chrome profile
    
    # Feature Flags
    "ENABLE_IMAGE_POSTING": True,  # Set to False to disable image attachments
    "COMMENT_BOX_XPATH": (
        "//div[@contenteditable='true' and @role='textbox' and ("
        "contains(@aria-placeholder, 'Write a public comment') or "
        "contains(@aria-placeholder, 'Write a public comment…') or "
        "contains(@aria-placeholder, 'Write an answer') or "
        "contains(@aria-placeholder, 'Write an answer…') or "
        "contains(@aria-placeholder, 'Write a comment') or "
        "contains(@aria-placeholder, 'Write a comment…') or "
        "contains(@aria-placeholder, 'Write something') or "
        "contains(@aria-placeholder, 'Write something…') or "
        "contains(@aria-placeholder, 'Comment') or "
        "contains(@aria-placeholder, 'Comment…')"
        ")]"
    ),
    
    # Fallback comment box selectors for different Facebook layouts
    "COMMENT_BOX_FALLBACK_XPATHS": [
        "//div[@contenteditable='true' and @role='textbox']",
        "//div[@contenteditable='true']",
        "//div[@role='textbox']",
        "//div[contains(@class, 'comment') and @contenteditable='true']",
        "//div[contains(@class, 'comment') and @role='textbox']",
        "//div[contains(@class, 'input') and @contenteditable='true']",
        "//div[contains(@class, 'input') and @role='textbox']",
        "//div[contains(@class, 'text') and @contenteditable='true']",
        "//div[contains(@class, 'text') and @role='textbox']"
    ],
    
    # Enhanced bot detection safety settings
    "bot_detection_safety": {
        "typing_speed_range": [3.0, 6.0],  # Characters per second range
        "natural_pauses": {
            "sentence_end": [0.3, 0.8],    # Pause after .!?
            "punctuation": [0.1, 0.4],     # Pause after ,;:
            "word_boundary": [0.05, 0.2],  # Pause after space
            "chunk_boundary": [0.5, 1.5],  # Pause between comment chunks
            "pre_click": [0.5, 2.0],       # Pause before clicking
            "post_click": [0.3, 1.5],      # Pause after clicking
            "pre_post": [2.0, 5.0]         # Pause before posting
        },
        "mouse_movement": {
            "jiggle_moves": [2, 4],        # Number of mouse jiggles
            "jiggle_range": [3, 8],        # Pixel range for jiggles
            "waypoint_count": [2, 4],      # Waypoints for long movements
            "curve_variation": [15, 25]    # Pixel variation for curves
        },
        "typing_errors": {
            "error_probability": 0.05,     # 5% chance of typing error
            "correction_probability": 0.5   # 50% chance to actually make error
        },
        "random_behavior": {
            "scroll_probability": 0.4,     # 40% chance to scroll
            "hover_probability": 0.3,      # 30% chance to hover
            "click_probability": 0.3       # 30% chance to click
        }
    },
    
    # Enhanced keyword scoring system
    "keyword_weights": {
        "negative": -100,      # Strong negative weight
        "brand_blacklist": -50, # Brand blacklist weight
        "service": 8,          # Service keyword weight (reduced from 10)
        "iso": 6,              # ISO keyword weight (reduced from 8)
        "general": 3,          # General keyword weight (reduced from 5)
        "modifier": 15,        # Allowed brand modifier weight
    },
    
    # Post type classification thresholds - LOWERED FOR BETTER COVERAGE
    "post_type_thresholds": {
        "service": 8,          # Lowered from 15 - more posts will qualify as service
        "iso": 6,              # Lowered from 10 - more posts will qualify as ISO
        "general": 4,          # Lowered from 8 - more posts will qualify as general
        "skip": -50,           # Much more lenient - only skip obvious negative posts
    },
    
    # Direct keyword lists for the classifier
    "negative_keywords": [
        "memo", "consignment", "for sale", "wts", "fs", "sold", "giveaway", "admin",
        "rule", "meme", "joke", "loose stone", "loose stones", "findings", "gallery wire", "strip stock",
        "equipment", "tool", "supplies", "auction", "bidding", "lot", "estate sale"
    ],
    "brand_blacklist": [
        "cartier", "tiffany", "kay", "pompeii", "van cleef", "bulgari", "david yurman",
        "rolex", "gucci", "chanel", "hermes", "pandora", "mikimoto", "graff", "harry winston", "messika"
    ],
    "allowed_brand_modifiers": [
        "inspired by", "similar to", "like", "style", "replica", "copy", "version"
    ],
    "service_keywords": [
        # Core service keywords (specific to services)
        "casting", "casting house", "service bureau", "service house", "manufacturing partner",
        "cad", "3d design", "stl", "3dm", "matrix", "matrixgold", "rhino",
        "stone setting", "prong", "pavé", "pave", "channel", "flush", "gypsy", "bezel", "micro setting",
        "engraving", "laser engraving", "hand engraving", "deep engraving",
        "enamel", "color fill", "rhodium", "plating", "vermeil",
        "laser weld", "solder", "retip", "re-tip", "repair", "ring sizing", "finish", "polish", "texture",
        "rush", "overnight", "fast turnaround", "quick turnaround", "express service",
        
        # Service request keywords
        "need help", "looking for help", "service request", "quote", "estimate",
        "wedding band", "wedding ring", "engagement ring", "anniversary ring",
        "band", "ring", "necklace", "bracelet", "earrings", "pendant",
        "gold", "silver", "platinum", "white gold", "yellow gold", "rose gold",
        "diamond", "gemstone", "stone", "precious metal", "metal", "alloy",
        
        # Stone and gemstone service keywords
        "looking for", "searching for", "need", "want", "find", "available", "in stock",
        "stone size", "stone dimensions", "stone measurements", "stone cut", "stone shape",
        "rectangular stone", "oval stone", "round stone", "square stone", "pear stone",
        "emerald cut", "princess cut", "marquise cut", "cushion cut", "radiant cut",
        "stone replacement", "stone fitting", "stone mounting", "stone setting",
        "gemstone", "sapphire", "ruby", "emerald", "diamond", "opal", "pearl", "turquoise",
        "stone sourcing", "stone supplier", "stone vendor", "stone dealer"
    ],
    "iso_keywords": [
        # Direct inquiry keywords
        "iso", "in stock", "ready to ship", "available now", "who makes this", "who manufactures this", "supplier",
        "similar to", "in the style of", "inspired by", "like this style", "similar pls",
        
        # General inquiry keywords (removed duplicates that are now in service_keywords)
        "who can", "who makes", "who manufactures", "who does", "who offers", "who has",
        "help", "need help", "looking for help", "advice", "recommendation", "suggestion",
        "make", "create", "build", "craft", "fabricate", "manufacture", "produce"
    ],
    "general_keywords": [
        # Positive sentiment keywords
        "beautiful", "gorgeous", "stunning", "amazing", "love this", "like this", "wow",
        "style", "fashion", "trend", "modern", "vintage", "classic", "unique", "elegant",
        "quality", "craftsmanship", "workmanship", "detail", "finish", "polish", "perfection",
        "stone", "gem", "diamond", "ruby", "emerald", "sapphire", "pearl", "opal",
        "metal", "titanium", "palladium", "rose gold",
        "brooch",
        "wedding", "engagement", "anniversary", "birthday", "gift", "present", "celebration"
    ],
    
    # Legacy keyword lists for backward compatibility
    "allowed_brand_modifiers": [
        "similar to", "in the style of", "inspired by", "style like", "similar pls",
        "looks like", "reminds me of", "similar design", "inspired design"
    ],
    "brand_blacklist": [
        "cartier","tiffany","kay","pompeii","van cleef","bulgari","david yurman",
        "rolex","gucci","chanel","hermes","pandora","mikimoto","graff","harry winston","messika"
    ],
    "negative_keywords": [
        "memo","consignment","for sale","wts","fs","sold","giveaway","admin",
        "rule","meme","joke","loose stone","loose stones","findings","gallery wire","strip stock",
        "equipment","tool","supplies"
    ],
    "service_keywords": [
        "casting","casting house","service bureau","service house","manufacturing partner",
        "cad","3d design","stl","3dm","matrix","matrixgold","rhino",
        "stone setting","prong","pavé","pave","channel","flush","gypsy","bezel","micro setting",
        "engraving","laser engraving","hand engraving","deep engraving",
        "enamel","color fill","rhodium","plating","vermeil",
        "laser weld","solder","retip","re-tip","repair","ring sizing","finish","polish","texture",
        "rush","overnight","fast turnaround",
        # General jewelry service keywords
        "custom","custom ring","custom jewelry","design","ring design","jewelry design",
        "help","need help","looking for","searching for","find","looking to find",
        "make","create","build","craft","fabricate","manufacture",
        "wedding band","wedding ring","engagement ring","anniversary ring",
        "band","ring","jewelry","necklace","bracelet","earrings","pendant",
        "gold","silver","platinum","white gold","yellow gold","rose gold",
        "diamond","gemstone","stone","precious metal","metal"
    ],
    
    # Enhanced comment templates with variation options
    "templates": {
        "service": [
            "Hi {{author_name}}! We're Bravo Creations — full-service B2B for jewelers: CAD, casting, stone setting, engraving, enameling, finishing. Fast turnaround, meticulous QC. (760) 431-9977 • welcome.bravocreations.com — ask for Eugene.",
            "Hi {{author_name}}! Bravo Creations service bureau — microscope-grade setting, clean castings, tight deadlines. CAD → cast → set → finish. (760) 431-9977 • welcome.bravocreations.com (ask for Eugene).",
            "Hi {{author_name}}! Need an overflow partner? We handle CAD/casting/setting/engraving with consistent QC. (760) 431-9977 • welcome.bravocreations.com — ask for Eugene.",
            "Hi {{author_name}}! Professional jewelry manufacturing partner here! We specialize in CAD, casting, stone setting, and finishing. Quality guaranteed. (760) 431-9977 • welcome.bravocreations.com — Eugene.",
            "Hi {{author_name}}! Looking for reliable jewelry manufacturing? Bravo Creations delivers: CAD design, precision casting, expert setting, perfect finish. (760) 431-9977 • welcome.bravocreations.com",
            "Hi {{author_name}}! 💎 Stone sourcing help? We work with trusted suppliers and can help find the perfect stone for your project. CAD + casting + setting + finishing. (760) 431-9977 • welcome.bravocreations.com — ask for Eugene.",
            "Hi {{author_name}}! 🔍 Need help finding a specific stone? We're Bravo Creations — full-service jewelry manufacturing with stone sourcing capabilities. (760) 431-9977 • welcome.bravocreations.com — Eugene."
        ],
        "iso": [
            "Hi {{author_name}}! ✨ Great style! We don't stock it, but this is exactly what we make daily with CAD + casting + setting. Upload jobs in minutes: welcome.bravocreations.com • (760) 431-9977 — ask for Eugene.",
            "Hi {{author_name}}! 💎 If you don't find it ready-to-ship, we can build it quickly to spec. CAD • casting • setting • finish. welcome.bravocreations.com • (760) 431-9977 (Eugene).",
            "Hi {{author_name}}! 🚀 No stock? No problem — we'll CAD + cast + set it fast, with careful QC. welcome.bravocreations.com • (760) 431-9977 — ask for Eugene.",
            "Hi {{author_name}}! 🎯 Love this design! We can recreate it with CAD + casting + setting. Fast turnaround, perfect quality. (760) 431-9977 • welcome.bravocreations.com — Eugene.",
            "Hi {{author_name}}! 💫 Beautiful piece! We can make something similar with our CAD + casting expertise. (760) 431-9977 • welcome.bravocreations.com"
        ],
        "general": [
            "Hi {{author_name}}! 💍 Beautiful piece! We're Bravo Creations — full-service B2B for jewelers. CAD, casting, stone setting, engraving, finishing. Fast turnaround, meticulous QC. (760) 431-9977 • welcome.bravocreations.com — ask for Eugene.",
            "Hi {{author_name}}! ✨ Stunning design! We handle custom jewelry from concept to completion. CAD • casting • setting • engraving • finish. (760) 431-9977 • welcome.bravocreations.com (Eugene).",
            "Hi {{author_name}}! 🌟 Love this style! We're Bravo Creations — custom jewelry manufacturing partner. From CAD to final polish, we deliver quality craftsmanship. (760) 431-9977 • welcome.bravocreations.com — ask for Eugene.",
            "Hi {{author_name}}! 💎 Gorgeous work! We're Bravo Creations — your jewelry manufacturing partner. CAD, casting, setting, finishing. Quality guaranteed. (760) 431-9977 • welcome.bravocreations.com",
            "Hi {{author_name}}! ✨ Amazing craftsmanship! We handle custom jewelry manufacturing with precision and care. (760) 431-9977 • welcome.bravocreations.com — Eugene."
        ]
    },
    
    # Comment variation settings
    "comment_variation": {
        "use_variations": True,
        "variation_chance": 0.4,  # 40% chance to use variation
        "max_variations_per_template": 3
    },
    
    # OpenAI LLM Configuration
    "openai": {
        "enabled": False,
        "model": "gpt-4o-mini",  # or "gpt-3.5-turbo" for cost savings
        "max_tokens": 150,
        "temperature": 0.7,
        "fallback_to_templates": True  # Use templates if LLM fails
    },
    
    # LLM Prompt Templates
    "llm_prompts": {
        "service": "You are Bravo Creations, a professional jewelry manufacturing company. Generate a friendly, professional comment for a Facebook post requesting jewelry services (CAD, casting, stone setting, engraving, enameling, finishing, stone sourcing, stone replacement). Start with 'Hi {{author_name}}!' to personalize it. Keep it under 150 characters. Include: (760) 431-9977 and welcome.bravocreations.com. Ask them to ask for Eugene. Be helpful but not pushy. If they're looking for a specific stone, mention your stone sourcing capabilities.",
        "iso": "You are Bravo Creations, a professional jewelry manufacturing company. Generate a friendly comment for a Facebook post where someone is looking for jewelry (ISO - in search of). Start with 'Hi {{author_name}}!' to personalize it. Mention that while you don't stock it, you can make it with CAD + casting + setting. Keep it under 150 characters. Include: (760) 431-9977 and welcome.bravocreations.com. Ask them to ask for Eugene. Be encouraging and helpful.",
        "general": "You are Bravo Creations, a professional jewelry manufacturing company. Generate a friendly, appreciative comment for a beautiful jewelry post. Start with 'Hi {{author_name}}!' to personalize it. Mention your services (CAD, casting, stone setting, engraving, finishing). Keep it under 150 characters. Include: (760) 431-9977 and welcome.bravocreations.com. Ask them to ask for Eugene. Be genuine and appreciative."
    },
    
    # Enhanced rate limiting and behavior
    "rate_limits": {
        "per_account_per_day": 8,
        "scan_refresh_minutes": 3,
        "min_delay_between_posts": 30,  # seconds
        "max_delay_between_posts": 120   # seconds
    },
    
    # Post processing settings
    "post_processing": {
        "max_scrolls_per_cycle": 5,
        "wait_between_scrolls": 2,  # seconds
        "cycle_wait_time": 15 * 60,  # 15 minutes
        "max_retries_per_post": 3
    },
    
    # Smart scanning configuration
    "smart_scanning": {
        "enabled": True,  # Set to False to revert to old continuous scanning
        "initial_scan_break_minutes": 15,  # Break after initial deep scan
        "incremental_scan_break_minutes": 15,  # Break between incremental scans
        "stop_at_processed_posts": True,  # Stop incremental scans at first processed post
        "stop_at_yesterday": True  # Stop initial scan when reaching yesterday's posts
    },
    
    "POST_URL": "https://www.facebook.com/groups/5440421919361046"
}