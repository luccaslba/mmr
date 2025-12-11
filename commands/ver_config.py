import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog

class VerConfig(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Ver a configuração do bot")
    async def ver_config(self, interact: discord.Interaction):
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

                sucess = Embed(
                    title=f"{emojis.SUCESS} | Informações:",
                    color=discord.Color.green()
                )
                mmr_channel = interact.guild.get_channel(guild.mrr_channel_id)
                matchmaking_channel = interact.guild.get_channel(guild.matchmaking_channel_id)
                confrontos_channel = interact.guild.get_channel(guild.confronto_channel_id)
                perm_cmd_role = interact.guild.get_role(guild.perm_cmd_role_id)
                bdf_role = interact.guild.get_role(guild.bdf_role_id) if guild.bdf_role_id else None
                ranqueada_channel = interact.guild.get_channel(guild.ranqueada_channel_id) if guild.ranqueada_channel_id else None

                sucess.add_field(name="mmr_channel:", value=mmr_channel.mention)
                sucess.add_field(name="matchmaking_channel:", value=matchmaking_channel.mention, inline=False)
                sucess.add_field(name="confrontos_channel:", value=confrontos_channel.mention, inline=False)
                sucess.add_field(name="ranqueada_channel:", value=ranqueada_channel.mention if ranqueada_channel else "Não configurado", inline=False)
                sucess.add_field(name="match_close_count:", value=guild.match_close_count, inline=False)
                sucess.add_field(name="perm_cmd_role:", value=perm_cmd_role, inline=False)
                sucess.add_field(name="bdf_role:", value=bdf_role.mention if bdf_role else "Não configurado", inline=False)
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
    await bot.add_cog(VerConfig(bot))
