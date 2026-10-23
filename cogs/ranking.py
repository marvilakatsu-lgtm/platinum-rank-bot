import datetime as dt
import discord
from discord import app_commands
from discord.ext import commands

import config

MEDALHAS = ["🥇", "🥈", "🥉"]


class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ranking", description="Veja as classificações do Colizeu")
    @app_commands.describe(tipo="Qual ranking exibir")
    @app_commands.choices(
        tipo=[
            app_commands.Choice(name="Platinas (total)", value="platinas"),
            app_commands.Choice(name="XP", value="xp"),
            app_commands.Choice(name="Platinas do mês", value="mensal"),
        ]
    )
    async def ranking(self, interaction: discord.Interaction, tipo: app_commands.Choice[str]):
        db = self.bot.db
        if tipo.value == "platinas":
            rows, titulo, unidade = await db.ranking_platinas(), "Ranking de Platinas", "🏆"
        elif tipo.value == "xp":
            rows, titulo, unidade = await db.ranking_xp(), "Ranking de XP", "XP"
        else:
            mes = dt.date.today().strftime("%Y-%m")
            rows, titulo, unidade = await db.ranking_mensal(mes), f"Platinas de {mes}", "🏆"

        if not rows:
            return await interaction.response.send_message("Ainda não há dados nesse ranking.", ephemeral=True)

        linhas = []
        for i, r in enumerate(rows):
            pos = MEDALHAS[i] if i < 3 else f"`{i + 1}.`"
            linhas.append(f"{pos} <@{r['user_id']}> — **{r['valor']}** {unidade}")
        embed = discord.Embed(title=f"🏛️ {titulo}", description="\n".join(linhas), color=config.COR_OURO)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Ranking(bot))
