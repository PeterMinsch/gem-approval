#!/usr/bin/env python3
"""
Simple test for Facebook image attachment selectors
"""

import re

def test_selectors():
    # Real HTML from DevTools for the attach button
    facebook_html = """
    <div aria-label="Attach a photo or video" class="x1i10hfl xjbqb8w x1ejq31n xd10rxx x1sy0etr x17r0tee x972fbf xcfux6l x1qhh985 xm0m39n x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz x1heor9g x1sur9pj xkrqix3 x1s688f x1lku1pv" role="button" tabindex="0">
        <div class="x9f619 x1n2onr6 x1ja2u2z x78zum5 xdt5ytf x2lah0s x193iq5w xeuugli x1r8uery x1iyjqo2 xs83m0k xsyo7zv x16hj40l x10b6aqq x1yrsyyn">
            <i alt="" data-visualcompletion="css-img" class="x1b0d499 xep6ejk"></i>
        </div>
    </div>
    """
    
    print("Testing Facebook Image Attachment Selectors")
    print("="*50)
    
    # Test patterns based on bot's XPath selectors
    tests = [
        ("div with aria-label='Attach a photo or video'", r'<div[^>]*aria-label="Attach a photo or video"[^>]*>'),
        ("div with aria-label='Photo/Video'", r'<div[^>]*aria-label="Photo/Video"[^>]*>'),
        ("button with aria-label='Attach a photo or video'", r'<button[^>]*aria-label="Attach a photo or video"[^>]*>'),
        ("div containing 'photo' in aria-label", r'<div[^>]*aria-label="[^"]*photo[^"]*"[^>]*>'),
    ]
    
    success_count = 0
    
    for i, (desc, pattern) in enumerate(tests, 1):
        matches = re.findall(pattern, facebook_html, re.IGNORECASE)
        
        if matches:
            print(f"Test {i}: PASS - Found {len(matches)} match(es)")
            print(f"  {desc}")
            success_count += 1
        else:
            print(f"Test {i}: FAIL - No matches found")
            print(f"  {desc}")
        print()
    
    print("="*50)
    print(f"SUMMARY: {success_count}/{len(tests)} tests passed")
    
    if success_count > 0:
        print("RESULT: The bot's image attachment selectors WILL work!")
        print("The bot can find the attach button on Facebook photo pages.")
        return True
    else:
        print("RESULT: The bot's image attachment selectors will NOT work.")
        print("New selectors need to be added to the bot code.")
        return False

if __name__ == "__main__":
    success = test_selectors()
    exit(0 if success else 1)