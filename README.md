# Bravo Bot API with Comment Approval Workflow

A FastAPI-based API layer that connects your React frontend with a Facebook comment bot, featuring a **Comment Approval Workflow** system.

## 🎯 **What This System Does**

Instead of the bot posting comments immediately, it now:
1. **Scans Facebook posts** continuously
2. **Generates AI comments** for suitable posts
3. **Queues comments for your approval** instead of posting them
4. **Lets you approve, edit, or reject** each comment
5. **Posts only approved comments** when you're ready

## 🚀 **Key Features**

- ✅ **Comment Queuing**: Bot generates comments and adds them to an approval queue
- ✅ **Human Review**: You can approve, edit, or reject each comment
- ✅ **Continuous Operation**: Bot keeps scanning while you review comments
- ✅ **Comment History**: Track all approved, rejected, and posted comments
- ✅ **Real-time Updates**: Frontend automatically refreshes the queue
- ✅ **Bot Control**: Start/stop the bot and monitor its status

## 🏗️ **Architecture**

```
Facebook Posts → Bot Scanner → Comment Generation → Approval Queue → Human Review → Posting
```

## 📋 **Prerequisites**

- Python 3.8+
- Node.js 16+
- Chrome browser (for Selenium)
- Facebook account credentials

## 🛠️ **Installation**

### 1. Install Python Dependencies
```bash
cd bot
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies
```bash
npm install
```

## 🚀 **Quick Start**

### 1. Start the API Server
```bash
cd bot
python start_api.py
# Or use the batch file on Windows:
start_api.bat
```

The API will be available at: `http://localhost:8000`

### 2. Start the Frontend
```bash
npm run dev
```

The frontend will be available at: `http://localhost:8080`

### 3. Access the System
- **Bot Control**: Manage bot start/stop and monitor status
- **Comment Approval**: Review and approve generated comments
- **Comment History**: Track all comment decisions

## 🔌 **API Endpoints**

### Bot Control
- `POST /bot/start` - Start the bot with comment queuing
- `POST /bot/stop` - Stop the running bot
- `GET /bot/status` - Get current bot status
- `GET /health` - Health check endpoint

### Comment Approval Workflow
- `GET /comments/queue` - Get pending comments for approval
- `GET /comments/history` - Get comment history (approved/rejected/posted)
- `POST /comments/approve` - Approve, reject, or edit a comment

### Comment Generation
- `POST /bot/comment` - Generate a comment for a specific post (testing)

### Configuration
- `GET /config` - Get current bot configuration
- `PUT /config` - Update bot configuration

## 🎮 **How to Use the Approval Workflow**

### 1. Start the Bot
- Go to the **Bot Control** section
- Click **Start Bot**
- The bot will begin scanning Facebook posts and queuing comments

### 2. Review Comments
- Go to the **Comment Approval Workflow** section
- You'll see pending comments in the queue
- For each comment, you can:
  - **Approve**: Comment is approved for posting
  - **Edit**: Modify the comment text and approve
  - **Reject**: Reject with a reason

### 3. Monitor Progress
- **Stats cards** show counts of pending, approved, rejected, and posted comments
- **Comment History** tracks all decisions
- **Real-time updates** every 10 seconds

## 🔧 **Configuration**

The bot uses configuration from `bravo_config.py`:
- Facebook group URLs
- Comment templates
- Filtering rules
- Rate limits

## 🧪 **Testing**

Test the approval workflow:
```bash
cd bot
python test_approval.py
```

This will:
1. Start the bot
2. Generate test comments
3. Test approval/rejection/editing
4. Verify the workflow

## 📱 **Frontend Components**

### BotControl
- Start/stop bot
- Monitor bot status
- Configure bot parameters

### CommentApproval
- Review pending comments
- Approve/reject/edit comments
- View comment history
- Real-time statistics

## 🔄 **Workflow States**

Comments progress through these states:
1. **pending** - Generated, waiting for review
2. **approved** - Approved for posting
3. **rejected** - Rejected with reason
4. **posted** - Successfully posted to Facebook

## 🚨 **Troubleshooting**

### CORS Issues
- Ensure the API server is running on port 8000
- Check that `localhost:8080` is in the CORS allow list
- Restart the API server after CORS changes

### Bot Not Starting
- Check Chrome browser installation
- Verify Facebook credentials in config
- Check console logs for errors

### Comments Not Appearing
- Verify the bot is running
- Check the approval queue endpoint
- Ensure the bot has proper permissions

## 🔮 **Future Enhancements**

- **Database Integration**: Replace in-memory storage with PostgreSQL
- **Batch Operations**: Approve/reject multiple comments at once
- **Scheduled Posting**: Set specific times for approved comments
- **Analytics Dashboard**: Track performance metrics
- **Team Collaboration**: Multiple reviewers and approval workflows

## 📄 **License**

This project is for educational and personal use.

## 🤝 **Support**

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation at `http://localhost:8000/docs`
3. Check console logs for error details

---

**Happy Commenting! 🚀**
