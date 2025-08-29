# 🤖 LLM Comment Generation Setup

## Overview

The bot now supports real AI-generated comments using OpenAI's GPT models, with automatic fallback to templates if the LLM fails.

## 🚀 Setup Steps

### 1. Get OpenAI API Key

- Go to [OpenAI Platform](https://platform.openai.com/api-keys)
- Create a new API key
- Copy the key

### 2. Set Environment Variable

Create a `.env` file in the `bot/` directory:

```bash
OPENAI_API_KEY=your_actual_api_key_here
```

### 3. Install Dependencies

The OpenAI package is already in `requirements.txt`. If you need to install it:

```bash
pip install openai
```

## ⚙️ Configuration

### LLM Settings (in `bravo_config.py`)

```python
"openai": {
    "enabled": True,                    # Enable/disable LLM
    "model": "gpt-4o-mini",            # Model to use
    "max_tokens": 150,                  # Max comment length
    "temperature": 0.7,                 # Creativity (0.0-1.0)
    "fallback_to_templates": True       # Use templates if LLM fails
}
```

### Available Models

- `gpt-4o-mini` (recommended - fast & cost-effective)
- `gpt-3.5-turbo` (cheaper alternative)
- `gpt-4` (highest quality, most expensive)

## 🔧 How It Works

1. **Post Classification**: Bot classifies posts as "service", "iso", or "general"
2. **LLM Generation**: Sends appropriate prompt to OpenAI with post context
3. **Fallback**: If LLM fails, automatically uses pre-written templates
4. **Quality Control**: All comments include required contact info

## 💰 Cost Estimation

- **GPT-4o-mini**: ~$0.00015 per comment
- **GPT-3.5-turbo**: ~$0.00002 per comment
- **1000 comments**: $0.15 (GPT-4o-mini) or $0.02 (GPT-3.5-turbo)

## 🎯 Prompt Examples

### Service Posts

```
You are Bravo Creations, a professional jewelry manufacturing company.
Generate a friendly, professional comment for a Facebook post requesting
jewelry services (CAD, casting, stone setting, engraving, enameling, finishing).
Keep it under 150 characters. Include: (760) 431-9977 and welcome.bravocreations.com.
Ask them to ask for Eugene. Be helpful but not pushy.
```

### ISO Posts

```
You are Bravo Creations, a professional jewelry manufacturing company.
Generate a friendly comment for a Facebook post where someone is looking
for jewelry (ISO - in search of). Mention that while you don't stock it,
you can make it with CAD + casting + setting. Keep it under 150 characters.
Include: (760) 431-9977 and welcome.bravocreations.com. Ask them to ask for Eugene.
Be encouraging and helpful.
```

## 🚨 Troubleshooting

### LLM Not Working?

1. Check your API key is set correctly
2. Verify you have OpenAI credits
3. Check the logs for error messages
4. The bot will automatically fallback to templates

### Comments Too Long?

- Reduce `max_tokens` in config
- Adjust prompts to be more specific about length

### Comments Too Generic?

- Increase `temperature` for more creativity
- Refine prompts to be more specific

## 🔄 Disabling LLM

To use only templates, set in `bravo_config.py`:

```python
"openai": {
    "enabled": False
}
```

The bot will automatically use the template system instead.
