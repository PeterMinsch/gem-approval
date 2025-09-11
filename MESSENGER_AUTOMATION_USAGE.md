# Messenger Automation Usage Guide

## Quick Start

### 1. Start the API Server
```bash
cd bot
python api.py
```

### 2. Test the Implementation
```bash
python test_messenger_automation.py
```

## Integrated Smart Launcher

The Selenium automation is now **fully integrated** with your existing "Generate & Send Message" button in the CommentQueue! 

### How to Use

1. **Open your Comment Queue** in the web interface
2. **Find a comment** with a valid Facebook author profile
3. **Choose your automation method**:
   - **Toggle OFF** (Clipboard Mode): Instant copy to clipboard + opens Messenger tab
   - **Toggle ON** (Full Automation): Automatic browser paste + image upload (3-6s)
4. **Click "Generate & Send Message"**
5. **Watch the automation happen**!

### User Interface

The enhanced button now includes:
- **Method Toggle Switch**: Choose between clipboard and Selenium automation
- **Smart Status Indicators**: 
  - 🔵 Clipboard Mode (Instant)
  - 🟣 Full Automation (3-6s)
- **Real-time Progress**: Shows "Automating..." vs "Generating..."
- **Duration Display**: Shows actual completion time for Selenium method

### Backend API Usage (if needed directly)

```bash
curl -X POST http://localhost:8000/messenger/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user_123",
    "recipient": "facebook_username_or_id",
    "message": "Hello! This is an automated message.",
    "images": ["/path/to/image1.jpg", "/path/to/image2.jpg"]
  }'
```

### Check Active Sessions
```bash
curl http://localhost:8000/messenger/sessions
```

### Cleanup Session
```bash
curl -X DELETE http://localhost:8000/messenger/session/user_123
```

## Configuration

### Browser Profiles
- Profiles stored in: `./browser_profiles/messenger_{session_id}/`
- Each user session gets its own browser profile
- Profiles persist between sessions for faster startup

### Resource Limits
- Default max concurrent browsers: 3
- Can be configured in `MessengerBrowserManager(max_concurrent=5)`
- Each browser uses ~200-400MB RAM

## Troubleshooting

### Common Issues

1. **"Max concurrent browsers reached"**
   - Too many active sessions
   - Clean up unused sessions: `DELETE /messenger/session/{id}`

2. **"Browser not responding"**
   - Automatic recovery will attempt to restart browser
   - After 3 failures, session is disabled

3. **"Could not find message box"**
   - Facebook interface may have changed
   - Update selectors in `messenger_automation.py`

4. **Chrome driver issues**
   - Ensure ChromeDriver is installed and in PATH
   - Update Chrome to latest version

### Debug Mode

Set `DEBUG=1` environment variable for verbose logging:

```bash
DEBUG=1 python api.py
```

## Performance Expectations

- **Message with text only**: 2-4 seconds
- **Message with images**: 3-6 seconds  
- **Browser startup**: 3-5 seconds (first time per session)
- **Subsequent messages**: 2-3 seconds (reuses browser)

## Security Notes

- Browser profiles contain Facebook session data
- Clean up profiles regularly: `rm -rf browser_profiles/`
- Consider using headless mode in production
- Monitor for Facebook rate limiting/detection