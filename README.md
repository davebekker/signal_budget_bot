# Signal Budget Bot (Async Python)

A Python-based budgeting tool that tracks a shared balance via Signal. This project replaces a legacy MicroPython/Raspberry Pi Pico web server with a more robust, asynchronous messaging bot.

## Features
- **Asynchronous Polling:** Listens for commands via the Signal CLI REST API.
- **Auto-Allowance:** Automatically adds a configurable "pocket money" amount every 7 days.
- **Multi-User Support:** Recognizes commands from both the primary number (SyncMessages) and group members (DataMessages).
- **Persistent Storage:** Saves state to a local JSON file.

## Commands
- `/balance`: Check the current pot total.
- `/add <amount> [comment]`: Add money with an optional description.
- `/sub <amount> [comment]`: Record a spend/withdrawal.
- `/history`: View the 10 most recent transactions.
- `/set <amount>`: Update the weekly allowance figure.
- `/usage`: Display command help.

## Setup

1. **Prerequisites:**
   - A running instance of [signal-cli-rest-api](https://github.com/bbernhard/signal-cli-rest-api).
   - Python 3.8+

2. **Installation:**
   ```bash
   git clone <your-repo-url>
   cd signal-budget-bot
   pip install -r requirements.txt
```

3. **Configuration:**
Create a .env file in the root directory:
```env
SIGNAL_NUMBER="+1234567890"
RECIPIENT_NUMBER="+1234567890"
```

4. **Run**
```bash
python3 budget_bot.py
```