# Colizeu Bot — Fase 1

Bot de Discord (discord.py) com perfis, XP, patentes, registro/aprovação de platinas e rankings.

## Rodar localmente
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # preencha os valores
python bot.py
```

## Comandos
/perfil · /platina registrar · /platinas · /ranking · /ajuda

## Estrutura
- `bot.py` – inicialização e sincronização dos comandos
- `config.py` – variáveis de ambiente e constantes (XP, cores)
- `levels.py` – fórmula de nível e patentes
- `database.py` – SQLite (usuários, platinas, logs)
- `cogs/` – perfil, platinas (registro + aprovação por botões), ranking
