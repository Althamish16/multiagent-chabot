"""
Simplified server configuration for local development
"""
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent
env_file = ROOT_DIR / '.env'

if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment from {env_file}")
else:
    print(f"⚠️ No .env file found at {env_file}")
    print("Creating default environment configuration...")

# Default configuration for POC development (no external dependencies)
DEFAULT_CONFIG = {
    'MONGO_URL': '',  # Empty = in-memory storage for POC
    'DB_NAME': 'multiagent_chabot_poc',
    'CORS_ORIGINS': 'http://localhost:3000',
    'ENV': 'development',
    'DEBUG': 'true',
    'LOG_LEVEL': 'INFO'
}

def get_config_value(key: str, default: str = None) -> str:
    """Get configuration value with fallback to default"""
    value = os.environ.get(key, default)
    if not value and key in DEFAULT_CONFIG:
        value = DEFAULT_CONFIG[key]
        print(f"⚠️ Using default value for {key}: {value}")
    return value

# Configuration
MONGO_URL = get_config_value('MONGO_URL')
DB_NAME = get_config_value('DB_NAME')
CORS_ORIGINS = get_config_value('CORS_ORIGINS')

# Azure OpenAI Configuration (optional for demo mode)
AZURE_OPENAI_API_KEY = os.environ.get('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_ENDPOINT = os.environ.get('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_API_VERSION = os.environ.get('AZURE_OPENAI_API_VERSION', '2024-02-01')
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = os.environ.get('AZURE_OPENAI_CHAT_DEPLOYMENT_NAME')

# Check if we have Azure OpenAI keys
HAS_LLM_KEYS = bool(AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_CHAT_DEPLOYMENT_NAME)

if not HAS_LLM_KEYS:
    print("✅ POC Mode: Using demo AI responses (no API keys needed)")
    print("💡 Add AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, and AZURE_OPENAI_CHAT_DEPLOYMENT_NAME to .env for real AI responses")

# Google OAuth Configuration (optional)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')

HAS_GOOGLE_CONFIG = all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET])

if not HAS_GOOGLE_CONFIG:
    print("✅ POC Mode: Using demo authentication (no Google OAuth needed)")

# Database check
USE_DATABASE = bool(MONGO_URL and MONGO_URL.strip())
if not USE_DATABASE:
    print("✅ POC Mode: Using in-memory storage (no MongoDB needed)")

# Logging configuration
LOG_LEVEL = get_config_value('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Print configuration summary
print("\n🔧 POC Configuration Summary:")
print(f"   Storage: {'Database (' + MONGO_URL + ')' if USE_DATABASE else 'In-Memory (POC Mode)'}")
print(f"   AI Responses: {'Real LLM' if HAS_LLM_KEYS else 'Demo Mode'}")
print(f"   Authentication: {'Google OAuth' if HAS_GOOGLE_CONFIG else 'Demo Mode'}")
print(f"   CORS Origins: {CORS_ORIGINS}")
print(f"   Log Level: {LOG_LEVEL}")
print(f"\n🎯 POC Status: {'Full Features' if (HAS_LLM_KEYS and HAS_GOOGLE_CONFIG and USE_DATABASE) else 'Demo Mode (Perfect for POC!)'}")
print()

if not env_file.exists():
    print("📝 Creating POC-ready .env file...")
    with open(env_file, 'w') as f:
        f.write("# Multiagent Chatbot POC Configuration\n")
        f.write("# Leave empty for POC demo mode (no external dependencies needed)\n\n")
        f.write("# Backend Configuration\n")
        f.write(f"CORS_ORIGINS={CORS_ORIGINS}\n\n")
        f.write("# Database (Optional - leave empty for in-memory storage)\n")
        f.write("MONGO_URL=\n")
        f.write(f"DB_NAME={DB_NAME}\n\n")
        f.write("# Azure OpenAI Configuration (Optional - leave empty for demo mode)\n")
        f.write("AZURE_OPENAI_API_KEY=\n")
        f.write("AZURE_OPENAI_ENDPOINT=\n")
        f.write("AZURE_OPENAI_API_VERSION=2024-02-01\n")
        f.write("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=\n\n")
        f.write("# Azure AD Configuration (Optional - leave empty for demo auth)\n")
        f.write("AZURE_CLIENT_ID=\n")
        f.write("AZURE_CLIENT_SECRET=\n")
        f.write("AZURE_TENANT_ID=\n")
        f.write("AZURE_REDIRECT_URI=http://localhost:3000/auth/callback\n\n")
        f.write("# Development Settings\n")
        f.write("ENV=development\n")
        f.write("DEBUG=true\n")
        f.write("LOG_LEVEL=INFO\n\n")
        f.write("# POC Instructions:\n")
        f.write("# This configuration runs in full demo mode - no setup required!\n")
        f.write("# For production features, add your API keys above\n")
    
    print(f"✅ Created POC-ready .env file at {env_file}")
    print("🎉 Ready to run! No additional configuration needed for POC")