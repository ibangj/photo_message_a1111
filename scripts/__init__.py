import os
import sys

print("[Photo Message] Loading scripts...")
print(f"[Photo Message] Current directory: {os.path.dirname(os.path.abspath(__file__))}")

# Add the scripts directory to Python path
scripts_dir = os.path.dirname(os.path.abspath(__file__))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)
    print(f"[Photo Message] Added to Python path: {scripts_dir}")

import main  # Direct import after adding to path 