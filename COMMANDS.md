# Terminal Commands Reference

## PC (Windows — Development)

### Setup

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy environment template and fill in credentials
Copy-Item .env.example .env
notepad .env
```

### Running the Bot

```powershell
# Activate venv first (if not already active)
.\venv\Scripts\Activate.ps1

# Start the bot
python bot.py
```

### Testing

```powershell
# Run all tests
.\venv\Scripts\python.exe -m pytest tests/ -v

# Run a specific test file
.\venv\Scripts\python.exe -m pytest tests/test_db.py -v
.\venv\Scripts\python.exe -m pytest tests/test_handlers.py -v
.\venv\Scripts\python.exe -m pytest tests/test_reminders.py -v
.\venv\Scripts\python.exe -m pytest tests/test_scheduler.py -v

# Run tests with output (no capture)
.\venv\Scripts\python.exe -m pytest tests/ -v -s

# Run a single test by name
.\venv\Scripts\python.exe -m pytest tests/test_nlp.py::test_function_name -v
```

### Dependency Management

```powershell
# Freeze current packages to requirements.txt
pip freeze > requirements.txt

# Show installed packages
pip list

# Upgrade a package
pip install --upgrade python-telegram-bot
```

### Git

```powershell
# Check status
git status

# Stage and commit
git add .
git commit -m "your message"

# Push to remote
git push origin feature/implement-bot

# Pull latest changes
git pull origin master
```

---

## VM (Ubuntu 22.04 — Production)

### First-Time Setup

```bash
# Run the automated setup script (installs system deps, venv, systemd service)
bash deploy/setup.sh

# Edit .env with real credentials after setup
nano .env
```

### Virtual Environment

```bash
# Activate virtual environment
source venv/bin/activate

# Deactivate
deactivate

# Install/update dependencies inside venv
pip install -r requirements.txt
```

### Running the Bot Manually

```bash
# Activate venv and run directly (useful for debugging)
source venv/bin/activate
python bot.py
```

### systemd Service Management

```bash
# Start the bot service
sudo systemctl start personal-assistant

# Stop the bot service
sudo systemctl stop personal-assistant

# Restart the bot service
sudo systemctl restart personal-assistant

# Check service status
sudo systemctl status personal-assistant

# Enable autostart on boot
sudo systemctl enable personal-assistant

# Disable autostart on boot
sudo systemctl disable personal-assistant

# Reload systemd after editing the service file
sudo systemctl daemon-reload
```

### Logs & Monitoring

```bash
# Follow live service logs via journald
sudo journalctl -u personal-assistant -f

# Show last 100 lines of service logs
sudo journalctl -u personal-assistant -n 100

# Follow the bot's own log file
tail -f bot.log

# Show last 50 lines of bot log
tail -n 50 bot.log
```

### Testing on VM

```bash
source venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_db.py -v
python -m pytest tests/test_reminders.py -v
```

### Database

```bash
# Open SQLite shell (inspect data)
sqlite3 data/assistant.db

# Inside sqlite3: list tables
.tables

# Inside sqlite3: query reminders
SELECT * FROM reminders;

# Exit sqlite3
.quit
```

### File & Directory

```bash
# Check disk usage of data and cache directories
du -sh data/ .cache/

# View .env (without exposing to terminal history)
cat .env

# Edit .env
nano .env
```

### Updates (deploy new code)

```bash
# Pull latest code from git
git pull origin master

# Re-install dependencies if requirements changed
source venv/bin/activate
pip install -r requirements.txt

# Restart the service to apply changes
sudo systemctl restart personal-assistant

# Verify it came back up
sudo systemctl status personal-assistant
```
