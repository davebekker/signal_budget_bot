import asyncio
import aiohttp
import json
import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Configuration ---
SIGNAL_API_BASE = "http://localhost:8080"
REGISTERED_NUMBER = os.getenv("SIGNAL_NUMBER")
GROUP_ID = os.getenv("RECIPIENT_NUMBER") 

STATE_FILE = "budget_state.json"
POLL_INTERVAL = 2

logging.basicConfig(level=logging.INFO)

class BudgetBot:
    def __init__(self):
        self.state = self.load_state()

    def load_state(self):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {
                "balance": 0.0,
                "weekly_amount": 1.0, 
                "last_weekly_update": datetime.now().strftime("%Y-%m-%d"),
                "history": []
            }

    def save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=4)

    def add_transaction(self, amount, comment):
        self.state["balance"] += amount
        self.state["history"].append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "amount": amount,
            "comment": comment if comment else "Manual Entry"
        })
        self.state["history"] = self.state["history"][-10:]
        self.save_state()
        return self.state["balance"]

    async def handle_command(self, text):
        parts = text.split()
        if not parts: return None
        cmd = parts[0].lower()
        
        try:
            if cmd in ["/usage", "/help"]:
                return (
                    "📖 *Budget Bot Usage*\n"
                    "• /balance - Show current balance\n"
                    "• /add [amount] [reason] - Add funds (e.g., `/add 10.50 birthday`)\n"
                    "• /sub [amount] [reason] - Withdraw (e.g., `/sub 5 coffee`)\n"
                    "• /history - Show last 10 transactions\n"
                    "• /set [amount] - Change weekly allowance\n"
                    "• /usage - Show this menu"
                )
            elif cmd == "/balance":
                return f"💰 Balance: £{self.state['balance']:.2f}"
            
            elif cmd == "/history":
                if not self.state["history"]:
                    return "📜 No transactions yet."
                h_lines = [f"• {h['date']}: £{h['amount']:.2f} ({h['comment']})" for h in self.state["history"]]
                return "📜 Recent History:\n" + "\n".join(h_lines)

            elif cmd in ["/add", "/sub", "/withdraw"] and len(parts) > 1:
                try:
                    amt = float(parts[1])
                    # Join all parts after the amount to create the comment
                    comment = " ".join(parts[2:]) if len(parts) > 2 else ""
                    
                    if cmd in ["/sub", "/withdraw"]:
                        amt = -amt
                        action = "Subtracted"
                    else:
                        action = "Added"
                        
                    self.add_transaction(amt, comment)
                    return f"✅ {action} £{abs(amt):.2f}. New Balance: £{self.state['balance']:.2f}"
                except ValueError:
                    return "⚠️ Invalid amount. Use: /add 5.00 chocolate"

            elif cmd == "/set" and len(parts) > 1:
                self.state["weekly_amount"] = float(parts[1])
                self.save_state()
                return f"⚙️ Weekly amount set to £{self.state['weekly_amount']:.2f}"
                
        except Exception as e:
            return f"⚠️ Error: {str(e)}"
        return None

async def send_signal_message(session, text):
    payload = {
        "message": text,
        "number": REGISTERED_NUMBER,
        "recipients": [GROUP_ID]
    }
    try:
        async with session.post(f"{SIGNAL_API_BASE}/v2/send", json=payload) as resp:
            if resp.status not in [200, 201]:
                logging.error(f"Failed to send: {await resp.text()}")
    except Exception as e:
        logging.error(f"Send error: {e}")

async def poll_signal_messages(bot):
    async with aiohttp.ClientSession() as session:
        logging.info("Sending startup notification...")
        startup_msg = (f"🚀 Budget Bot is online!\n"
                       f"💰 Balance: £{bot.state['balance']:.2f}\n"
                       f"📅 Weekly: £{bot.state['weekly_amount']:.2f}")
        await send_signal_message(session, startup_msg)

        while True:
            try:
                receive_url = f"{SIGNAL_API_BASE}/v1/receive/{REGISTERED_NUMBER}"
                async with session.get(receive_url, timeout=10) as resp:
                    if resp.status == 200:
                        raw_text = await resp.text()
                        if raw_text and raw_text.strip() != "null":
                            messages = json.loads(raw_text)
                            for msg in messages:
                                envelope = msg.get("envelope", {})
                                
                                # Check standard dataMessage (from others)
                                incoming_text = envelope.get("dataMessage", {}).get("message")
                                
                                # Check syncMessage (from you)
                                if not incoming_text:
                                    sync_msg = envelope.get("syncMessage", {})
                                    incoming_text = sync_msg.get("sentMessage", {}).get("message")
                                
                                if incoming_text and incoming_text.startswith("/"):
                                    response_text = await bot.handle_command(incoming_text)
                                    if response_text:
                                        await send_signal_message(session, response_text)
            except Exception as e:
                logging.error(f"Polling error: {e}")
            await asyncio.sleep(POLL_INTERVAL)

async def weekly_task(bot):
    while True:
        now = datetime.now()
        last_date = datetime.strptime(bot.state["last_weekly_update"], "%Y-%m-%d")
        
        if (now - last_date).days >= 7:
            weeks = (now - last_date).days // 7
            total = weeks * bot.state["weekly_amount"]
            bot.add_transaction(total, f"Auto-allowance ({weeks} wks)")
            bot.state["last_weekly_update"] = (last_date + timedelta(weeks=weeks)).strftime("%Y-%m-%d")
            bot.save_state()
            logging.info(f"Automatically added £{total}")
            
        await asyncio.sleep(3600)

async def main():
    bot = BudgetBot()
    await asyncio.gather(
        poll_signal_messages(bot),
        weekly_task(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())