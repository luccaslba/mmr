import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog

class Config(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Configurar o bot")
    @app_commands.describe(mrr_channel="O canal que será enviado o MRR", matchmaking_channel="O canal que será enviado os matchmaking", perm_cmd="Cargo que terá permissão para usar os comandos", match_close_count="A quantidade de MMR necessario para um matchmaking fechado")
    async def config(self, interact: discord.Interaction, mrr_channel: discord.TextChannel, matchmaking_channel: discord.TextChannel, perm_cmd: discord.Role, match_close_count: int, confronto_channel: discord.TextChannel):
        await interact.response.defer(ephemeral=True)
        load = Embed(
            description=f" {emojis.LOADING} | Carregando... ",
            color=discord.Color.light_embed()
        )
        await interact.edit_original_response(embed=load)

        await sleep(2)
        if interact.user.id == config_bot.OWNER_ID: 
            guild = db.session.query(db.Guild_Config).filter_by(guild_id=interact.guild.id).first()
            if not guild:
                        
                add_guild = db.Guild_Config(interact.guild.id, interact.guild.name, mrr_channel.id, matchmaking_channel.id, perm_cmd.id, match_close_count, confronto_channel.id)
                db.session.add(add_guild)
                db.session.commit()

                sucess = Embed(
                    title=f"{emojis.SUCESS} | Servidor configurado com sucesso!",
                    color=discord.Color.green()
                )
                await interact.edit_original_response(embed=sucess)
           
            else:
                guild.guild_id = interact.guild.id
                guild.guild_name = interact.guild.name
                guild.mrr_channel_id = mrr_channel.id
                guild.matchmaking_channel_id = matchmaking_channel.id
                guild.perm_cmd_role_id = perm_cmd.id
                guild.match_close_count = match_close_count
                guild.confronto_channel_id = confronto_channel.id

                db.session.add(guild)
                db.session.commit()

                sucess = Embed(
                    title=f"{emojis.SUCESS} | Configurado com sucesso!",
                    color=discord.Color.green()
                )
                await interact.edit_original_response(embed=sucess)

        else:
            failed = Embed(
                    title=f"{emojis.FAILED} | Não possui permissão!",
                    color=discord.Color.red()
                )
            await interact.edit_original_response(embed=failed)

# Necessário para o bot carregar a extensão
async def setup(bot):
    await bot.add_cog(Config(bot))
