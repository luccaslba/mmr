# ARQUIVO DEPRECATED - Use .env ao invés deste
# Veja .env.example para configurar suas credenciais

import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "m!")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
