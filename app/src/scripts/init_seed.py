import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

import asyncio
from src.core.models.seed import create_default_users
if __name__ == "__main__":
    asyncio.run(create_default_users())
