import os
from dotenv import load_dotenv

load_dotenv()

# Groq API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "openai/gpt-oss-120b"

# Application Metadata
APP_TITLE = "Reg2Release: From Regulation to Verified Rule Change"
APP_SUBTITLE = "Multi-Agent Regulatory Change & Automated Rule Verification System"
AUTHOR = "Adapala Bhargava Krishna"
AUTHOR_EMAIL = "bk.adapala@gmail.com"
INSTITUTION = "Chaitanya Bharathi Institute of Technology, Hyderabad"
PROJECT_EVENT = "Flarre AI Inc Hackathon 2026"
