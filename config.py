# =============================================================================
# Oil & Gas Job Agent — Configuration
# FREE engines: DDGS (unlimited) + Serper.dev (2500/mo) + Google PSE (100/day)
# Paid upgrade: SerpAPI
# =============================================================================
import os, json

# =============================================================================
# 🔍 SEARCH ENGINE KEYS (all optional — DDGS works without any)
# =============================================================================
SERPER_API_KEY   = os.getenv("SERPER_API_KEY", "")     # https://serper.dev — 2,500 free/mo
GOOGLE_CSE_KEY   = os.getenv("GOOGLE_CSE_KEY", "")     # Google Custom Search — 100/day free
GOOGLE_CSE_CX    = os.getenv("GOOGLE_CSE_CX", "")      # Your search engine ID
SERPAPI_KEY      = os.getenv("SERPAPI_KEY", "")        # Paid fallback

# =============================================================================
# 📧 EMAIL — "resend", "brevo", "sendgrid", "gmail"
# =============================================================================
EMAIL_PROVIDER   = os.getenv("EMAIL_PROVIDER", "resend")
FROM_EMAIL       = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
FROM_NAME        = os.getenv("FROM_NAME", "Oil & Gas Job Agent")
RECIPIENT_EMAIL  = os.getenv("RECIPIENT_EMAIL", "gregslum@gmail.com")
RESEND_API_KEY   = os.getenv("RESEND_API_KEY", "")
BREVO_SMTP_KEY   = os.getenv("BREVO_SMTP_KEY", "")
BREVO_LOGIN      = os.getenv("BREVO_LOGIN", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
GMAIL_ADDRESS    = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASS   = os.getenv("GMAIL_APP_PASS", "")

# =============================================================================
# 🤖 TELEGRAM
# =============================================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

# =============================================================================
# ⏰ SCHEDULE
# =============================================================================
SCHEDULE_CRON = "0 7 * * 2,5"

# =============================================================================
# 🔍 SEARCH SETTINGS
# =============================================================================
REQUEST_TIMEOUT      = 20
SEARCH_DELAY_SECONDS = 1.5   # Polite delay between queries
MAX_RESULTS          = 8

# =============================================================================
# 📋 14 POSITIONS — split Tue (1-7) / Fri (8-14)
# =============================================================================
POSITIONS_WEEK = {
    "tuesday": [
        "Manager", "Project Manager", "HSE Manager",
        "Maintenance Manager", "Maintenance Engineer",
        "HSE Engineer", "Safety Engineer",
    ],
    "friday": [
        "Project Engineer", "Corrosion Engineer",
        "Reliability Engineer", "Reliability Manager",
        "Facilities Engineer", "Operations Integrity",
        "Management of Change Coordinator",
    ],
}
POSITIONS = POSITIONS_WEEK["tuesday"] + POSITIONS_WEEK["friday"]

# =============================================================================
# 🌍 ALL 50 COUNTRIES
# =============================================================================
COUNTRIES = [
    "Trinidad and Tobago","United Arab Emirates","Ghana","Uganda","Kenya",
    "Namibia","Equatorial Guinea","Kazakhstan","Turkmenistan","Uzbekistan",
    "Saudi Arabia","Bahrain","Kuwait","Guyana","Canada",
    "Mozambique","Tanzania","South Africa","Botswana","Sierra Leone",
    "Liberia","Norway","Sweden","United States","Singapore",
    "Brunei","Oman","Qatar","Netherlands","Italy",
    "United Kingdom","Ireland","Argentina","Brazil","Mexico",
    "Suriname","Zambia","Zimbabwe","Malawi","Angola",
    "Senegal","Gambia","Rwanda","Australia","Mauritius",
    "Azerbaijan","Tajikistan","Sao Tome and Principe","Gabon","Congo Brazzaville",
]

# =============================================================================
# 🛂 VISA SPONSORSHIP KEYWORDS (25)
# =============================================================================
VISA_KEYWORDS = [
    "visa sponsorship","visa sponsored","sponsor visa",
    "sponsorship available","work visa sponsorship","employer sponsored visa",
    "work permit sponsorship","sponsor work permit","international candidates welcome",
    "relocation support","relocation package","global mobility",
    "expat package","expatriate package","sponsor employment visa",
    "employment visa sponsorship","will sponsor","can sponsor",
    "sponsorship for","work authorization sponsorship","visa assistance",
    "immigration support","foreign workers welcome","overseas applicants",
    "international applicants welcome",
]

# =============================================================================
# 🛢️ OIL & GAS KEYWORDS (21)
# =============================================================================
OIL_GAS_KEYWORDS = [
    "oil and gas","oil & gas","oil gas","upstream","downstream",
    "midstream","petroleum","petrochemical","refinery","refining",
    "offshore","onshore","drilling","exploration","production",
    "LNG","natural gas","pipeline","gas processing","oilfield","energy sector",
]