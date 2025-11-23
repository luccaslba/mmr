import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog

class Register(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Registrar-se no banco de dados")
    async def register(self, interact: discord.Interaction):
        await interact.response.defer(ephemeral=True)
        load = Embed(
            description=f" {emojis.LOADING} | Carregando... ",
            color=discord.Color.light_embed()
        )
        await interact.edit_original_response(embed=load)

        await sleep(2)

        user = db.session.query(db.Users).filter_by(discord_id=interact.user.id).first()
        if not user:
            add_user = db.Users(interact.user.id, interact.user.name, 0, interact.guild.id)
            db.session.add(add_user)
            db.session.commit()

            sucess = Embed(
                    title=f"{emojis.SUCESS} | Registrado com sucesso!",
                    color=discord.Color.green()
                )
            await interact.edit_original_response(embed=sucess)
           
        else:
             
            failed = Embed(
                    title=f"{emojis.FAILED} | Já registrado!",
                    color=discord.Color.red()
                )
            await interact.edit_original_response(embed=failed)

async def setup(bot):
    await bot.add_cog(Register(bot))
