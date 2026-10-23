import discord
from discord import app_commands
from discord.ext import commands

import config
from levels import nivel_por_xp, patente_por_nivel, barra_progresso


class Perfil(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="perfil", description="Mostra o perfil de um gladiador do Colizeu")
    @app_commands.describe(membro="Quem você quer ver (padrão: você)")
    async def perfil(self, interaction: discord.Interaction, membro: discord.Member | None = None):
        membro = membro or interaction.user
        db = self.bot.db
        user = await db.get_user(membro.id)
        nivel = nivel_por_xp(user["xp"])
        qtd = await db.contar_platinas(membro.id)

        embed = discord.Embed(title=f"🏛️ {membro.display_name}", color=config.COR_OURO)
        embed.set_thumbnail(url=membro.display_avatar.url)
        embed.add_field(name="Patente", value=patente_por_nivel(nivel), inline=True)
        embed.add_field(name="Nível", value=str(nivel), inline=True)
        embed.add_field(name="Denários", value=f"🪙 {user['denarios']}", inline=True)
        embed.add_field(name="XP", value=barra_progresso(user["xp"]), inline=False)
        embed.add_field(name="🏆 Platinas", value=str(qtd), inline=True)
        embed.add_field(name="Rank XP", value=f"#{await db.posicao_xp(user['xp'])}", inline=True)
        embed.add_field(name="Rank Platinas", value=f"#{await db.posicao_platinas(qtd)}", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="platinas", description="Lista os jogos platinados de um membro")
    @app_commands.describe(membro="Quem você quer consultar (padrão: você)")
    async def platinas(self, interaction: discord.Interaction, membro: discord.Member | None = None):
        membro = membro or interaction.user
        rows = await self.bot.db.platinas_do_usuario(membro.id)
        if not rows:
            return await interaction.response.send_message(
                f"{membro.display_name} ainda não tem platinas aprovadas.", ephemeral=True
            )
        linhas = [f"🏆 **{r['game']}** — {r['platform']} ({r['earned_at']})" for r in rows[:25]]
        embed = discord.Embed(
            title=f"Platinas de {membro.display_name}",
            description="\n".join(linhas),
            color=config.COR_PRATA,
        )
        if len(rows) > 25:
            embed.set_footer(text=f"Mostrando 25 de {len(rows)}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ajuda", description="Lista os comandos do Colizeu Bot")
    async def ajuda(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⚔️ Colizeu Bot — Comandos", color=config.COR_OURO)
        embed.description = (
            "`/perfil` — seu perfil ou de outro membro\n"
            "`/platina registrar` — registra uma platina (vai para aprovação)\n"
            "`/platinas` — jogos platinados de um membro\n"
            "`/ranking` — rankings de platinas, XP e mensal\n"
            "`/ajuda` — esta mensagem"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Perfil(bot))
