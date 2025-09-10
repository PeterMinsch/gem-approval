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

## Smart Launcher Components (from SMART_LAUNCHER_PRD.md)

The implementation should also include these Smart Launcher features for enhanced functionality:

### User Profile ID Extraction
Extract Facebook user IDs from various profile URL formats to create proper Messenger links.

### AI-Powered Message Generation  
Generate personalized DM messages using OpenAI API with template fallbacks.

### Smart Launcher Button
Replace generic buttons with intelligent message generation system.

## Implementation Phases

### Phase 0: Smart Launcher Foundation (1-2 days)
*Implement these components first as they're required for full functionality*

#### 0.1 User Profile ID Extraction Utility
**File**: `src/utils/messageUtils.ts` (create if doesn't exist)

```typescript
/**
 * Extract Facebook ID from various profile URL formats
 * Supports: profile.php?id=123, /username, /groups/.../user/123/
 */
export const extractFacebookIdFromProfileUrl = (profileUrl: string): string | null => {
  if (profileUrl.includes('profile.php?id=')) {
    // Extract numeric ID: facebook.com/profile.php?id=123456789
    const match = profileUrl.match(/id=([^&]+)/);
    return match ? match[1] : null;
  } else if (profileUrl.includes('/groups/') && profileUrl.includes('/user/')) {
    // Handle group-based profile URLs: /groups/[groupid]/user/[userid]/
    const userMatch = profileUrl.match(/\/user\/([^/?]+)/);
    return userMatch ? userMatch[1] : null;
  } else {
    // Extract username: facebook.com/john.smith
    const pathMatch = profileUrl.match(/facebook\.com\/([^/?]+)/);
    const path = pathMatch ? pathMatch[1] : null;
    
    // Filter out non-profile paths
    if (path && !['profile.php', 'photo', 'events', 'pages'].includes(path)) {
      return path;
    }
  }
  return null;
};

/**
 * Create Messenger URL from Facebook profile URL
 */
export const createMessengerLink = (profileUrl: string): string | null => {
  const facebookId = extractFacebookIdFromProfileUrl(profileUrl);
  if (facebookId) {
    return `https://www.facebook.com/messages/t/${facebookId}`;
  }
  return null;
};

/**
 * Copy text to clipboard with fallback support
 */
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    // Modern Clipboard API (preferred)
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      console.log('✅ Message copied to clipboard via Clipboard API');
      return true;
    }
    
    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    const successful = document.execCommand('copy');
    document.body.removeChild(textArea);
    
    if (successful) {
      console.log('✅ Message copied to clipboard via fallback method');
      return true;
    }
  } catch (error) {
    console.error('❌ Failed to copy to clipboard:', error);
    return false;
  }
  return false;
};

/**
 * Open Messenger conversation in new tab
 */
export const openMessengerConversation = (messengerUrl: string): boolean => {
  try {
    if (!messengerUrl) {
      console.error('❌ No Messenger URL provided');
      return false;
    }
    
    // Open Messenger in new tab
    const newWindow = window.open(messengerUrl, '_blank', 'noopener,noreferrer');
    
    if (newWindow) {
      console.log(`✅ Opened Messenger conversation: ${messengerUrl}`);
      newWindow.focus();
      return true;
    } else {
      // Fallback if popup is blocked
      console.warn('⚠️ Popup blocked, trying fallback navigation');
      window.location.href = messengerUrl;
      return true;
    }
  } catch (error) {
    console.error('❌ Failed to open Messenger conversation:', error);
    return false;
  }
};

/**
 * Execute Smart Launcher: copy message and open Messenger
 */
export const executeSmartLauncher = async (
  message: string,
  messengerUrl: string,
  images: string[] = [],
  debugMode: boolean = false
): Promise<{
  success: boolean;
  message: string;
  clipboardSuccess: boolean;
  messengerSuccess: boolean;
  hasImage: boolean;
}> => {
  console.log('🚀 Executing Smart Launcher...');
  
  // Step 1: Copy message to clipboard
  const clipboardSuccess = await copyToClipboard(message);
  
  // Step 2: Open Messenger conversation (unless in debug mode)
  let messengerSuccess = true;
  if (!debugMode) {
    messengerSuccess = openMessengerConversation(messengerUrl);
  } else {
    console.log('🐛 Debug mode: Messenger not opened');
  }
  
  const result = {
    success: clipboardSuccess && messengerSuccess,
    message: message,
    clipboardSuccess,
    messengerSuccess,
    hasImage: images.length > 0
  };
  
  return result;
};
```

#### 0.2 AI Message Generator Backend
**File**: `bot/modules/message_generator.py` (create new file)

```python
import random
import logging
import openai
from typing import Dict, Any, Optional
import asyncio

logger = logging.getLogger(__name__)

# Message Templates by Post Type
DM_TEMPLATES = {
    'DM_SERVICE': [
        "Hi {author_name}! 💫 Beautiful work! We're Bravo Creations, full-service B2B jewelry manufacturer specializing in CAD design, casting, and finishing. We'd love to help bring your custom pieces to life. Check us out: {register_url} - Call us: {phone}",
        "Hi {author_name}! ✨ Stunning piece! As a B2B jewelry manufacturer, we specialize in turning concepts into reality through CAD design and precision casting. Would love to collaborate! {register_url} - {phone}",
        "Hello {author_name}! 💎 Amazing craftsmanship! Bravo Creations offers complete B2B manufacturing - from CAD to finished pieces. Let's discuss your custom projects! {register_url} - {phone}"
    ],
    'DM_ISO': [
        "Hi {author_name}! 💫 Beautiful piece! We can make something similar with our CAD + casting expertise. Full-service B2B manufacturer ready to help. {register_url} - {phone}",
        "Hello {author_name}! ✨ Love this design! As a B2B manufacturer, we can create similar pieces with precision CAD work and quality casting. {register_url} - {phone}",
        "Hi {author_name}! 💎 Gorgeous work! We specialize in bringing designs like this to life through our complete manufacturing process. {register_url} - {phone}"
    ],
    'DM_GENERAL': [
        "Hi {author_name}! 👋 Saw your jewelry post - beautiful work! We're Bravo Creations, B2B manufacturer specializing in custom pieces. Would love to connect! {register_url} - {phone}",
        "Hello {author_name}! ✨ Beautiful jewelry! We're a B2B manufacturer focused on custom design and production. Let's explore how we can help! {register_url} - {phone}",
        "Hi {author_name}! 💫 Impressive work! Bravo Creations offers comprehensive B2B jewelry manufacturing services. Would love to discuss opportunities! {register_url} - {phone}"
    ]
}

class MessageGenerator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
        self.setup_openai()
        
        # AI Prompts
        self.dm_system_prompt = """
You are a professional B2B jewelry manufacturer representative. Generate personalized, friendly DM messages for Facebook outreach.

Guidelines:
- Keep it under 200 characters
- Be warm but professional
- Mention Bravo Creations as a B2B manufacturer
- Include phone number and registration URL
- Use appropriate emojis (1-2 max)
- Personalize based on their post content
- Focus on collaboration and custom manufacturing
"""

    def setup_openai(self):
        """Initialize OpenAI client if API key is available"""
        api_key = self.config.get('openai_api_key')
        if api_key:
            try:
                self.client = openai.AsyncOpenAI(api_key=api_key)
                logger.info("✅ OpenAI client initialized")
            except Exception as e:
                logger.warning(f"⚠️ OpenAI setup failed: {e}")
                self.client = None
        else:
            logger.info("🔧 No OpenAI API key - using templates only")

    def prepare_message_context(self, comment_data: dict) -> dict:
        """Prepare context for message generation"""
        return {
            'author_name': comment_data.get('post_author', 'there'),
            'post_text': comment_data.get('post_text', ''),
            'post_type': comment_data.get('post_type', 'general'),
            'phone': self.config.get('phone', ''),
            'register_url': self.config.get('register_url', ''),
            'image_url': self.config.get('image_url', '')
        }

    def determine_message_type(self, post_text: str) -> str:
        """Determine message type based on post content"""
        post_lower = post_text.lower()
        
        # Check for service-related keywords
        service_keywords = ['custom', 'commission', 'design', 'make', 'create', 'craft']
        if any(keyword in post_lower for keyword in service_keywords):
            return 'DM_SERVICE'
        
        # Check for ISO (In Search Of) keywords  
        iso_keywords = ['iso', 'looking for', 'need', 'want', 'search', 'find']
        if any(keyword in post_lower for keyword in iso_keywords):
            return 'DM_ISO'
        
        return 'DM_GENERAL'

    def generate_template_message(self, context: dict) -> dict:
        """Generate message using templates"""
        message_type = self.determine_message_type(context['post_text'])
        templates = DM_TEMPLATES.get(message_type, DM_TEMPLATES['DM_GENERAL'])
        
        # Select random template
        template = random.choice(templates)
        
        # Format with context
        message = template.format(**context)
        
        return {
            'message': message,
            'generation_method': 'template',
            'template_type': message_type,
            'character_count': len(message)
        }

    async def generate_ai_message(self, context: dict) -> str:
        """Generate AI message with fallback to templates"""
        try:
            if not self.client:
                raise Exception("OpenAI client not available")
                
            user_prompt = self.format_user_prompt(context)
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.dm_system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=200,
                temperature=0.7,
                timeout=30.0
            )
            
            ai_message = response.choices[0].message.content.strip()
            
            return {
                'message': ai_message,
                'generation_method': 'ai',
                'character_count': len(ai_message)
            }
            
        except Exception as e:
            logger.warning(f"⚠️ AI generation failed, using template fallback: {e}")
            return self.generate_template_message(context)

    def format_user_prompt(self, context: dict) -> str:
        """Format user prompt for AI generation"""
        return f"""
Generate a personalized DM message for this jewelry post:

Author: {context['author_name']}
Post Content: {context['post_text'][:300]}...
Post Type: {context['post_type']}

Include:
- Phone: {context['phone']}
- URL: {context['register_url']}

Make it personal, professional, and under 200 characters.
"""

    async def generate_dm_message(self, comment_data: dict) -> dict:
        """Main method to generate DM message"""
        context = self.prepare_message_context(comment_data)
        
        # Try AI first, fallback to template
        if self.client:
            result = await self.generate_ai_message(context)
        else:
            result = self.generate_template_message(context)
        
        # Add common fields
        result.update({
            'author_name': context['author_name'],
            'post_type': self.determine_message_type(context['post_text'])
        })
        
        return result
```

#### 0.3 Message Generation API Endpoint
**File**: Add to `bot/api.py`

```python
from bot.modules.message_generator import MessageGenerator

# Initialize message generator (add near other global variables)
message_generator = MessageGenerator(CONFIG)

@app.post("/generate-message/{comment_id}")
async def generate_dm_message(comment_id: str):
    """Generate personalized DM message for a specific comment"""
    import time
    start_time = time.time()
    
    try:
        # Get comment data from database
        comment_id_int = int(comment_id)
        db_comment = db.get_comment_by_id(comment_id_int)
        
        if not db_comment:
            raise HTTPException(status_code=404, detail=f"Comment {comment_id} not found")
        
        # Generate the message
        result = await message_generator.generate_dm_message(db_comment)
        
        # Create Messenger URL from author profile URL
        messenger_url = None
        if db_comment.get('post_author_url'):
            # Extract Facebook ID from profile URL
            facebook_id = extract_facebook_id_from_profile_url(db_comment['post_author_url'])
            if facebook_id:
                messenger_url = f"https://www.facebook.com/messages/t/{facebook_id}"
        
        generation_time = time.time() - start_time
        
        return {
            'success': True,
            'message': result['message'],
            'author_name': result['author_name'],
            'generation_method': result['generation_method'],
            'character_count': result['character_count'],
            'generation_time_seconds': round(generation_time, 2),
            'post_type': result['post_type'],
            'messenger_url': messenger_url,
            'has_images': False,  # Text-only for reliable Messenger compatibility
            'post_images': []  # Empty for now, can be populated later
        }
    except Exception as e:
        logger.error(f"❌ Failed to generate message: {e}")
        raise HTTPException(status_code=500, detail=f"Message generation failed: {str(e)}")

def extract_facebook_id_from_profile_url(profile_url: str) -> str:
    """Extract Facebook ID from profile URL (Python version)"""
    import re
    
    if 'profile.php?id=' in profile_url:
        match = re.search(r'id=([^&]+)', profile_url)
        return match.group(1) if match else None
    elif '/groups/' in profile_url and '/user/' in profile_url:
        match = re.search(r'/user/([^/?]+)', profile_url)
        return match.group(1) if match else None
    else:
        match = re.search(r'facebook\.com/([^/?]+)', profile_url)
        path = match.group(1) if match else None
        
        if path and path not in ['profile.php', 'photo', 'events', 'pages']:
            return path
    
    return None
```

#### 0.4 Frontend Message Generation Hook
**File**: `src/hooks/useMessageGeneration.ts` (create new file)

```typescript
import { useState, useCallback } from 'react';

export interface MessageGenerationResult {
  success: boolean;
  message: string;
  author_name: string;
  generation_method: string;
  character_count: number;
  generation_time_seconds: number;
  post_type: string;
  messenger_url?: string;
  has_images: boolean;
  post_images: string[];
}

export interface MessageGenerationError {
  message: string;
  details: string;
}

export interface UseMessageGenerationReturn {
  generateMessage: (commentId: string) => Promise<MessageGenerationResult | null>;
  isGenerating: boolean;
  error: MessageGenerationError | null;
  clearError: () => void;
}

export const useMessageGeneration = (): UseMessageGenerationReturn => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<MessageGenerationError | null>(null);

  const generateMessage = useCallback(async (commentId: string) => {
    setIsGenerating(true);
    setError(null);

    try {
      const response = await fetch(`http://localhost:8000/generate-message/${commentId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        mode: 'cors',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result: MessageGenerationResult = await response.json();
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError({
        message: 'Failed to generate message',
        details: errorMessage
      });
      return null;
    } finally {
      setIsGenerating(false);
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return { generateMessage, isGenerating, error, clearError };
};
```

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

#### 2.1 Smart Launcher Button Integration
**File**: Update existing `src/components/CommentQueue.tsx`

Add Smart Launcher button to replace or supplement existing PM buttons:

```typescript
import { useMessageGeneration } from '../hooks/useMessageGeneration';
import { executeSmartLauncher } from '../utils/messageUtils';
import { MessageSquare, Loader2 } from 'lucide-react'; // Or your icon library

// Add to component
const { generateMessage, isGenerating, error } = useMessageGeneration();
const [statusMessage, setStatusMessage] = useState<string>('');
const debugMode = false; // Set to true for development

const handleSmartLauncher = async (comment: QueuedComment) => {
  console.log(`🚀 Smart Launcher initiated for comment: ${comment.id}`);
  setStatusMessage('Generating personalized message...');
  
  try {
    // Generate personalized message
    const result = await generateMessage(comment.id.toString());
    
    if (result?.success) {
      setStatusMessage('Message generated! Opening Messenger...');
      
      // Execute Smart Launcher (copy + open Messenger)
      const launcherResult = await executeSmartLauncher(
        result.message,
        result.messenger_url || '',
        result.post_images || [],
        debugMode
      );
      
      if (launcherResult.success) {
        console.log('✅ Smart Launcher executed successfully');
        setStatusMessage(
          `✅ Message copied to clipboard! ${debugMode ? '(Debug: Messenger not opened)' : 'Messenger opened - paste with Ctrl+V'}`
        );
      } else {
        setStatusMessage('❌ Failed to copy message or open Messenger');
      }
    } else {
      setStatusMessage('❌ Failed to generate message');
    }
  } catch (error) {
    console.error('❌ Smart Launcher failed:', error);
    setStatusMessage('❌ Smart Launcher failed. Please try again.');
  }
};

// In your JSX, add the Smart Launcher button for each comment:
<button
  onClick={() => handleSmartLauncher(comment)}
  disabled={isGenerating}
  className="smart-launcher-btn bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded flex items-center gap-2"
  title="Generate personalized message and open Messenger"
>
  {isGenerating ? (
    <>
      <Loader2 className="w-4 h-4 animate-spin" />
      Generating...
    </>
  ) : (
    <>
      <MessageSquare className="w-4 h-4" />
      Smart Launcher
    </>
  )}
</button>

{/* Status message display */}
{statusMessage && (
  <div className="mt-2 p-2 bg-gray-100 rounded text-sm">
    {statusMessage}
  </div>
)}
```

#### 2.2 Alternative MessengerSender Component
**File**: `src/components/MessengerSender.tsx` (new component for manual use)

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

## Configuration Requirements

### Environment Variables
Add to your environment or `.env` file:

```bash
# Optional - for AI message generation
OPENAI_API_KEY=your_openai_key_here

# Required - for message templates
BRAVO_PHONE="(760) 431-9977"
BRAVO_REGISTER_URL="https://welcome.bravocreations.com"
BRAVO_IMAGE_URL="https://your-cdn/bravo-comment-card.png"
```

### Update Bot Configuration
**File**: `bot/bravo_config.py`

Add Smart Launcher config:
```python
CONFIG = {
    # Existing config...
    
    # Smart Launcher settings
    "phone": "(760) 431-9977",
    "register_url": "https://welcome.bravocreations.com", 
    "image_url": "https://your-cdn/bravo-comment-card.png",
    "openai_api_key": os.getenv("OPENAI_API_KEY"),  # Optional
}
```

## Deployment Notes

### Dependencies
Add to `requirements.txt`:
```
selenium>=4.0.0
webdriver-manager>=3.8.0
openai>=1.0.0
```

Add to `package.json` (if not already present):
```json
{
  "dependencies": {
    "lucide-react": "^0.294.0"
  }
}
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

## Complete User Flow

### Option 1: Smart Launcher (Recommended)
1. **User clicks "Smart Launcher"** on any comment in the queue
2. **System generates personalized message** using AI or templates
3. **Message copied to clipboard** automatically  
4. **Messenger opens** to the correct conversation
5. **User pastes message** with Ctrl+V and sends

### Option 2: Full Automation 
1. **User clicks "Generate and Send Message"** 
2. **System generates message** and extracts recipient ID
3. **Browser automation** pastes message and uploads images
4. **Message sent** automatically via Selenium

---

**Implementation Timeline: 6-8 days total**
- **Phase 0 (Smart Launcher)**: 1-2 days
- **Phase 1 (Browser Automation)**: 2-3 days  
- **Phase 2 (Frontend Integration)**: 1-2 days
- **Phase 3 (Error Handling)**: 1 day

**Expected Performance:**
- **Smart Launcher**: Instant clipboard + Messenger tab opening
- **Full Automation**: 3-6 seconds per message with images
- **Resource Usage**: ~1GB RAM for full concurrent operation
- **Detection Risk**: Very Low (mimics natural user behavior)

**Recommended Approach**: Start with Smart Launcher (Phase 0), then add full automation (Phases 1-3) based on user feedback.