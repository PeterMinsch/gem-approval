# Linux Browser Path Fix Summary

## Problem
The Facebook comment bot was failing on Linux servers because the browser_manager.py files contained hardcoded Windows Chrome paths:
- `"C:\Program Files\Google\Chrome\Application\chrome.exe"`
- This caused the error: "Browser path does not exist"

## Solution
Updated both browser manager files to use cross-platform auto-detection:

### Files Modified
1. `bot/browser_manager.py`
2. `bot/modules/browser_manager.py`

### Changes Made

#### 1. Added Platform Detection
- Added `import platform` to detect the operating system
- Created `_find_chrome_binary()` method for cross-platform Chrome detection
- Created `_find_chromedriver_binary()` method for cross-platform ChromeDriver detection

#### 2. Linux Chrome Paths Added
The auto-detection now checks these Linux paths in order:
- `/usr/bin/google-chrome`
- `/usr/bin/google-chrome-stable`
- `/usr/bin/chromium`
- `/usr/bin/chromium-browser`
- `/snap/bin/chromium`
- `/opt/google/chrome/chrome`
- `/usr/local/bin/google-chrome`
- `/usr/local/bin/chromium`

#### 3. Linux ChromeDriver Paths Added
The auto-detection now checks these Linux paths:
- `/usr/bin/chromedriver` ← Based on error logs, this should work
- `/usr/local/bin/chromedriver`
- `/opt/chromedriver/chromedriver`
- `./chromedriver`

#### 4. Fallback Behavior
If no binaries are found in common locations, the code falls back to Selenium's auto-detection, which should work for most standard installations.

## Cross-Platform Compatibility
The solution maintains compatibility with:
- **Linux**: Auto-detects common Chrome/Chromium installations
- **Windows**: Still works with existing Windows installations
- **macOS**: Added support for macOS Chrome paths

## Testing
Created `test_browser_detection.py` script to verify the auto-detection functionality works correctly.

## Expected Result
The bot should now work on Linux servers with any of these Chrome installations:
- Google Chrome (installed via package manager)
- Chromium (installed via package manager)
- Snap-installed Chromium
- Manually installed Chrome

The ChromeDriver should be automatically detected at `/usr/bin/chromedriver` as mentioned in the error logs.

## Deployment Notes
- No additional configuration required
- The bot will automatically detect the appropriate browser and driver paths
- If auto-detection fails, Selenium will attempt its own auto-detection as a fallback
- Check logs for "Found Chrome binary at:" and "Found ChromeDriver at:" messages to confirm detection