import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog

class ConfigMatchClose(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Configurar a quantidade necessaria do evento fechado")
    @app_commands.describe(match_close_count="A quantidade de MMR necessario para um matchmaking fechado")
    async def config_match(self, interact: discord.Interaction, match_close_count: int):
        await interact.response.defer(ephemeral=True)
        load = Embed(
            description=f" {emojis.LOADING} | Carregando... ",
            color=discord.Color.light_embed()
        )
        await interact.edit_original_response(embed=load)

        await sleep(2)
        guild = db.session.query(db.Guild_Config).filter_by(guild_id=interact.guild.id).first()
        if guild:
            if interact.user.get_role(guild.perm_cmd_role_id):
                antigo = guild.match_close_count
                guild.match_close_count = match_close_count
                db.session.commit()

                sucess = Embed(
                    title=f"{emojis.SUCESS} | match_close_count modificado com sucesso!",
                    color=discord.Color.green()
                )
                sucess.add_field(name="Quantidade Antiga:", value=antigo)
                sucess.add_field(name="Quantidade Atual:", value=guild.match_close_count)
                await interact.edit_original_response(embed=sucess)
           
            else:
                failed = Embed(
                    title=f"{emojis.FAILED} | Não possui permissão!",
                    color=discord.Color.red()
                )
                await interact.edit_original_response(embed=failed)

        else:
            failed = Embed(
                    title=f"{emojis.FAILED} | Servidor não está configurado!",
                    color=discord.Color.red()
                )
            await interact.edit_original_response(embed=failed)

# Necessário para o bot carregar a extensão
async def setup(bot):
    await bot.add_cog(ConfigMatchClose(bot))
