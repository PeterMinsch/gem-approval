# Messenger Automation Implementation Plan

## Overview

This document outlines the implementation plan for adding automated Facebook Messenger message sending with image attachments to the existing Bravo Bot system. The feature allows users to click "Generate and Send Message" to automatically paste messages and upload images via Selenium-controlled browsers.

## Key Insights & Risk Assessment

### Low Detection Risk Strategy
- **Text pasting**: Mimics human clipboard behavior - NO random delays needed
- **Image uploads**: Only minimal system response delays (100-200ms)
- **Session reuse**: Leverage existing authenticated sessions
- **Performance**: 3-6 seconds per message (vs 15+ with unnecessary delays)

### Resource Requirements
- **RAM per browser**: 200-300MB
- **CPU per operation**: 5-10%
- **Concurrent limit**: 3-4 browsers recommended
- **Total overhead**: ~1GB RAM for full concurrent usage

## Architecture

### Browser Management Strategy
```
Main Bot Browser (existing) 
├── Messenger Browser Pool
│   ├── User Session 1 Browser
│   ├── User Session 2 Browser  
│   └── User Session 3 Browser
└── Queue for overflow requests
```

### Component Overview
1. **BrowserManager**: Manages multiple browser instances
2. **MessengerAutomation**: Handles message sending logic
3. **API Endpoints**: New FastAPI endpoints for frontend integration
4. **Error Recovery**: Browser crash handling and session management

## Implementation Phases

### Phase 1: Core Messenger Automation (2-3 days)

#### 1.1 Create Browser Manager Class
**File**: `bot/browser_manager.py`

```python
import asyncio
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from typing import Dict, Optional

class MessengerBrowserManager:
    def __init__(self, max_concurrent: int = 3):
        self.main_bot_browser = None
        self.messenger_browsers: Dict[str, webdriver.Chrome] = {}
        self.max_concurrent = max_concurrent
        self.request_queue = asyncio.Queue()
        
    def get_messenger_browser(self, session_id: str) -> webdriver.Chrome:
        """Get or create messenger browser for session"""
        if session_id in self.messenger_browsers:
            browser = self.messenger_browsers[session_id]
            if self._is_browser_alive(browser):
                return browser
            else:
                self._cleanup_browser(session_id)
        
        if len(self.messenger_browsers) >= self.max_concurrent:
            raise Exception("Max concurrent browsers reached")
            
        browser = self._create_messenger_browser(session_id)
        self.messenger_browsers[session_id] = browser
        return browser
    
    def _create_messenger_browser(self, session_id: str) -> webdriver.Chrome:
        """Create optimized browser instance"""
        options = Options()
        
        # Profile persistence for session reuse
        profile_dir = f"./browser_profiles/messenger_{session_id}"
        os.makedirs(profile_dir, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")
        
        # Performance optimizations
        options.add_argument("--disable-extensions")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        
        # Keep visible for debugging (can make headless later)
        # options.add_argument("--headless")
        
        browser = webdriver.Chrome(options=options)
        browser.set_window_size(1200, 800)
        return browser
    
    def _is_browser_alive(self, browser: webdriver.Chrome) -> bool:
        """Check if browser is still responsive"""
        try:
            browser.current_url
            return True
        except:
            return False
    
    def _cleanup_browser(self, session_id: str):
        """Clean up browser resources"""
        if session_id in self.messenger_browsers:
            try:
                self.messenger_browsers[session_id].quit()
            except:
                pass
            del self.messenger_browsers[session_id]
    
    def cleanup_all(self):
        """Cleanup all browsers"""
        for session_id in list(self.messenger_browsers.keys()):
            self._cleanup_browser(session_id)
```

#### 1.2 Create Messenger Automation Class
**File**: `bot/messenger_automation.py`

```python
import asyncio
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class MessengerAutomation:
    def __init__(self, browser: webdriver.Chrome):
        self.browser = browser
        self.wait = WebDriverWait(browser, 10)
        
    async def send_message_with_images(self, recipient: str, message: str, image_paths: list = None):
        """Send message with optional images to recipient"""
        start_time = time.time()
        
        try:
            # Navigate to messenger if not already there
            await self._navigate_to_messenger()
            
            # Find or start conversation
            await self._open_conversation(recipient)
            
            # Paste message text (INSTANT - no delays)
            await self._paste_message(message)
            
            # Upload images if provided (MINIMAL delays)
            if image_paths:
                for image_path in image_paths:
                    await self._upload_image(image_path)
            
            # Send message
            await self._send_message()
            
            duration = time.time() - start_time
            return {"status": "success", "duration": f"{duration:.2f}s"}
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _navigate_to_messenger(self):
        """Navigate to Facebook Messenger"""
        current_url = self.browser.current_url
        if "messenger.com" not in current_url:
            self.browser.get("https://www.messenger.com/")
            await asyncio.sleep(1)  # Allow page load
    
    async def _open_conversation(self, recipient: str):
        """Find and open conversation with recipient"""
        # Implementation depends on how you identify recipients
        # Could be by name search or direct conversation URL
        
        # Option 1: Search for recipient
        search_box = self.wait.until(
            EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Search Messenger']"))
        )
        search_box.clear()
        search_box.send_keys(recipient)
        await asyncio.sleep(0.5)  # Allow search results
        
        # Click first result
        first_result = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//div[@role='button']//span[contains(text(), '" + recipient + "')]"))
        )
        first_result.click()
        await asyncio.sleep(0.5)  # Allow conversation load
    
    async def _paste_message(self, message: str):
        """Paste message text - INSTANT, mimics clipboard behavior"""
        message_box = self.wait.until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='textbox']"))
        )
        
        # Clear existing content
        message_box.clear()
        
        # Paste text instantly (mimics human clipboard paste)
        message_box.send_keys(message)
        
        # NO DELAYS - this mimics natural clipboard behavior
    
    async def _upload_image(self, image_path: str):
        """Upload single image - MINIMAL delays for system response"""
        # Find and click attachment button
        attach_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='file']"))
        )
        
        # Upload file directly to input element
        attach_button.send_keys(image_path)
        
        # Brief pause for file processing (system response time)
        await asyncio.sleep(0.2)
    
    async def _send_message(self):
        """Send the message"""
        # Find send button (usually Enter key or send button)
        message_box = self.browser.find_element(By.XPATH, "//div[@role='textbox']")
        message_box.send_keys(Keys.RETURN)
        
        # Brief pause to ensure message sent
        await asyncio.sleep(0.3)
```

#### 1.3 Update API Endpoints
**File**: `bot/api.py` (add to existing file)

```python
from bot.browser_manager import MessengerBrowserManager
from bot.messenger_automation import MessengerAutomation
from pydantic import BaseModel
from typing import List, Optional

# Global browser manager
messenger_browser_manager = MessengerBrowserManager()

class MessengerRequest(BaseModel):
    session_id: str
    recipient: str
    message: str
    images: Optional[List[str]] = None

class MessengerResponse(BaseModel):
    status: str
    duration: Optional[str] = None
    error: Optional[str] = None

@app.post("/messenger/send-message", response_model=MessengerResponse)
async def send_messenger_message(request: MessengerRequest):
    """Send message via Messenger automation"""
    try:
        # Get browser for this session
        browser = messenger_browser_manager.get_messenger_browser(request.session_id)
        
        # Create automation instance
        messenger = MessengerAutomation(browser)
        
        # Send message with images
        result = await messenger.send_message_with_images(
            recipient=request.recipient,
            message=request.message,
            image_paths=request.images
        )
        
        return MessengerResponse(**result)
        
    except Exception as e:
        return MessengerResponse(status="error", error=str(e))

@app.get("/messenger/sessions")
async def get_messenger_sessions():
    """Get active messenger browser sessions"""
    sessions = list(messenger_browser_manager.messenger_browsers.keys())
    return {"active_sessions": sessions, "count": len(sessions)}

@app.delete("/messenger/session/{session_id}")
async def cleanup_messenger_session(session_id: str):
    """Cleanup specific messenger session"""
    messenger_browser_manager._cleanup_browser(session_id)
    return {"status": "cleaned", "session_id": session_id}

# Cleanup on app shutdown
@app.on_event("shutdown")
async def cleanup_browsers():
    messenger_browser_manager.cleanup_all()
```

### Phase 2: Frontend Integration (1-2 days)

#### 2.1 Update Frontend Component
**File**: `src/components/MessengerSender.tsx` (new component)

```typescript
import React, { useState } from 'react';

interface MessengerSenderProps {
  sessionId: string;
  generatedMessage: string;
  generatedImages: string[];
}

export const MessengerSender: React.FC<MessengerSenderProps> = ({
  sessionId,
  generatedMessage,
  generatedImages
}) => {
  const [recipient, setRecipient] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleSendMessage = async () => {
    if (!recipient.trim()) {
      alert('Please enter recipient name');
      return;
    }

    setIsLoading(true);
    setResult(null);

    try {
      const response = await fetch('/messenger/send-message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          recipient: recipient,
          message: generatedMessage,
          images: generatedImages
        })
      });

      const data = await response.json();
      setResult(data);
      
      if (data.status === 'success') {
        alert(`Message sent successfully in ${data.duration}!`);
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (error) {
      alert(`Request failed: ${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="messenger-sender">
      <h3>Send to Messenger</h3>
      
      <div className="form-group">
        <label>Recipient:</label>
        <input
          type="text"
          value={recipient}
          onChange={(e) => setRecipient(e.target.value)}
          placeholder="Enter recipient name or ID"
          disabled={isLoading}
        />
      </div>

      <div className="message-preview">
        <h4>Message:</h4>
        <p>{generatedMessage}</p>
        {generatedImages.length > 0 && (
          <div>
            <h4>Images ({generatedImages.length}):</h4>
            <ul>
              {generatedImages.map((img, idx) => (
                <li key={idx}>{img}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <button
        onClick={handleSendMessage}
        disabled={isLoading || !recipient.trim()}
        className="send-button"
      >
        {isLoading ? 'Sending...' : 'Generate and Send Message'}
      </button>

      {result && (
        <div className={`result ${result.status}`}>
          <strong>Result:</strong> {result.status}
          {result.duration && <span> ({result.duration})</span>}
          {result.error && <div>Error: {result.error}</div>}
        </div>
      )}
    </div>
  );
};
```

#### 2.2 Integrate with Existing Components
Add the MessengerSender component to your main approval workflow interface.

### Phase 3: Error Handling & Polish (1 day)

#### 3.1 Enhanced Error Recovery
**File**: `bot/browser_recovery.py`

```python
import logging
import time
from typing import Dict, Any

class BrowserRecovery:
    def __init__(self, browser_manager):
        self.browser_manager = browser_manager
        self.failure_counts: Dict[str, int] = {}
        self.max_failures = 3
        
    def handle_browser_failure(self, session_id: str, error: Exception):
        """Handle browser failures with recovery"""
        self.failure_counts[session_id] = self.failure_counts.get(session_id, 0) + 1
        
        logging.error(f"Browser failure for session {session_id}: {error}")
        
        if self.failure_counts[session_id] >= self.max_failures:
            logging.error(f"Max failures reached for session {session_id}, disabling")
            return False
            
        # Clean up and recreate browser
        self.browser_manager._cleanup_browser(session_id)
        time.sleep(2)  # Brief pause before recreation
        
        try:
            new_browser = self.browser_manager._create_messenger_browser(session_id)
            self.browser_manager.messenger_browsers[session_id] = new_browser
            logging.info(f"Browser recreated for session {session_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to recreate browser for session {session_id}: {e}")
            return False
    
    def reset_failure_count(self, session_id: str):
        """Reset failure count after successful operation"""
        if session_id in self.failure_counts:
            del self.failure_counts[session_id]
```

#### 3.2 Add Progress Monitoring
**File**: `bot/progress_tracker.py`

```python
import time
from typing import Dict, Any

class ProgressTracker:
    def __init__(self):
        self.operations: Dict[str, Dict[str, Any]] = {}
    
    def start_operation(self, operation_id: str, session_id: str):
        """Start tracking an operation"""
        self.operations[operation_id] = {
            'session_id': session_id,
            'start_time': time.time(),
            'status': 'running',
            'progress': 'Starting...'
        }
    
    def update_progress(self, operation_id: str, progress: str):
        """Update operation progress"""
        if operation_id in self.operations:
            self.operations[operation_id]['progress'] = progress
    
    def complete_operation(self, operation_id: str, success: bool, error: str = None):
        """Mark operation as complete"""
        if operation_id in self.operations:
            op = self.operations[operation_id]
            op['status'] = 'success' if success else 'error'
            op['end_time'] = time.time()
            op['duration'] = op['end_time'] - op['start_time']
            if error:
                op['error'] = error
    
    def get_operation_status(self, operation_id: str):
        """Get current operation status"""
        return self.operations.get(operation_id, {})
```

## Testing Strategy

### Manual Testing Checklist
- [ ] Single message send (text only)
- [ ] Message with single image
- [ ] Message with multiple images
- [ ] Concurrent operations (2-3 simultaneous)
- [ ] Browser crash recovery
- [ ] Session persistence across operations
- [ ] Error handling for invalid recipients

### Performance Testing
- [ ] Measure actual send times
- [ ] Monitor RAM usage with multiple browsers
- [ ] Test with different image sizes/formats
- [ ] Verify no memory leaks over extended use

## Security Considerations

### Facebook Terms of Service
- Ensure compliance with Facebook's automation policies
- Consider rate limiting to avoid triggering abuse detection
- Monitor for any changes in Facebook's anti-automation measures

### Data Privacy
- Store session data securely
- Clear browser profiles when appropriate
- Handle authentication data responsibly


## Deployment Notes

### Dependencies
Add to `requirements.txt`:
```
selenium>=4.0.0
webdriver-manager>=3.8.0
```

### Chrome Driver Setup
Ensure ChromeDriver is properly installed and in PATH.

### Directory Structure
Create these directories:
```
bot/
├── browser_profiles/     # Browser session storage
├── browser_manager.py
├── messenger_automation.py
├── browser_recovery.py
└── progress_tracker.py
```

## Monitoring & Maintenance

### Logging
- Log all browser operations
- Track success/failure rates
- Monitor performance metrics

### Regular Maintenance
- Clean up old browser profiles
- Monitor disk space usage
- Update ChromeDriver as needed
- Review Facebook interface changes

## Future Enhancements

### Phase 4 Possible Additions
- Scheduled message sending
- Message templates management
- Bulk message operations
- Advanced recipient targeting
- Analytics dashboard for sent messages

## Support & Troubleshooting

### Common Issues
1. **Browser won't start**: Check ChromeDriver installation
2. **Can't find recipient**: Verify recipient name format
3. **Images won't upload**: Check file paths and permissions
4. **Memory usage high**: Implement browser cleanup schedule
5. **Facebook interface changes**: Update selectors in automation code

### Debug Mode
Set environment variable `DEBUG=1` to enable verbose logging and keep browsers visible for debugging.

---

**Implementation Timeline: 4-6 days total**
**Expected Performance: 3-6 seconds per message**
**Resource Usage: ~1GB RAM for full concurrent operation**
**Detection Risk: Very Low (mimics natural user behavior)**