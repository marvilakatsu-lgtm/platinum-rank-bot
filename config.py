import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0")) or None
MOD_CHANNEL_ID = int(os.getenv("MOD_CHANNEL_ID", "0"))
PLATINAS_CHANNEL_ID = int(os.getenv("PLATINAS_CHANNEL_ID", "0"))
MOD_ROLE_ID = int(os.getenv("MOD_ROLE_ID", "0"))
DB_PATH = os.getenv("DB_PATH", "data/colizeu.db")

# Recompensas por platina aprovada
XP_PLATINA = 200
DENARIOS_PLATINA = 50

# Identidade visual (preto, dourado, prata)
COR_OURO = 0xD4AF37
COR_PRATA = 0xC0C0C0
COR_PRETO = 0x0D0D0D
