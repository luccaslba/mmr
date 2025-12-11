import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog

class ConfigRanqueada(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Configurar os canais de partidas ranqueadas")
    @app_commands.describe(
        canal_botao="O canal onde será enviado o botão de ranqueada",
        canal_inscricao="O canal onde as inscrições vão ocorrer",
        canal_confronto="O canal onde os confrontos serão enviados"
    )
    async def config_ranqueada(
        self,
        interact: discord.Interaction,
        canal_botao: discord.TextChannel,
        canal_inscricao: discord.TextChannel,
        canal_confronto: discord.TextChannel
    ):
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
                # Canais antigos
                antigo_botao = interact.guild.get_channel(guild.ranqueada_channel_id) if guild.ranqueada_channel_id else None
                antigo_inscricao = interact.guild.get_channel(guild.ranqueada_inscricao_channel_id) if guild.ranqueada_inscricao_channel_id else None
                antigo_confronto = interact.guild.get_channel(guild.ranqueada_confronto_channel_id) if guild.ranqueada_confronto_channel_id else None

                # Atualizar canais
                guild.ranqueada_channel_id = canal_botao.id
                guild.ranqueada_inscricao_channel_id = canal_inscricao.id
                guild.ranqueada_confronto_channel_id = canal_confronto.id
                db.session.commit()

                sucess = Embed(
                    title=f"{emojis.SUCESS} | Canais de ranqueada configurados!",
                    color=discord.Color.green()
                )

                # Canal do botão
                sucess.add_field(
                    name="Canal do Botão:",
                    value=f"{antigo_botao.mention if antigo_botao else 'Não configurado'} → {canal_botao.mention}",
                    inline=False
                )

                # Canal de inscrições
                sucess.add_field(
                    name="Canal de Inscrições:",
                    value=f"{antigo_inscricao.mention if antigo_inscricao else 'Não configurado'} → {canal_inscricao.mention}",
                    inline=False
                )

                # Canal de confrontos
                sucess.add_field(
                    name="Canal de Confrontos:",
                    value=f"{antigo_confronto.mention if antigo_confronto else 'Não configurado'} → {canal_confronto.mention}",
                    inline=False
                )

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
