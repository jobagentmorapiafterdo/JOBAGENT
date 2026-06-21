# Oil & Gas Job Agent — Config
import os

# ── Search ──
# ddgs (DuckDuckGo API backend) — FREE, unlimited, no key needed

# ── Email (Resend) ──
EMAIL_PROVIDER  = os.getenv("EMAIL_PROVIDER", "resend")
RESEND_API_KEY  = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL      = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
FROM_NAME       = os.getenv("FROM_NAME", "Oil & Gas Job Agent")
RECIPIENT       = os.getenv("RECIPIENT_EMAIL", "gregslum@gmail.com")

# ── Telegram ──
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT  = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Schedule ──
CRON = "0 7 * * 2,5"  # Tue & Fri 07:00 UTC = 08:00 Lagos
DELAY = 1.5            # seconds between queries
TIMEOUT = 20           # HTTP timeout

# ── Tue (1-7) / Fri (8-14) ──
TUE_POSITIONS = [
    "Manager","Project Manager","HSE Manager",
    "Maintenance Manager","Maintenance Engineer",
    "HSE Engineer","Safety Engineer",
]
FRI_POSITIONS = [
    "Project Engineer","Corrosion Engineer",
    "Reliability Engineer","Reliability Manager",
    "Facilities Engineer","Operations Integrity",
    "Management of Change Coordinator",
]
POSITIONS = TUE_POSITIONS + FRI_POSITIONS

# ── 50 Countries ──
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

# ── Keywords ──
VISA_KW = [
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

OIL_GAS_KW = [
    "oil and gas","oil & gas","oil gas","upstream","downstream",
    "midstream","petroleum","petrochemical","refinery","refining",
    "offshore","onshore","drilling","exploration","production",
    "LNG","natural gas","pipeline","gas processing","oilfield","energy sector",
]
