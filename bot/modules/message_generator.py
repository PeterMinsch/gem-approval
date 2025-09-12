"""
Message Generator Module
Handles AI-powered generation of personalized DM messages for Facebook Messenger outreach
"""

import logging
import json
import asyncio
from typing import Dict, List, Optional
import time

# Handle different OpenAI library versions
try:
    from openai import AsyncOpenAI
    OPENAI_VERSION = 'v1'
except ImportError:
    try:
        import openai
        AsyncOpenAI = None
        OPENAI_VERSION = 'legacy'
    except ImportError:
        openai = None
        AsyncOpenAI = None
        OPENAI_VERSION = 'none'

logger = logging.getLogger(__name__)

class MessageGenerator:
    """Generates personalized DM messages using AI for sales outreach"""
    
    def __init__(self, config: dict):
        """
        Initialize MessageGenerator
        
        Args:
            config: Configuration dictionary containing OpenAI API key and business settings
        """
        self.config = config
        self.openai_api_key = config.get('OPENAI_API_KEY')
        self.client = None
        
        # Business context for message personalization
        self.business_context = {
            'company_name': 'Bravo Creations',
            'services': ['CAD design', 'casting', 'stone setting', 'engraving', 'enamel work'],
            'phone': config.get('PHONE', '(760) 431-9977'),
            'website': config.get('REGISTER_URL', 'https://welcome.bravocreations.com'),
            'contact_person': config.get('ASK_FOR', 'Eugene')
        }
        
        # Initialize OpenAI client if API key is available
        if self.openai_api_key and OPENAI_VERSION != 'none':
            if OPENAI_VERSION == 'v1' and AsyncOpenAI:
                self.client = AsyncOpenAI(api_key=self.openai_api_key)
                logger.info("✅ MessageGenerator initialized with OpenAI v1+ client")
            elif OPENAI_VERSION == 'legacy' and openai:
                openai.api_key = self.openai_api_key
                self.client = openai
                logger.info("✅ MessageGenerator initialized with legacy OpenAI client")
            else:
                self.client = None
                logger.warning("⚠️ OpenAI library version not supported")
        else:
            self.client = None
            if not self.openai_api_key:
                logger.warning("⚠️ No OpenAI API key found - will use template-only generation")
            else:
                logger.warning("⚠️ OpenAI library not installed - will use template-only generation")
    
    @property
    def dm_system_prompt(self) -> str:
        """System prompt for AI DM generation"""
        return f"""You are a professional B2B jewelry manufacturing sales assistant for {self.business_context['company_name']}.

Generate personalized direct messages for Facebook Messenger outreach to jewelry professionals.

COMPANY CONTEXT:
- Full-service B2B jewelry manufacturer
- Services: {', '.join(self.business_context['services'])}
- Target: Jewelry store owners, independent jewelers, designers
- Contact: {self.business_context['phone']} • {self.business_context['website']}

MESSAGE REQUIREMENTS:
- TONE: Professional but friendly, conversational
- LENGTH: 2-3 sentences maximum (keep it brief for mobile)
- GOAL: Get them interested in visiting website or calling
- PERSONALIZATION: Reference their specific post content
- NO PUSHY SALES: Offer value, don't hard sell

AVOID:
- Generic greetings
- Long paragraphs  
- Multiple questions
- Aggressive sales language
- Mentioning competitors

FOCUS:
- Show you read their post
- Offer relevant services
- Make it easy to take next step"""

    def format_user_prompt(self, context: dict) -> str:
        """Format the user prompt with post context"""
        return f"""Generate a personalized Facebook Messenger DM for this jewelry professional:

RECIPIENT: {context['author_name']}
POST CONTENT: "{context['post_text'][:400]}"
POST TYPE: {context['post_type']}
JEWELRY CATEGORIES: {', '.join(context.get('categories', []))}

Create a message that:
1. Shows you read their specific post
2. Offers relevant {self.business_context['company_name']} services
3. Includes our contact info: {self.business_context['website']} • {self.business_context['phone']}
4. Mentions asking for {self.business_context['contact_person']}

Keep it conversational and brief - this is a direct message, not an email."""

    def prepare_message_context(self, comment_data: dict) -> dict:
        """
        Prepare context data for message generation
        
        Args:
            comment_data: Comment queue data from database
            
        Returns:
            Context dictionary for AI generation
        """
        return {
            'author_name': comment_data.get('post_author', 'there'),
            'post_text': comment_data.get('post_text', '')[:500],  # Truncate for API limits
            'post_type': comment_data.get('post_type', 'general'),
            'categories': json.loads(comment_data.get('detected_categories', '[]')),
            'business_info': self.business_context
        }
    
    def select_fallback_template(self, post_type: str, categories: List[str]) -> str:
        """
        Select appropriate fallback template when AI generation fails
        
        Args:
            post_type: Type of post (service, iso, etc.)
            categories: Detected jewelry categories
            
        Returns:
            Template string with placeholders
        """
        templates = {
            'service': f"Hi {{author_name}}! Saw your jewelry work - impressive craftsmanship! We're {self.business_context['company_name']}, a full-service manufacturer specializing in CAD, casting, and setting. Would love to chat about potential partnership opportunities. {self.business_context['website']} • {self.business_context['phone']} - ask for {self.business_context['contact_person']}",
            
            'iso': f"Hi {{author_name}}! Great style in your post! We don't stock pieces, but this is exactly what we manufacture daily with CAD + casting + setting. Quick turnaround, quality focus. {self.business_context['website']} • {self.business_context['phone']} - ask for {self.business_context['contact_person']}",
            
            'general': f"Hi {{author_name}}! Noticed your jewelry post - beautiful work! We're {self.business_context['company_name']}, full-service B2B manufacturing (CAD, casting, setting, engraving). Always looking to connect with quality jewelers. {self.business_context['website']} • {self.business_context['phone']} - ask for {self.business_context['contact_person']}"
        }
        
        # Determine best template based on post type and categories
        if 'iso' in post_type.lower() or any('iso' in cat.lower() for cat in categories):
            return templates['iso']
        elif 'service' in post_type.lower():
            return templates['service'] 
        else:
            return templates['general']
    
    def generate_template_message(self, context: dict) -> str:
        """
        Generate message using templates only (fallback method)
        
        Args:
            context: Message context data
            
        Returns:
            Generated message string
        """
        template = self.select_fallback_template(context['post_type'], context['categories'])
        
        # Fill in template variables
        message = template.format(
            author_name=context['author_name']
        )
        
        logger.info(f"📝 Generated template message for {context['author_name']}")
        return message
    
    async def generate_ai_message(self, context: dict) -> str:
        """
        Generate message using OpenAI API
        
        Args:
            context: Message context data
            
        Returns:
            AI-generated message string
        """
        if not self.client:
            raise Exception("OpenAI client not initialized")
        
        start_time = time.time()
        
        try:
            if OPENAI_VERSION == 'v1':
                # New OpenAI v1+ API
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",  # Fast and cost-effective
                    messages=[
                        {"role": "system", "content": self.dm_system_prompt},
                        {"role": "user", "content": self.format_user_prompt(context)}
                    ],
                    max_tokens=200,  # Keep messages concise
                    temperature=0.7,  # Balanced creativity
                    timeout=30.0  # 30 second timeout
                )
                message = response.choices[0].message.content.strip()
                
            elif OPENAI_VERSION == 'legacy':
                # Legacy OpenAI API (synchronous)
                response = self.client.ChatCompletion.create(
                    model="gpt-3.5-turbo",  # Fallback to stable model
                    messages=[
                        {"role": "system", "content": self.dm_system_prompt},
                        {"role": "user", "content": self.format_user_prompt(context)}
                    ],
                    max_tokens=200,
                    temperature=0.7,
                )
                message = response['choices'][0]['message']['content'].strip()
                
            else:
                raise Exception("Unsupported OpenAI version")
            
            generation_time = time.time() - start_time
            logger.info(f"🤖 Generated AI message for {context['author_name']} in {generation_time:.2f}s")
            return message
            
        except Exception as e:
            logger.error(f"❌ AI generation failed for {context['author_name']}: {e}")
            raise
    
    async def generate_dm_message(self, comment_data: dict) -> dict:
        """
        Main method to generate personalized DM message
        
        Args:
            comment_data: Comment queue data from database
            
        Returns:
            Dictionary with generated message and metadata
        """
        context = self.prepare_message_context(comment_data)
        
        logger.info(f"🎯 Generating DM message for {context['author_name']} (post type: {context['post_type']})")
        
        # Try AI generation first, fall back to templates
        try:
            if self.client:
                message = await self.generate_ai_message(context)
                generation_method = 'ai'
            else:
                raise Exception("No OpenAI client available")
                
        except Exception as e:
            logger.warning(f"⚠️ AI generation failed, using template fallback: {e}")
            message = self.generate_template_message(context)
            generation_method = 'template'
        
        # Validate message length (Facebook Messenger limits)
        if len(message) > 1000:
            logger.warning(f"⚠️ Message too long ({len(message)} chars), truncating")
            message = message[:950] + "..."
        
        result = {
            'message': message,
            'author_name': context['author_name'],
            'generation_method': generation_method,
            'character_count': len(message),
            'post_type': context['post_type']
        }
        
        logger.info(f"✅ Generated {len(message)}-char message using {generation_method} method")
        return result

# Export for easy importing
__all__ = ['MessageGenerator']