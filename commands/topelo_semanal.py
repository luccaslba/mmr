import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog


class TopeloSemanal(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Mostrar os 20 players com mais pontos no ranking semanal")
    async def topelo_semanal(self, interact: discord.Interaction):
        load = Embed(
            description=f"{emojis.LOADING} | Carregando...",
            color=discord.Color.light_embed()
        )
        await interact.response.send_message(embed=load, ephemeral=True)

        await sleep(1)

        guild = db.session.query(db.Guild_Config).filter_by(guild_id=interact.guild.id).first()

        if not guild:
            failed = Embed(
                title=f"{emojis.FAILED} | O servidor precisa estar registrado para essa ação!",
                color=discord.Color.red()
            )
            return await interact.edit_original_response(embed=failed)

        top_players = db.session.query(db.UsersWeekly)\
            .filter_by(guild_id=interact.guild.id)\
            .order_by(db.UsersWeekly.MRR.desc())\
            .limit(20)\
            .all()

        if not top_players:
            failed = Embed(
                title=f"{emojis.FAILED} | Nenhum jogador no ranking semanal!",
                description="O ranking semanal está vazio. Participe de eventos para aparecer aqui!",
                color=discord.Color.red()
            )
            return await interact.edit_original_response(embed=failed)

        # Filtrar apenas quem tem pontos > 0
        top_players_com_pontos = [p for p in top_players if p.MRR > 0]

        if not top_players_com_pontos:
            info = Embed(
                title="📊 Ranking Semanal",
                description="Nenhum jogador com pontos nesta semana ainda.\nParticipe de eventos para aparecer aqui!",
                color=discord.Color.orange()
            )
            return await interact.edit_original_response(embed=info)

        embed = Embed(
            title="📊 Top 20 - Ranking Semanal",
            description="Pontuação acumulada nesta semana",
            color=discord.Color.blue()
        )

        medalhas = {1: "🥇", 2: "🥈", 3: "🥉"}

        for i, player in enumerate(top_players_com_pontos, start=1):
            member = interact.guild.get_member(player.discord_id)
            name = member.display_name if member else f"Desconhecido ({player.discord_id})"
            medalha = medalhas.get(i, f"#{i}")

            embed.add_field(
                name=f"{medalha} {name}",
                value=f"Pontos: **{player.MRR}**",
                inline=False
            )

        success = Embed(
            title=f"{emojis.SUCESS} | Ranking Semanal:",
            color=discord.Color.green()
        )
        await interact.edit_original_response(embed=success)
        await interact.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TopeloSemanal(bot))
