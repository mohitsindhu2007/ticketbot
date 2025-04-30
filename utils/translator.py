import logging
import re
import json
import os
import sqlite3
from utils.database import get_db_connection

# Set up logging
logger = logging.getLogger(__name__)

# Language codes for supported languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese (Simplified)",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish"
}

# Basic translations for common support phrases
# In a real implementation, this would use a proper translation API
BASIC_TRANSLATIONS = {
    "ticket_created": {
        "en": "Your ticket has been created.",
        "es": "Su ticket ha sido creado.",
        "fr": "Votre ticket a été créé.",
        "de": "Ihr Ticket wurde erstellt.",
        "it": "Il tuo ticket è stato creato.",
        "pt": "Seu ticket foi criado.",
        "nl": "Uw ticket is aangemaakt.",
        "ru": "Ваш тикет создан.",
        "ja": "チケットが作成されました。",
        "ko": "티켓이 생성되었습니다.",
        "zh": "您的工单已创建。",
        "ar": "تم إنشاء تذكرتك.",
        "hi": "आपका टिकट बना दिया गया है।",
        "tr": "Biletiniz oluşturuldu."
    },
    "ticket_closed": {
        "en": "This ticket has been closed.",
        "es": "Este ticket ha sido cerrado.",
        "fr": "Ce ticket a été fermé.",
        "de": "Dieses Ticket wurde geschlossen.",
        "it": "Questo ticket è stato chiuso.",
        "pt": "Este ticket foi fechado.",
        "nl": "Dit ticket is gesloten.",
        "ru": "Этот тикет закрыт.",
        "ja": "このチケットは閉じられました。",
        "ko": "이 티켓이 닫혔습니다.",
        "zh": "此工单已关闭。",
        "ar": "تم إغلاق هذه التذكرة.",
        "hi": "यह टिकट बंद कर दिया गया है।",
        "tr": "Bu bilet kapatıldı."
    },
    "waiting_for_response": {
        "en": "We are waiting for a response from the support team.",
        "es": "Estamos esperando una respuesta del equipo de soporte.",
        "fr": "Nous attendons une réponse de l'équipe de support.",
        "de": "Wir warten auf eine Antwort vom Support-Team.",
        "it": "Stiamo aspettando una risposta dal team di supporto.",
        "pt": "Estamos aguardando uma resposta da equipe de suporte.",
        "nl": "We wachten op een reactie van het ondersteuningsteam.",
        "ru": "Мы ждем ответа от службы поддержки.",
        "ja": "サポートチームからの返答を待っています。",
        "ko": "지원팀의 응답을 기다리고 있습니다.",
        "zh": "我们正在等待支持团队的回复。",
        "ar": "نحن في انتظار رد من فريق الدعم.",
        "hi": "हम सपोर्ट टीम से प्रतिक्रिया का इंतजार कर रहे हैं।",
        "tr": "Destek ekibinden yanıt bekliyoruz."
    },
    "how_can_we_help": {
        "en": "How can we help you today?",
        "es": "¿Cómo podemos ayudarte hoy?",
        "fr": "Comment pouvons-nous vous aider aujourd'hui?",
        "de": "Wie können wir Ihnen heute helfen?",
        "it": "Come possiamo aiutarti oggi?",
        "pt": "Como podemos ajudá-lo hoje?",
        "nl": "Hoe kunnen we u vandaag helpen?",
        "ru": "Чем мы можем помочь вам сегодня?",
        "ja": "本日はどのようにお手伝いできますか？",
        "ko": "오늘 어떻게 도와 드릴까요?",
        "zh": "今天我们能为您做些什么？",
        "ar": "كيف يمكننا مساعدتك اليوم؟",
        "hi": "आज हम आपकी कैसे मदद कर सकते हैं?",
        "tr": "Bugün size nasıl yardımcı olabiliriz?"
    },
    "thank_you": {
        "en": "Thank you for contacting us.",
        "es": "Gracias por contactarnos.",
        "fr": "Merci de nous avoir contactés.",
        "de": "Vielen Dank, dass Sie uns kontaktiert haben.",
        "it": "Grazie per averci contattato.",
        "pt": "Obrigado por nos contactar.",
        "nl": "Bedankt voor uw contact.",
        "ru": "Спасибо, что связались с нами.",
        "ja": "お問い合わせありがとうございます。",
        "ko": "연락해 주셔서 감사합니다.",
        "zh": "感谢您与我们联系。",
        "ar": "شكرا لاتصالك بنا.",
        "hi": "हमसे संपर्क करने के लिए धन्यवाद।",
        "tr": "Bizimle iletişime geçtiğiniz için teşekkür ederiz."
    }
}

def initialize_translation_system():
    """Initialize the translation system in the database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create user language preferences table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_languages (
            user_id INTEGER PRIMARY KEY,
            language_code TEXT NOT NULL,
            auto_translate BOOLEAN DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create guild language settings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS guild_languages (
            guild_id INTEGER PRIMARY KEY,
            default_language TEXT NOT NULL DEFAULT 'en',
            auto_translate BOOLEAN DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        logger.info("Translation system initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing translation system: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def set_user_language(user_id, language_code, auto_translate=False):
    """Set a user's preferred language"""
    conn = None
    try:
        if language_code not in SUPPORTED_LANGUAGES:
            return False
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO user_languages (user_id, language_code, auto_translate, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, language_code, auto_translate))
        
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error setting user language: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_user_language(user_id):
    """Get a user's preferred language"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT language_code, auto_translate
        FROM user_languages
        WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                "language_code": result[0],
                "auto_translate": bool(result[1]),
                "language_name": SUPPORTED_LANGUAGES.get(result[0], "Unknown")
            }
        else:
            return {
                "language_code": "en",
                "auto_translate": False,
                "language_name": "English"
            }
        
    except Exception as e:
        logger.error(f"Error getting user language: {e}")
        return {
            "language_code": "en",
            "auto_translate": False,
            "language_name": "English"
        }
    finally:
        if conn:
            conn.close()

def set_guild_language(guild_id, language_code, auto_translate=False):
    """Set a guild's default language"""
    conn = None
    try:
        if language_code not in SUPPORTED_LANGUAGES:
            return False
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO guild_languages (guild_id, default_language, auto_translate, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (guild_id, language_code, auto_translate))
        
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error setting guild language: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_guild_language(guild_id):
    """Get a guild's default language"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT default_language, auto_translate
        FROM guild_languages
        WHERE guild_id = ?
        ''', (guild_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                "language_code": result[0],
                "auto_translate": bool(result[1]),
                "language_name": SUPPORTED_LANGUAGES.get(result[0], "Unknown")
            }
        else:
            return {
                "language_code": "en",
                "auto_translate": False,
                "language_name": "English"
            }
        
    except Exception as e:
        logger.error(f"Error getting guild language: {e}")
        return {
            "language_code": "en",
            "auto_translate": False,
            "language_name": "English"
        }
    finally:
        if conn:
            conn.close()

def translate_text(text, target_language="en"):
    """
    Translate text to the target language
    
    In a real implementation, this would call a translation API like Google Translate,
    DeepL, or Microsoft Translator. For this example, we'll use a simple dictionary
    of predefined translations.
    """
    if target_language not in SUPPORTED_LANGUAGES:
        target_language = "en"
    
    # Check if this is one of our predefined phrases
    for key, translations in BASIC_TRANSLATIONS.items():
        for lang, phrase in translations.items():
            if text.strip() == phrase:
                # Found an exact match, return the translation in the target language
                return BASIC_TRANSLATIONS[key].get(target_language, text)
    
    # In a real implementation, call the translation API here
    # For now, just append a note that translation would happen
    if target_language != "en":
        return f"{text} [Would be translated to {SUPPORTED_LANGUAGES[target_language]}]"
    else:
        return text

def detect_language(text):
    """
    Detect the language of a text
    
    In a real implementation, this would use a language detection API or library.
    For this example, we'll use a simple pattern matching approach.
    """
    # Simple language detection for demo purposes
    # In a real implementation, use a proper language detection library
    
    # Check for exact matches in our translations
    for key, translations in BASIC_TRANSLATIONS.items():
        for lang, phrase in translations.items():
            if text.strip() == phrase:
                return lang
    
    # Simple heuristics for demo purposes
    text = text.lower()
    
    # Spanish markers
    if re.search(r'\b(hola|gracias|ayuda|por favor|cómo)\b', text):
        return "es"
        
    # French markers
    if re.search(r'\b(bonjour|merci|s\'il vous plaît|comment|puis-je)\b', text):
        return "fr"
        
    # German markers
    if re.search(r'\b(hallo|danke|bitte|wie|kann ich)\b', text):
        return "de"
        
    # Japanese markers (very simplified)
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
        return "ja"
        
    # Chinese markers (very simplified)
    if re.search(r'[\u4E00-\u9FFF]', text):
        return "zh"
        
    # Korean markers (very simplified)
    if re.search(r'[\uAC00-\uD7AF]', text):
        return "ko"
        
    # Arabic markers (very simplified)
    if re.search(r'[\u0600-\u06FF]', text):
        return "ar"
        
    # Hindi markers (very simplified)
    if re.search(r'[\u0900-\u097F]', text):
        return "hi"
        
    # Default to English
    return "en"

def get_supported_languages():
    """Get a list of supported languages"""
    return {code: name for code, name in SUPPORTED_LANGUAGES.items()}

# Initialize translation system on module import
initialize_translation_system()