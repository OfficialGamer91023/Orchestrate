import os
from datetime import datetime

LOG_FILE = "log.txt"

def append_to_log(role: str, content: str):
    """Append a message to the chat transcript log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {role.upper()}:\n{content}\n\n")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python chat_logger.py <role> <message>")
        sys.exit(1)
        
    role = sys.argv[1]
    message = " ".join(sys.argv[2:])
    append_to_log(role, message)
    print(f"Appended to {LOG_FILE}")
