import os
import sys
from pathlib import Path
import environ
from openai import OpenAI

# Find the base directory (where .env is located)
BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file
env = environ.Env()
env_file = os.path.join(BASE_DIR, '.env')

if os.path.exists(env_file):
    environ.Env.read_env(env_file)
else:
    print(f"Error: .env file not found at {env_file}")
    sys.exit(1)

api_key = env.str('OPENAI_API_KEY', default=None)

if not api_key:
    print("Error: OPENAI_API_KEY not found in .env")
    sys.exit(1)

print("Connecting to OpenAI...")
client = OpenAI(api_key=api_key)

try:
    # Fetch available models
    models = client.models.list()
    
    print("\n--- Available OpenAI Models ---")
    model_ids = sorted([model.id for model in models.data])
    
    # Optional: Highlight common ones like gpt-3.5, gpt-4
    for m in model_ids:
        if "gpt" in m:
            print(f" ⭐ {m}")
        else:
            print(f" - {m}")
            
    print(f"\nTotal models available: {len(model_ids)}")

except Exception as e:
    print(f"Error connecting to OpenAI API: {e}")