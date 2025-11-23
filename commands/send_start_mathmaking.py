import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog
from ui.buttons.start_mathmaking import StartMatchMaking

class SendStartMatchMaking(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Envia o Iniciar Matchmaking")
    async def send_mathmaking(self, interact: discord.Interaction):

        load = Embed(
            description=f" {emojis.LOADING} | Carregando... ",
            color=discord.Color.light_embed()
        )
        await interact.response.send_message(embed=load, ephemeral=True)

        await sleep(2)

        guild = db.session.query(db.Guild_Config).filter_by(guild_id=interact.guild.id).first()
        if guild:

            if interact.user.get_role(guild.perm_cmd_role_id):

                mrr_channel = interact.guild.get_channel(guild.mrr_channel_id)

                send = Embed(
                    title=f"Enviado no canal: {mrr_channel.mention}",
                    color=discord.Color.light_embed()
                )

                mrr = Embed(
                    title="Start Matchmaking",
                    description="Clique no botão abaixo para iniciar um matchmaking:",
                    color=discord.Color.light_embed()
                )

                await interact.edit_original_response(embed=send)
                await mrr_channel.send(embed=mrr, view=StartMatchMaking(self.bot))

async def setup(bot):
    await bot.add_cog(SendStartMatchMaking(bot))
