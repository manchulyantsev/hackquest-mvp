# HackQuest MVP

A gamified hackathon progress tracking system built with Streamlit. Teams progress through sequential quests, earn XP, and unlock achievements using Hero's Journey mechanics.

## Features

- **Team Authentication**: Secure PIN-based team login with bcrypt hashing
- **Sequential Quest Progression**: Four quests unlocked in order (Idea → Team Roles → MVP → Presentation)
- **XP & Leveling System**: Earn 100 XP per quest completion
- **Profile Dashboard**: View team progress, level, and submitted artifacts
- **Tavern Information Hub**: Access hackathon details and quest mechanics
- **Google Sheets Persistence**: Reliable data storage without traditional backend
- **Datadog Analytics**: Track stage completion metrics for organizer insights

## Tech Stack

- **Frontend/Backend**: Streamlit
- **Database**: Google Sheets (via gspread)
- **Authentication**: bcrypt
- **Analytics**: Datadog HTTP API
- **Testing**: pytest, Hypothesis (property-based testing)

## Setup Instructions

### Prerequisites

- Python 3.9 or higher
- Google Cloud Platform account with Sheets API enabled
- Datadog account (optional, for analytics)

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd hackquest-mvp
pip install -r requirements.txt
```

### 2. Google Sheets Setup

1. Create a new Google Sheet with the following columns in the first row:
   ```
   Team_Name | PIN_Hash | Stage | XP | Idea_Text | Roles_Text | GitHub_Link | Pitch_Link | Timestamp
   ```

2. Create a Google Cloud Platform service account:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable Google Sheets API
   - Create service account credentials
   - Download the JSON key file

3. Share your Google Sheet with the service account email (found in the JSON key file)

4. Note your Google Sheets document ID (from the URL: `https://docs.google.com/spreadsheets/d/{DOCUMENT_ID}/edit`)

### 3. Datadog Setup (Optional)

1. Sign up for [Datadog](https://www.datadoghq.com/)
2. Generate an API key from Organization Settings → API Keys
3. Note your Datadog site (e.g., `datadoghq.com`, `datadoghq.eu`)

### 4. Configure Secrets

1. Copy the example secrets file:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

2. Edit `.streamlit/secrets.toml` and fill in your credentials:
   - Paste your Google service account JSON content into `[gcp_service_account]`
   - Add your Google Sheets document ID
   - Add your Datadog API key and site

3. **Important**: Never commit `.streamlit/secrets.toml` to version control

### 5. Run the Application

```bash
streamlit run hackquest/app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

### For Participants

1. **Create Team**: Enter a team name and PIN (first time)
2. **Login**: Use your team name and PIN to access your progress
3. **Complete Quests**: Submit artifacts for each unlocked quest
4. **Earn XP**: Gain 100 XP per quest completion
5. **View Profile**: Check your level, XP, and submitted artifacts
6. **Visit Tavern**: Read hackathon info and quest mechanics

### For Organizers

1. **Monitor Progress**: Access Google Sheets directly to view all team data
2. **Analytics**: View stage completion metrics in Datadog dashboard
3. **PIN Recovery**: Help teams recover lost PINs (see PIN Recovery Process below)

## Quest Structure

1. **Quest 1: The Call to Adventure** - Submit your hackathon idea (1-1000 characters)
2. **Quest 2: Gathering the Party** - Define team roles (1-1000 characters)
3. **Quest 3: The Road of Trials** - Submit GitHub repository link (1-1000 characters)
4. **Quest 4: The Return** - Submit presentation link (1-1000 characters)

Each quest awards 100 XP and unlocks the next quest.

## PIN Recovery Process

If a team loses their PIN, organizers can help them recover access by updating the PIN_Hash in Google Sheets.

### Steps for Admins

1. **Verify Team Identity**: Confirm the team's identity through other means (email, Slack, in-person verification)

2. **Locate Team in Google Sheets**: 
   - Open your HackQuest Google Sheet
   - Find the team's row by searching for their Team_Name

3. **Generate New PIN Hash**:
   ```python
   # Run this Python code to generate a new PIN hash
   import bcrypt
   
   # Choose a new PIN for the team
   new_pin = "temporary_pin_1234"
   
   # Generate the hash
   pin_hash = bcrypt.hashpw(new_pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
   
   print(f"New PIN: {new_pin}")
   print(f"PIN Hash to paste in Google Sheets: {pin_hash}")
   ```

4. **Update PIN_Hash in Google Sheets**:
   - Copy the generated PIN hash
   - Paste it into the PIN_Hash column (column B) for the team's row
   - Save the changes

5. **Communicate New PIN**: Securely share the new PIN with the team (not the hash)

### Alternative: Using the update_team_pin Function

If you have Python access to the system, you can use the built-in function:

```python
from hackquest.auth import hash_pin
from hackquest.database import update_team_pin
import gspread

# Initialize Google Sheets client
gc = gspread.service_account(filename='path/to/credentials.json')
sheet = gc.open_by_key('your_sheet_id').sheet1

# Generate new PIN hash
new_pin = "temporary_pin_1234"
new_pin_hash = hash_pin(new_pin)

# Update the team's PIN
success = update_team_pin("Team Alpha", new_pin_hash, sheet)

if success:
    print(f"PIN updated successfully for Team Alpha")
    print(f"New PIN: {new_pin}")
else:
    print("Team not found")
```

### Security Notes

- Always verify team identity before resetting PINs
- Use secure channels to communicate new PINs (not public chat)
- Consider using temporary PINs and asking teams to change them
- Log all PIN recovery actions for audit purposes

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=hackquest --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run only property-based tests
pytest tests/property/

# Run only integration tests
pytest tests/integration/
```

### Project Structure

```
hackquest/
├── hackquest/           # Main application code
│   ├── __init__.py
│   ├── app.py          # Streamlit entry point
│   ├── auth.py         # Authentication logic
│   ├── database.py     # Google Sheets operations
│   ├── analytics.py    # Datadog integration
│   ├── quests.py       # Quest logic and validation
│   └── ui_components.py # UI rendering functions
├── tests/
│   ├── unit/           # Unit tests
│   ├── property/       # Property-based tests
│   └── integration/    # Integration tests
├── .streamlit/
│   └── secrets.toml.example  # Configuration template
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Troubleshooting

### Google Sheets Connection Issues

- Verify service account email has edit access to the sheet
- Check that Google Sheets API is enabled in GCP
- Ensure `google_sheets_id` in secrets.toml matches your document ID
- Verify JSON credentials are properly formatted (no extra quotes or escaping)

### Authentication Errors

- PINs are case-sensitive
- Team names are case-sensitive
- First login creates a new team; subsequent logins require exact match

### Rate Limit Errors

- Google Sheets API has rate limits (100 requests per 100 seconds per user)
- The app automatically retries with exponential backoff (up to 3 attempts)
- If rate limits persist, wait a few minutes before retrying

### Datadog Metrics Not Appearing

- Verify API key is correct in secrets.toml
- Check Datadog site matches your account region
- Datadog failures don't block quest completion (fail-open design)
- Check Streamlit logs for Datadog error messages

## Security Notes

- PINs are hashed with bcrypt before storage (never stored in plaintext)
- API credentials are loaded from Streamlit secrets (not hardcoded)
- Team data is isolated (teams can only access their own data)
- Generic error messages prevent username enumeration

## License

MIT License

## Support

For issues or questions, please contact the hackathon organizers.
