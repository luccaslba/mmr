import discord
from discord import app_commands
from discord.ext import commands
from db import session, Guild_Config
import emojis


class ConfigContadores(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="config_contadores", description="Configura os canais de estatísticas de organizadores e jurados")
    @app_commands.describe(
        canal_org_ranqueada="Canal para estatísticas de organizadores em RANQUEADAS",
        canal_org_evento="Canal para estatísticas de organizadores em EVENTOS",
        canal_jurado="Canal para estatísticas de JURADOS (ranqueadas + eventos)"
    )
    async def config_contadores(
        self,
        interact: discord.Interaction,
        canal_org_ranqueada: discord.TextChannel = None,
        canal_org_evento: discord.TextChannel = None,
        canal_jurado: discord.TextChannel = None
    ):
        guild = session.query(Guild_Config).filter_by(guild_id=interact.guild.id).first()

        if not guild:
            failed = discord.Embed(
                title=f"{emojis.FAILED} | Servidor não configurado!",
                description="Use `/config` primeiro para configurar o servidor.",
                color=discord.Color.red()
            )
            return await interact.response.send_message(embed=failed, ephemeral=True)

        # Verificar permissão de administrador
        if not interact.user.guild_permissions.administrator:
            failed = discord.Embed(
                title=f"{emojis.FAILED} | Permissão negada!",
                description="Apenas administradores podem usar este comando.",
                color=discord.Color.red()
            )
            return await interact.response.send_message(embed=failed, ephemeral=True)

        # Atualizar canais
        alteracoes = []

        if canal_org_ranqueada is not None:
            antigo = interact.guild.get_channel(guild.organizador_ranqueada_stats_channel_id) if guild.organizador_ranqueada_stats_channel_id else None
            guild.organizador_ranqueada_stats_channel_id = canal_org_ranqueada.id
            alteracoes.append(f"**Canal Org. Ranqueadas:** {antigo.mention if antigo else 'Nenhum'} → {canal_org_ranqueada.mention}")

        if canal_org_evento is not None:
            antigo = interact.guild.get_channel(guild.organizador_evento_stats_channel_id) if guild.organizador_evento_stats_channel_id else None
            guild.organizador_evento_stats_channel_id = canal_org_evento.id
            alteracoes.append(f"**Canal Org. Eventos:** {antigo.mention if antigo else 'Nenhum'} → {canal_org_evento.mention}")

        if canal_jurado is not None:
            antigo = interact.guild.get_channel(guild.jurado_stats_channel_id) if guild.jurado_stats_channel_id else None
            guild.jurado_stats_channel_id = canal_jurado.id
            alteracoes.append(f"**Canal Jurados:** {antigo.mention if antigo else 'Nenhum'} → {canal_jurado.mention}")

        if not alteracoes:
            # Mostrar configuração atual
            ch_org_ranqueada = interact.guild.get_channel(guild.organizador_ranqueada_stats_channel_id) if guild.organizador_ranqueada_stats_channel_id else None
            ch_org_evento = interact.guild.get_channel(guild.organizador_evento_stats_channel_id) if guild.organizador_evento_stats_channel_id else None
            ch_jurado = interact.guild.get_channel(guild.jurado_stats_channel_id) if guild.jurado_stats_channel_id else None

            embed = discord.Embed(
                title="📊 Configuração de Contadores",
                description=(
                    "**Canais de estatísticas:**\n"
                    "• **Org. Ranqueadas:** Lista de organizadores + quantidade de ranqueadas finalizadas\n"
                    "• **Org. Eventos:** Lista de organizadores + quantidade de eventos finalizados\n"
                    "• **Jurados:** Lista de jurados + quantidade de ranqueadas e eventos\n\n"
                    "**Configuração atual:**"
                ),
                color=discord.Color.blurple()
            )
            embed.add_field(name="🏆 Canal Org. Ranqueadas", value=ch_org_ranqueada.mention if ch_org_ranqueada else "*Não configurado*", inline=True)
            embed.add_field(name="🎮 Canal Org. Eventos", value=ch_org_evento.mention if ch_org_evento else "*Não configurado*", inline=True)
            embed.add_field(name="⚖️ Canal Jurados", value=ch_jurado.mention if ch_jurado else "*Não configurado*", inline=True)

            if not ch_org_ranqueada and not ch_org_evento and not ch_jurado:
                embed.add_field(
                    name="⚠️ Aviso",
                    value="Nenhum canal configurado = **estatísticas não serão exibidas**",
                    inline=False
                )

            return await interact.response.send_message(embed=embed, ephemeral=True)

        session.commit()

        sucess = discord.Embed(
            title=f"{emojis.SUCESS} | Canais de contadores atualizados!",
            description="\n".join(alteracoes),
            color=discord.Color.green()
        )

        # Mostrar resumo
        ch_org_ranqueada = interact.guild.get_channel(guild.organizador_ranqueada_stats_channel_id) if guild.organizador_ranqueada_stats_channel_id else None
        ch_org_evento = interact.guild.get_channel(guild.organizador_evento_stats_channel_id) if guild.organizador_evento_stats_channel_id else None
        ch_jurado = interact.guild.get_channel(guild.jurado_stats_channel_id) if guild.jurado_stats_channel_id else None

        sucess.add_field(name="🏆 Canal Org. Ranqueadas", value=ch_org_ranqueada.mention if ch_org_ranqueada else "*Não configurado*", inline=True)
        sucess.add_field(name="🎮 Canal Org. Eventos", value=ch_org_evento.mention if ch_org_evento else "*Não configurado*", inline=True)
        sucess.add_field(name="⚖️ Canal Jurados", value=ch_jurado.mention if ch_jurado else "*Não configurado*", inline=True)

        await interact.response.send_message(embed=sucess, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ConfigContadores(bot))
