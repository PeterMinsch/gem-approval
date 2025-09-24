#!/usr/bin/env python3
"""
Chrome Crash Diagnostic Tool
Identifies why Chrome is crashing on server startup
"""

import subprocess
import tempfile
import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_chrome_dependencies():
    """Check if Chrome dependencies are installed"""
    logger.info("🔍 STEP 1: Checking Chrome dependencies...")

    dependencies = [
        'google-chrome-stable',
        'chromium-browser',
        'libgconf-2-4',
        'libxss1',
        'libappindicator1',
        'libindicator7',
        'fonts-liberation',
        'libasound2',
        'libgtk-3-0',
        'libxshmfence1',
        'libgbm1',
        'libnss3'
    ]

    missing_deps = []
    for dep in dependencies:
        try:
            result = subprocess.run(['dpkg', '-s', dep], capture_output=True, text=True)
            if result.returncode != 0:
                missing_deps.append(dep)
        except Exception:
            # Try with different package manager
            try:
                result = subprocess.run(['rpm', '-q', dep], capture_output=True, text=True)
                if result.returncode != 0:
                    missing_deps.append(dep)
            except Exception:
                missing_deps.append(f"{dep} (unknown)")

    if missing_deps:
        logger.error(f"❌ Missing dependencies: {missing_deps}")
        return False
    else:
        logger.info("✅ All Chrome dependencies found")
        return True

def check_system_resources():
    """Check available system resources"""
    logger.info("🔍 STEP 2: Checking system resources...")

    try:
        # Check memory
        with open('/proc/meminfo', 'r') as f:
            mem_info = f.read()
            for line in mem_info.split('\n'):
                if 'MemAvailable:' in line:
                    mem_kb = int(line.split()[1])
                    mem_mb = mem_kb // 1024
                    logger.info(f"📊 Available Memory: {mem_mb} MB")
                    if mem_mb < 512:
                        logger.warning("⚠️ Low memory - Chrome may crash")

        # Check disk space
        result = subprocess.run(['df', '-h', '/tmp'], capture_output=True, text=True)
        logger.info(f"📊 Disk space: {result.stdout.strip()}")

        # Check /dev/shm
        result = subprocess.run(['df', '-h', '/dev/shm'], capture_output=True, text=True)
        logger.info(f"📊 Shared memory: {result.stdout.strip()}")

    except Exception as e:
        logger.error(f"❌ Could not check system resources: {e}")

def test_chrome_startup_with_logs():
    """Test Chrome startup and capture detailed logs"""
    logger.info("🔍 STEP 3: Testing Chrome startup with detailed logging...")

    # Create temp directory for logs
    log_dir = tempfile.mkdtemp(prefix="chrome_crash_logs_")
    logger.info(f"📁 Chrome logs will be saved to: {log_dir}")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    # Enable extensive logging
    chrome_options.add_argument("--enable-logging")
    chrome_options.add_argument("--log-level=0")  # Most verbose
    chrome_options.add_argument(f"--log-file={log_dir}/chrome.log")
    chrome_options.add_argument("--verbose")

    # Use temp profile
    profile_dir = tempfile.mkdtemp(prefix="chrome_test_profile_")
    chrome_options.add_argument(f"--user-data-dir={profile_dir}")

    driver = None
    try:
        logger.info("🚀 Starting Chrome driver...")
        service = Service(ChromeDriverManager().install())

        start_time = time.time()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info(f"✅ Chrome started successfully in {time.time() - start_time:.2f} seconds")

        # Test basic functionality
        logger.info("🌐 Testing navigation...")
        driver.get("data:text/html,<html><body><h1>Test Page</h1></body></html>")
        logger.info("✅ Navigation successful")

        # Check if Chrome is still alive after a few seconds
        logger.info("⏱️ Waiting 10 seconds to check for crashes...")
        time.sleep(10)

        # Test if Chrome is still responsive
        current_url = driver.current_url
        logger.info(f"✅ Chrome still alive after 10 seconds, URL: {current_url}")

        return True, log_dir

    except Exception as e:
        logger.error(f"❌ Chrome crashed or failed to start: {e}")

        # Try to read Chrome logs
        try:
            chrome_log_path = os.path.join(log_dir, "chrome.log")
            if os.path.exists(chrome_log_path):
                with open(chrome_log_path, 'r') as f:
                    log_content = f.read()[-2000:]  # Last 2000 chars
                    logger.error(f"🔍 Chrome log excerpt:\n{log_content}")
        except Exception as log_error:
            logger.error(f"❌ Could not read Chrome logs: {log_error}")

        return False, log_dir

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def run_chrome_process_test():
    """Test Chrome process directly (without Selenium)"""
    logger.info("🔍 STEP 4: Testing raw Chrome process...")

    try:
        # Try to run Chrome directly
        chrome_cmd = [
            'google-chrome',
            '--headless',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--dump-dom',
            'data:text/html,<html><body><h1>Test</h1></body></html>'
        ]

        logger.info("🚀 Starting raw Chrome process...")
        result = subprocess.run(chrome_cmd, capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            logger.info("✅ Raw Chrome process completed successfully")
            return True
        else:
            logger.error(f"❌ Raw Chrome process failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("❌ Raw Chrome process timed out")
        return False
    except FileNotFoundError:
        logger.error("❌ google-chrome command not found")
        return False
    except Exception as e:
        logger.error(f"❌ Raw Chrome test failed: {e}")
        return False

def main():
    """Run full Chrome crash diagnosis"""
    logger.info("🏥 Starting Chrome Crash Diagnosis...")
    logger.info("=" * 60)

    # Step 1: Dependencies
    deps_ok = check_chrome_dependencies()

    # Step 2: Resources
    check_system_resources()

    # Step 3: Raw Chrome test
    chrome_direct_ok = run_chrome_process_test()

    # Step 4: Selenium Chrome test
    selenium_ok, log_dir = test_chrome_startup_with_logs()

    # Summary
    logger.info("=" * 60)
    logger.info("🏥 DIAGNOSIS SUMMARY:")
    logger.info(f"  Dependencies: {'✅ OK' if deps_ok else '❌ MISSING'}")
    logger.info(f"  Raw Chrome:   {'✅ OK' if chrome_direct_ok else '❌ FAILED'}")
    logger.info(f"  Selenium:     {'✅ OK' if selenium_ok else '❌ FAILED'}")
    logger.info(f"  Log Directory: {log_dir}")

    if not selenium_ok:
        logger.info("🔧 RECOMMENDATIONS:")
        if not deps_ok:
            logger.info("  1. Install missing Chrome dependencies")
        if not chrome_direct_ok:
            logger.info("  2. Chrome binary is not working - reinstall Chrome")
        logger.info("  3. Check server resource limits (memory/disk)")
        logger.info("  4. Consider using Firefox as alternative")

if __name__ == "__main__":
    main()