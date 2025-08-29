# Bravo CRM System

A comprehensive Customer Relationship Management system for managing Facebook bot interactions, built on top of your existing Bravo bot infrastructure.

## 🚀 Features

### Core CRM Capabilities
- **Smart Post Triage**: AI-powered intent detection (Service, ISO/Buy, Ignore)
- **Template Management**: Specialized comment templates with variable substitution
- **Workflow Management**: Status tracking from Pending → Approved → Posted
- **Facebook Account Rotation**: Automatic account selection with daily quotas
- **Activity Logging**: Complete audit trail of all actions
- **Search & Filtering**: Advanced post search with multiple criteria

### Post Management
- **Ingestion**: Bot automatically ingests posts with AI-drafted comments
- **Review Queue**: Human-in-the-loop approval process
- **One-click Actions**: Approve, Submit, Skip, or PM authors
- **Template Swapping**: Quick template changes for different post types
- **Image Attachments**: Support for image packs with templates

### Settings & Configuration
- **Keyword Management**: Configurable negative, service, and ISO keywords
- **Brand Rules**: Blacklist and allowed modifier phrases
- **Template Editor**: Create and manage comment templates
- **Account Management**: Facebook account configuration and quotas
- **API Configuration**: OpenAI keys and system settings

## 🏗️ Architecture

### Database Schema
The system uses an enhanced SQLite database with the following new tables:

- **posts**: Facebook posts with metadata and status
- **comments**: Comment drafts and posting history
- **templates**: Comment templates with categories
- **image_packs**: Image collections for templates
- **fb_accounts**: Facebook accounts with quotas
- **settings**: System configuration (singleton)
- **activity_log**: Audit trail of all actions

### API Endpoints
- `POST /api/ingest` - Ingest new posts from bot
- `GET /api/posts` - Get posts filtered by status
- `POST /api/comments/:id/queue` - Queue comment for posting
- `POST /api/comments/:id/submit` - Submit comment immediately
- `POST /api/posts/:id/skip` - Mark post as skipped
- `GET /api/pm-link/:post_id` - Get Messenger link for author
- `GET /api/templates` - Get comment templates
- `GET /api/settings` - Get system settings
- `PUT /api/settings` - Update system settings
- `GET /api/fb-accounts` - Get Facebook accounts
- `GET /api/search` - Search posts with filters

## 🎯 Usage

### 1. Getting Started
1. **Start the Bot**: Use the existing bot control interface
2. **Access CRM**: Navigate to `/crm` for the main dashboard
3. **Configure Settings**: Go to `/settings` to set up templates and keywords

### 2. Post Review Workflow
1. **Bot Ingests Posts**: Automatically scans Facebook groups
2. **AI Drafts Comments**: Uses templates based on post intent
3. **Human Review**: Review in the Pending tab
4. **Take Action**: Approve, Edit, Submit, or Skip
5. **Track Progress**: Monitor status through the workflow

### 3. Template Management
- **Default Templates**: Pre-configured for Generic, ISO Pivot, CAD, Casting, etc.
- **Variable Substitution**: Use `{{phone}}`, `{{register_url}}`, `{{ask_for}}`
- **Category-based**: Templates automatically selected based on post intent
- **Quick Swapping**: Change templates on-the-fly during review

### 4. Settings Configuration
- **Keywords**: Add/remove negative, service, and ISO keywords
- **Brand Rules**: Configure brand blacklist and allowed modifiers
- **Account Management**: Set up Facebook accounts with daily quotas
- **System Settings**: Configure scan intervals and rate limits

## 🔧 Technical Details

### Database Migration
The system automatically upgrades your existing database:
- Creates new CRM tables alongside legacy tables
- Seeds default templates and settings
- Maintains backward compatibility

### Template Variables
Available template variables:
- `{{register_url}}` → https://welcome.bravocreations.com
- `{{phone}}` → (760) 431-9977
- `{{ask_for}}` → Eugene

### Status Workflow
```
PENDING → APPROVED → QUEUED → POSTED
   ↓
SKIPPED (if rejected)
PM_SENT (if PM action taken)
```

### Rate Limiting
- **Per Account**: Configurable daily quotas (default: 8)
- **Scan Intervals**: Configurable refresh rate (default: 3 minutes)
- **Account Rotation**: Automatic selection of available accounts

## 🚀 First Sprint Implementation

### What's Ready Now
✅ **Database Schema**: Complete CRM database with all tables  
✅ **API Endpoints**: All core CRM functionality  
✅ **Frontend Dashboard**: CRM interface with tabs and cards  
✅ **Settings Management**: Complete configuration interface  
✅ **Template System**: 7 pre-configured templates  
✅ **Search & Filtering**: Advanced post search capabilities  

### What's Coming Next
🔄 **Background Workers**: Automated comment posting  
🔄 **Image Upload**: Image pack management interface  
🔄 **Analytics**: Engagement tracking and reporting  
🔄 **Follow-ups**: Snooze and reminder system  
🔄 **Advanced Quotas**: Per-account usage analytics  

## 🧪 Testing

Run the database test to verify everything is working:

```bash
python test_crm_database.py
```

This will test:
- Database initialization
- Default data seeding
- Template loading
- Settings retrieval
- Search functionality

## 🔗 Integration

### Bot Integration
The bot can now call the CRM API to:
- Ingest posts with metadata
- Get template suggestions
- Report posting success/failure
- Update comment statuses

### Frontend Integration
The CRM integrates with your existing:
- React + TypeScript setup
- Tailwind CSS styling
- shadcn/ui components
- React Router navigation

## 📱 Navigation

- **Home** (`/`): Bot control and system overview
- **CRM** (`/crm`): Main dashboard for post management
- **Settings** (`/settings`): System configuration

## 🎨 UI Components

### Post Cards
- **Left**: Image gallery with carousel
- **Middle**: Post content and author info
- **Right**: Comment draft with template selector
- **Footer**: Action buttons (Approve, Submit, Skip, PM)

### Status Tabs
- **Pending**: Posts awaiting review
- **Approved**: Posts approved but not posted
- **Queued**: Comments queued for posting
- **Posted**: Successfully posted comments
- **Skipped**: Rejected posts
- **PM Sent**: Posts with PM actions

### Settings Tabs
- **General**: Basic configuration
- **Templates**: Comment template management
- **Image Packs**: Image collection management
- **Keywords**: Keyword configuration
- **Accounts**: Facebook account management

## 🔒 Security & Best Practices

- **API Keys**: Secure storage of OpenAI and other API keys
- **Rate Limiting**: Built-in protection against abuse
- **Audit Trail**: Complete logging of all actions
- **Input Validation**: Pydantic models for API requests
- **Error Handling**: Graceful error handling and user feedback

## 🚀 Deployment

### Requirements
- Python 3.8+
- SQLite3
- FastAPI
- React + TypeScript
- Node.js 16+

### Setup
1. **Backend**: The bot API automatically upgrades the database
2. **Frontend**: Build and serve the React app
3. **Configuration**: Use the Settings page to configure the system

### Environment
- **Development**: `http://localhost:5173` (Vite dev server)
- **Production**: Configure your production server and database

## 📞 Support

For questions or issues:
- Check the database test script
- Review the API endpoints
- Examine the frontend console for errors
- Check the bot logs for backend issues

---

**Built for Bravo Creations** - Full-service B2B jewelry manufacturing partner
