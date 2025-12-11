import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog
from ui.buttons.start_ranqueada import StartRanqueadaView

class SendRanqueada(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Envia o botão de partida ranqueada")
    async def send_ranqueada(self, interact: discord.Interaction):

        load = Embed(
            description=f" {emojis.LOADING} | Carregando... ",
            color=discord.Color.light_embed()
        )
        await interact.response.send_message(embed=load, ephemeral=True)

        await sleep(2)

        guild = db.session.query(db.Guild_Config).filter_by(guild_id=interact.guild.id).first()
        if guild:
            if interact.user.get_role(guild.perm_cmd_role_id) or interact.user.id == config_bot.OWNER_ID:

                if not guild.ranqueada_channel_id:
                    failed = Embed(
                        title=f"{emojis.FAILED} | Canal de ranqueada não configurado!",
                        description="Use `/config_ranqueada` para configurar o canal.",
                        color=discord.Color.red()
                    )
                    return await interact.edit_original_response(embed=failed)

                ranqueada_channel = interact.guild.get_channel(guild.ranqueada_channel_id)

                if not ranqueada_channel:
                    failed = Embed(
                        title=f"{emojis.FAILED} | Canal de ranqueada não encontrado!",
                        description="O canal configurado não existe mais. Use `/config_ranqueada` para reconfigurar.",
                        color=discord.Color.red()
                    )
                    return await interact.edit_original_response(embed=failed)

                send = Embed(
                    title=f"Enviado no canal: {ranqueada_channel.mention}",
                    color=discord.Color.light_embed()
                )

                ranqueada_embed = Embed(
                    title="🏆 Partida Ranqueada",
                    description=(
                        "Clique no botão abaixo para iniciar uma partida ranqueada!\n\n"
                        "**Regras:**\n"
                        "• Escolha o formato: **1x1** ou **2x2**\n"
                        "• Mínimo de **4 jogadores** para sortear\n"
                        "• Se houver **8 ou mais** inscritos, sorteia 8\n"
                        "• Se houver entre **4 e 7** inscritos, sorteia 4\n"
                        "• Tipo de evento: **Ranqueada** (K=5)"
                    ),
                    color=discord.Color.gold()
                )

                await interact.edit_original_response(embed=send)
                await ranqueada_channel.send(embed=ranqueada_embed, view=StartRanqueadaView(self.bot))

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

async def setup(bot):
    await bot.add_cog(SendRanqueada(bot))
