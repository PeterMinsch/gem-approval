CONFIG = {
    "phone": "(760) 431-9977",
    "register_url": "https://welcome.bravocreations.com",
    "image_url": "https://your-cdn/bravo-comment-card.png",
    "CHROME_PROFILE": "Default",  # Or your Chrome profile name
    "COMMENT_BOX_XPATH": (
        "//div[@contenteditable='true' and @role='textbox' and ("
        "contains(@aria-placeholder, 'Write a public comment') or "
        "contains(@aria-placeholder, 'Write a public comment…') or "
        "contains(@aria-placeholder, 'Write an answer') or "
        "contains(@aria-placeholder, 'Write an answer…') or "
        "contains(@aria-placeholder, 'Write a comment') or "
        "contains(@aria-placeholder, 'Write a comment…')"
        ")]"
    ),
    "allowed_brand_modifiers": [
        "similar to", "in the style of", "inspired by", "style like", "similar pls"
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
        "rush","overnight","fast turnaround"
    ],
    "iso_keywords": [
        "iso","in stock","ready to ship","available now","who makes this","who manufactures this","supplier",
        "similar to","in the style of","inspired by","like this style","similar pls"
    ],
    "templates": {
        "service": [
            "Hi! We’re Bravo Creations — full-service B2B for jewelers: CAD, casting, stone setting, engraving, enameling, finishing. Fast turnaround, meticulous QC. (760) 431-9977 • welcome.bravocreations.com — ask for Eugene.",
            "Bravo Creations service bureau — microscope-grade setting, clean castings, tight deadlines. CAD → cast → set → finish. (760) 431-9977 • welcome.bravocreations.com (ask for Eugene).",
            "Need an overflow partner? We handle CAD/casting/setting/engraving with consistent QC. (760) 431-9977 • welcome.bravocreations.com — ask for Eugene."
        ],
        "iso": [
            "✨ Great style! We don’t stock it, but this is exactly what we make daily with CAD + casting + setting. Upload jobs in minutes: welcome.bravocreations.com • (760) 431-9977 — ask for Eugene.",
            "💎 If you don’t find it ready-to-ship, we can build it quickly to spec. CAD • casting • setting • finish. welcome.bravocreations.com • (760) 431-9977 (Eugene).",
            "🚀 No stock? No problem — we’ll CAD + cast + set it fast, with careful QC. welcome.bravocreations.com • (760) 431-9977 — ask for Eugene."
        ]
    },
    "rate_limits": {
        "per_account_per_day": 8,
        "scan_refresh_minutes": 3
    },
    "POST_URL": "https://www.facebook.com/groups/5440421919361046"
}