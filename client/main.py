import sys
from app import ChatApp

def main():
    URL = sys.argv[1] if len(sys.argv) > 1 else None
    if not URL:
        print("Usage: python main.py wss://server.com")
        sys.exit(1)
    
    app = ChatApp(url=URL)
    app.run()

if __name__ == "__main__":
    main()