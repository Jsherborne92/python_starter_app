from dotenv import load_dotenv
import os

load_dotenv()

def main():
    print("Environment variable:", os.getenv("EXAMPLE_VAR"))

if __name__ == "__main__":
    main()
