import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog

class Topelo(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Mostrar os 20 players com mais mmr")
    async def topelo(self, interact: discord.Interaction):
        load = Embed(
            description=f" {emojis.LOADING} | Carregando... ",
            color=discord.Color.light_embed()
        )
        await interact.response.send_message(embed=load, ephemeral=True)

        await sleep(2)

        guild = db.session.query(db.Guild_Config).filter_by(guild_id=interact.guild.id).first()

        if not guild:
            failed = Embed(
                title=f"{emojis.FAILED} | O servidor precisa está registrado para essa ação!",
                color=discord.Color.red()
            )
            return await interact.edit_original_response(embed=failed)
        
        top_players = db.session.query(db.Users)\
            .filter_by(guild_id=interact.guild.id)\
            .order_by(db.Users.MRR.desc())\
            .limit(20)\
            .all()

        if not top_players:
            failed = Embed(
                title=f"{emojis.FAILED} | Nenhum jogador encontrado!",
                color=discord.Color.red()
            )
            return await interact.edit_original_response(embed=failed)

        embed = Embed(
            title="🏆 Top 20 Jogadores com Maior MMR",
            color=discord.Color.gold()
        )

        for i, player in enumerate(top_players, start=1):
            member = interact.guild.get_member(player.discord_id)
            name = member.display_name if member else f"Desconhecido ({player.discord_id})"
            embed.add_field(
                name=f"#{i} - {name}",
                value=f"MMR: **{player.MRR}**",
                inline=False
            )
        sucess = Embed(
            title=f"{emojis.SUCESS} | Top 20 logo abaixo:",
            color=discord.Color.green()
        )
        await interact.edit_original_response(embed=sucess)
        await interact.followup.send(embed=embed)

# Necessário para o bot carregar a extensão
async def setup(bot):
    await bot.add_cog(Topelo(bot))
