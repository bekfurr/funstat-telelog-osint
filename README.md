OFFICIAL PROJECT https://funstat.in/
FIRST, YOU NEED TO GET JWT TOKEN FOR API, WITHOT TOKEN IT'S NOT WORKING
YOU CAN GET TOKEN VIA OFFICAL TELELOG OSINT TELEGRAM BOT WITH DEPOSIT ACCAUNT(WITHOUT DEPOSIT IT WONT GIVE TOKEN)
# Funstat OSINT Web Interface

Flask proxy + vanilla JS frontend for the Funstat Telegram OSINT API.  
Single file, no build step, dark terminal UI. All endpoints exposed.

## Features
- All 20 Funstat API v1 endpoints (Groups, Users, Text search)
- Bearer token auth forwarded via proxy (no CORS)
- Query parameter forwarding including repeated arrays
- Balance/cost info visible in raw JSON response
- Pagination handled where applicable

## Prerequisites
- Python 3.7+
- `pip install flask requests`

## Installation
```bash
git clone <repo-url>
cd telelog-osint
pip install -r requirements.txt  # if provided, else pip install flask requests
python app.py
