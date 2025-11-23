import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog

class Perfilelo(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Ver as informações de um usuario!")
    @app_commands.describe(user="O usuario que deseja ver as informações")
    async def perfilelo(self, interact: discord.Interaction, user: discord.Member):

        load = Embed(
            description=f" {emojis.LOADING} | Carregando... ",
            color=discord.Color.light_embed()
        )
        await interact.response.send_message(embed=load, ephemeral=True)

        await sleep(2)

        user_db = db.session.query(db.Users).filter_by(discord_id=user.id).first()
        MMR_value = "Not register"
        sucess = Embed(
            title=f"{emojis.SUCESS} | Informações:",
            color=discord.Color.green()
        )
        if not user_db:

            info = Embed(
                title="📄 | Informações:",
                color=discord.Color.green()
            )
            info.add_field(name="Mention:", value=user.mention)
            info.add_field(name="Name:", value=user.name)
            info.add_field(name="Display Name:", value=user.display_name, inline=False)
            info.add_field(name="ID:", value=user.id, inline=False)
            info.add_field(name="MMR:", value=MMR_value, inline=False)

            await interact.edit_original_response(embed=sucess)
            await interact.followup.send(embed=info)
           
        else:
            MMR_value = str(user_db.MRR)
            info = Embed(
                title="📄 | Informações:",
                color=discord.Color.green()
            )
            info.add_field(name="Mention:", value=user.mention)
            info.add_field(name="Name:", value=user.name)
            info.add_field(name="Display Name:", value=user.display_name, inline=False)
            info.add_field(name="ID:", value=user.id, inline=False)
            info.add_field(name="MMR:", value=MMR_value, inline=False)
            
            await interact.edit_original_response(embed=sucess)
            await interact.followup.send(embed=info)

async def setup(bot):
    await bot.add_cog(Perfilelo(bot))
