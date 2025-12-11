import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog

class ConfigRanqueada(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Configurar o canal de partidas ranqueadas")
    @app_commands.describe(canal="O canal onde será enviado o botão de ranqueada")
    async def config_ranqueada(self, interact: discord.Interaction, canal: discord.TextChannel):
        await interact.response.defer(ephemeral=True)
        load = Embed(
            description=f" {emojis.LOADING} | Carregando... ",
            color=discord.Color.light_embed()
        )
        await interact.edit_original_response(embed=load)

        await sleep(2)
        guild = db.session.query(db.Guild_Config).filter_by(guild_id=interact.guild.id).first()
        if guild:
            if interact.user.get_role(guild.perm_cmd_role_id) or interact.user.id == config_bot.OWNER_ID:
                antigo = guild.ranqueada_channel_id
                antigo_channel = interact.guild.get_channel(antigo) if antigo else None

                guild.ranqueada_channel_id = canal.id
                db.session.commit()

                sucess = Embed(
                    title=f"{emojis.SUCESS} | Canal de ranqueada configurado!",
                    color=discord.Color.green()
                )
                sucess.add_field(name="Canal Antigo:", value=antigo_channel.mention if antigo_channel else "Não configurado", inline=False)
                sucess.add_field(name="Canal Atual:", value=canal.mention, inline=False)
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
    await bot.add_cog(ConfigRanqueada(bot))
