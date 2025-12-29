import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog
from ui.buttons.cargo_premiacao import ConfigCargoPremiacaoView


class ConfigCargoPremiacao(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Configurar cargos de premiação para eventos")
    async def config_cargo_premiacao(self, interact: discord.Interaction):
        await interact.response.defer(ephemeral=True)

        load = Embed(
            description=f"{emojis.LOADING} | Carregando...",
            color=discord.Color.light_embed()
        )
        await interact.edit_original_response(embed=load)

        await sleep(1)

        guild = db.session.query(db.Guild_Config).filter_by(guild_id=interact.guild.id).first()

        if guild:
            # Verificar permissão
            if interact.user.get_role(guild.perm_cmd_role_id) or interact.user.id == config_bot.OWNER_ID:
                # Buscar cargos cadastrados
                cargos = db.session.query(db.CargosPremiacao).filter_by(guild_id=interact.guild.id).all()

                embed = Embed(
                    title="🎁 Configurar Cargos de Premiação",
                    description=(
                        "Configure os cargos que podem ser usados como premiação em eventos.\n\n"
                        f"**Cargos cadastrados:** `{len(cargos)}`\n\n"
                        "Use os botões abaixo para gerenciar os cargos:"
                    ),
                    color=discord.Color.gold()
                )

                await interact.edit_original_response(embed=embed, view=ConfigCargoPremiacaoView())

            else:
                failed = Embed(
                    title=f"{emojis.FAILED} | Não possui permissão!",
                    color=discord.Color.red()
                )
                await interact.edit_original_response(embed=failed)
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Servidor não configurado!",
                description="Use `/config` primeiro para configurar o servidor.",
                color=discord.Color.red()
            )
            await interact.edit_original_response(embed=failed)


async def setup(bot):
    await bot.add_cog(ConfigCargoPremiacao(bot))
