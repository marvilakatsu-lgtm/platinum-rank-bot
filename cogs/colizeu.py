import logging
import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from cogs.platinas import eh_moderador
from levels import nivel_por_xp, patente_por_nivel

PODIO = [("🥇", config.COR_OURO), ("🥈", config.COR_PRATA), ("🥉", 0xCD7F32)]


class Colizeu(commands.Cog):
    """Mantém uma mensagem-painel sempre atualizada no canal #colizeu."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.loop_atualizar.start()

    async def cog_unload(self):
        self.loop_atualizar.cancel()

    @tasks.loop(minutes=10)
    async def loop_atualizar(self):
        try:
            await self.atualizar()
        except Exception:
            logging.exception("Falha ao atualizar o painel do Colizeu")

    @loop_atualizar.before_loop
    async def _antes(self):
        await self.bot.wait_until_ready()

    async def _membro(self, guild: discord.Guild, user_id: int):
        m = guild.get_member(user_id)
        if m:
            return m
        try:
            return await guild.fetch_member(user_id)
        except discord.HTTPException:
            return None

    async def _foto_platina(self, guild: discord.Guild, platina) -> str | None:
        """Busca a mensagem original para obter um link de imagem válido (links do Discord expiram)."""
        canal = guild.get_channel(config.MOD_CHANNEL_ID)
        if canal and platina["proof_msg_id"]:
            try:
                msg = await canal.fetch_message(platina["proof_msg_id"])
                if msg.embeds and msg.embeds[0].image:
                    return msg.embeds[0].image.url
                if msg.attachments:
                    return msg.attachments[0].url
            except discord.HTTPException:
                pass
        return None

    async def montar_embeds(self, guild: discord.Guild) -> list[discord.Embed]:
        db = self.bot.db
        top = await db.ranking_completo(10)
        agora = int(discord.utils.utcnow().timestamp())

        cabecalho = discord.Embed(
            title="🏛️ COLIZEU — Hall dos Gladiadores",
            description=f"Os maiores caçadores de platinas da arena.\nAtualizado <t:{agora}:R>",
            color=config.COR_OURO,
        )
        if not top:
            cabecalho.add_field(name="Arena vazia", value="Nenhuma platina aprovada ainda. Use `/platina registrar`!")
            return [cabecalho]

        embeds = [cabecalho]
        for i, row in enumerate(top[:3]):
            medalha, cor = PODIO[i]
            membro = await self._membro(guild, row["user_id"])
            nome = membro.display_name if membro else f"<@{row['user_id']}>"
            nivel = nivel_por_xp(row["xp"])
            ultimas = await db.ultimas_platinas(row["user_id"], 3)
            jogos = "\n".join(f"🏆 {p['game']} ({p['platform']})" for p in ultimas)

            e = discord.Embed(title=f"{medalha} {nome}", color=cor)
            e.description = (
                f"**{row['platinas']}** platinas • **{patente_por_nivel(nivel)}** • Nível {nivel} • {row['xp']} XP\n\n"
                f"**Últimas conquistas**\n{jogos}"
            )
            if membro:
                e.set_thumbnail(url=membro.display_avatar.url)
            foto = await self._foto_platina(guild, ultimas[0]) if ultimas else None
            if foto:
                e.set_image(url=foto)
            embeds.append(e)

        if len(top) > 3:
            linhas = []
            for i, row in enumerate(top[3:], start=4):
                membro = await self._membro(guild, row["user_id"])
                nome = membro.display_name if membro else f"<@{row['user_id']}>"
                patente = patente_por_nivel(nivel_por_xp(row["xp"]))
                linhas.append(f"`{i:>2}.` **{nome}** — 🏆 {row['platinas']} • {patente}")
            embeds.append(
                discord.Embed(title="⚔️ Demais gladiadores", description="\n".join(linhas), color=config.COR_PRETO)
            )
        return embeds

    async def atualizar(self) -> bool:
        if not config.COLIZEU_CHANNEL_ID:
            return False
        canal = self.bot.get_channel(config.COLIZEU_CHANNEL_ID)
        if canal is None:
            return False
        embeds = await self.montar_embeds(canal.guild)

        msg_id = await self.bot.db.get_kv("colizeu_msg_id")
        if msg_id:
            try:
                msg = await canal.fetch_message(int(msg_id))
                await msg.edit(content=None, embeds=embeds)
                return True
            except discord.NotFound:
                pass  # mensagem apagada: cria outra
        msg = await canal.send(embeds=embeds)
        await self.bot.db.set_kv("colizeu_msg_id", str(msg.id))
        return True

    @app_commands.command(name="colizeu", description="Atualiza o painel do canal #colizeu (moderadores)")
    async def colizeu(self, interaction: discord.Interaction):
        if not eh_moderador(interaction.user):
            return await interaction.response.send_message("Apenas moderadores.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        ok = await self.atualizar()
        await interaction.followup.send(
            "✅ Painel atualizado!" if ok else "Não achei o canal. Confira COLIZEU_CHANNEL_ID e as permissões do bot.",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Colizeu(bot))
