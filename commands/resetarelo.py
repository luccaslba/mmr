import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog

class Resetarelo(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Reseta os MMR de todos os usuarios")
    async def resetarelo(self, interact: discord.Interaction):

        load = Embed(
            description=f" {emojis.LOADING} | Carregando... ",
            color=discord.Color.light_embed()
        )
        await interact.response.send_message(embed=load, ephemeral=True)

        await sleep(2)

        guild = db.session.query(db.Guild_Config).filter_by(guild_id=interact.guild.id).first()
        users = db.session.query(db.Users).all()
        if guild:
            if interact.user.get_role(guild.perm_cmd_role_id) or interact.user.id == config_bot.OWNER_ID:
                count = 0
                for _, user in enumerate(users, start=1):
                    if user.MRR != 0:  # Reseta qualquer valor diferente de 0 (positivo ou negativo)
                        user.MRR = 0
                        db.session.add(user)
                        db.session.commit()
                        count += 1

                sucess = Embed(
                    title=f"{emojis.SUCESS} | Todos os MMR de todos os usuarios resetados!",
                    color=discord.Color.green()
                )
                sucess.add_field(name="Total resetados:", value=count)
                await interact.edit_original_response(embed=sucess)
            else:
                failed = Embed(
                    title=f"{emojis.FAILED} | Sem permissão para usar esse comando!",
                    color=discord.Color.red()
                )
                return await interact.edit_original_response(embed=failed)
        else:

            failed = Embed(
                title=f"{emojis.FAILED} | O servidor precisa está registrado para essa ação!",
                color=discord.Color.red()
            )
            return await interact.edit_original_response(embed=failed)

async def setup(bot):
    await bot.add_cog(Resetarelo(bot))
