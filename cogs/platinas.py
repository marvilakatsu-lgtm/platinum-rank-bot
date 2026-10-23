import datetime as dt
import discord
from discord import app_commands
from discord.ext import commands

import config
from levels import patente_por_nivel


def eh_moderador(member: discord.Member) -> bool:
    if member.guild_permissions.manage_guild:
        return True
    return config.MOD_ROLE_ID and any(r.id == config.MOD_ROLE_ID for r in member.roles)


async def sincronizar_patente(guild: discord.Guild, member: discord.Member, nivel: int):
    """Dá o cargo da patente atual e remove as outras. Cria o cargo se não existir."""
    from levels import PATENTES

    nomes = [n for _, n in PATENTES]
    alvo_nome = patente_por_nivel(nivel)
    alvo = discord.utils.get(guild.roles, name=alvo_nome)
    try:
        if alvo is None:
            alvo = await guild.create_role(name=alvo_nome, color=discord.Color(config.COR_OURO))
        remover = [r for r in member.roles if r.name in nomes and r != alvo]
        if remover:
            await member.remove_roles(*remover, reason="Colizeu: mudança de patente")
        if alvo not in member.roles:
            await member.add_roles(alvo, reason="Colizeu: nova patente")
    except discord.Forbidden:
        pass  # o cargo do bot precisa estar ACIMA dos cargos de patente


class RevisaoView(discord.ui.View):
    """Botões persistentes: continuam funcionando após reiniciar o bot."""

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def _processar(self, interaction: discord.Interaction, aprovar: bool):
        if not eh_moderador(interaction.user):
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)

        db = self.bot.db
        platina_id = int(interaction.message.embeds[0].footer.text.split(":")[1])
        p = await db.get_platina(platina_id)
        if p is None or p["status"] != "pending":
            return await interaction.response.send_message("Este registro já foi processado.", ephemeral=True)

        novo_status = "approved" if aprovar else "rejected"
        await db.set_status(platina_id, novo_status, interaction.user.id)
        await db.log(interaction.user.id, f"platina_{novo_status}", f"id={platina_id} user={p['user_id']}")

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green() if aprovar else discord.Color.red()
        embed.add_field(
            name="Resultado",
            value=f"{'✅ Aprovada' if aprovar else '❌ Rejeitada'} por {interaction.user.mention}",
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=None)

        membro = interaction.guild.get_member(p["user_id"])
        if aprovar:
            antigo, novo, _ = await db.add_reward(p["user_id"], config.XP_PLATINA, config.DENARIOS_PLATINA)
            if membro:
                await sincronizar_patente(interaction.guild, membro, novo)
            canal = interaction.guild.get_channel(config.PLATINAS_CHANNEL_ID)
            if canal:
                anuncio = discord.Embed(
                    title="🏆 NOVA PLATINA NO COLIZEU!",
                    description=f"<@{p['user_id']}> conquistou a platina de **{p['game']}** ({p['platform']})!",
                    color=config.COR_OURO,
                )
                anuncio.set_image(url=p["proof_url"])
                anuncio.set_footer(text=f"+{config.XP_PLATINA} XP • +{config.DENARIOS_PLATINA} Denários")
                if novo > antigo:
                    anuncio.add_field(name="⬆️ Subiu de nível!", value=f"Agora é nível **{novo}** — {patente_por_nivel(novo)}")
                await canal.send(embed=anuncio)
        elif membro:
            try:
                await membro.send(f"Sua platina de **{p['game']}** foi rejeitada. Fale com a moderação se tiver dúvidas.")
            except discord.Forbidden:
                pass

    @discord.ui.button(label="Aprovar", style=discord.ButtonStyle.success, custom_id="plat:approve")
    async def aprovar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._processar(interaction, True)

    @discord.ui.button(label="Rejeitar", style=discord.ButtonStyle.danger, custom_id="plat:reject")
    async def rejeitar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._processar(interaction, False)


class Platinas(commands.GroupCog, name="platina"):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(RevisaoView(self.bot))

    @app_commands.command(name="registrar", description="Registre uma platina para aprovação da moderação")
    @app_commands.describe(
        jogo="Nome do jogo",
        plataforma="Ex.: PS5, PS4, PC, Xbox",
        data="Data da conquista (DD/MM/AAAA)",
        captura="Print da platina como comprovante",
    )
    async def registrar(
        self,
        interaction: discord.Interaction,
        jogo: str,
        plataforma: str,
        data: str,
        captura: discord.Attachment,
    ):
        try:
            d = dt.datetime.strptime(data, "%d/%m/%Y").date()
        except ValueError:
            return await interaction.response.send_message("Data inválida. Use DD/MM/AAAA.", ephemeral=True)
        if d > dt.date.today():
            return await interaction.response.send_message("A data não pode estar no futuro.", ephemeral=True)
        if not (captura.content_type or "").startswith("image/"):
            return await interaction.response.send_message("O comprovante precisa ser uma imagem.", ephemeral=True)

        jogo, plataforma = jogo.strip()[:100], plataforma.strip()[:30]
        db = self.bot.db
        if await db.platina_duplicada(interaction.user.id, jogo, plataforma):
            return await interaction.response.send_message(
                "Você já registrou essa platina (pendente ou aprovada).", ephemeral=True
            )

        canal = interaction.guild.get_channel(config.MOD_CHANNEL_ID)
        if canal is None:
            return await interaction.response.send_message(
                "Canal de moderação não configurado. Avise um administrador.", ephemeral=True
            )

        # Guarda a imagem no registro; em produção, prefira reenviar o arquivo ao canal da moderação
        # para o link não expirar. Aqui reenviamos e guardamos a URL do canal.
        arquivo = await captura.to_file()
        embed = discord.Embed(title="🏆 Platina aguardando aprovação", color=config.COR_PRATA)
        embed.add_field(name="Membro", value=interaction.user.mention)
        embed.add_field(name="Jogo", value=jogo)
        embed.add_field(name="Plataforma", value=plataforma)
        embed.add_field(name="Data", value=d.strftime("%d/%m/%Y"))
        embed.set_image(url=f"attachment://{arquivo.filename}")

        await interaction.response.defer(ephemeral=True)
        msg = await canal.send(embed=embed, file=arquivo, view=RevisaoView(self.bot))
        url = msg.embeds[0].image.url if msg.embeds and msg.embeds[0].image else captura.url
        platina_id = await db.criar_platina(interaction.user.id, jogo, plataforma, d.isoformat(), url)
        embed.set_footer(text=f"ID:{platina_id}")
        await msg.edit(embed=embed)
        await db.log(interaction.user.id, "platina_registrada", f"id={platina_id} jogo={jogo}")
        await interaction.followup.send("✅ Registro enviado para a moderação!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Platinas(bot))
