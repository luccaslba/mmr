import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog
from ui.buttons.vip_role import AddVipView

class ConfigVips(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Configurar o cargo vip")
    async def config_vip(self, interact: discord.Interaction):
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
                    title=f"Para adicionar, deletar ou configurar um cargo, clique no botão relacionado abaixo:",
                    color=discord.Color.green()
                )

                await interact.edit_original_response(embed=sucess, view=AddVipView())

            else:
                failed = Embed(
                        title=f"{emojis.FAILED} | Não possui permissão!",
                        color=discord.Color.red()
                    )
                await interact.edit_original_response(embed=failed)
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Servidor não configurado!",
                color=discord.Color.red()
            )
            await interact.edit_original_response(embed=failed)

# Necessário para o bot carregar a extensão
async def setup(bot):
    await bot.add_cog(ConfigVips(bot))
