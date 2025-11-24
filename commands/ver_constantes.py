import discord, emojis, config_bot, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog

class VerConstantes(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Visualizar constantes K configuradas")
    async def ver_constantes(self, interact: discord.Interaction):
        await interact.response.defer(ephemeral=True)

        load = Embed(
            description=f" {emojis.LOADING} | Carregando... ",
            color=discord.Color.light_embed()
        )
        await interact.edit_original_response(embed=load)

        await sleep(1)

        # Buscar configuração de constantes
        constantes = db.session.query(db.ConstantesK).filter_by(guild_id=interact.guild.id).first()

        if constantes:
            success = Embed(
                title="📊 Constantes K Configuradas",
                description="Valores de K usados no cálculo de MMR por tipo de evento:",
                color=discord.Color.blurple()
            )

            success.add_field(
                name="🎯 Ranqueada",
                value=f"**K = {constantes.k_ranqueada}**\nPartidas ranqueadas competitivas",
                inline=False
            )
            success.add_field(
                name="🌍 Evento Aberto",
                value=f"**K = {constantes.k_aberto}**\nTodos podem participar, sem restrição de MMR",
                inline=False
            )
            success.add_field(
                name="🔒 Evento Fechado",
                value=f"**K = {constantes.k_fechado}**\nApenas jogadores com MMR mínimo configurado",
                inline=False
            )
            success.add_field(
                name="⚔️ Evento BDF",
                value=f"**K = {constantes.k_bdf}**\nVagas garantidas com seleção manual",
                inline=False
            )

            success.set_footer(text="💡 Quanto maior o K, maior a variação de MMR por partida")

            await interact.edit_original_response(embed=success)

        else:
            # Se não existe, mostrar valores padrão
            info = Embed(
                title="📊 Constantes K (Valores Padrão)",
                description="Este servidor ainda não configurou valores personalizados. Usando valores padrão:",
                color=discord.Color.orange()
            )

            info.add_field(name="🎯 Ranqueada", value="**K = 5**", inline=True)
            info.add_field(name="🌍 Aberto", value="**K = 20**", inline=True)
            info.add_field(name="🔒 Fechado", value="**K = 40**", inline=True)
            info.add_field(name="⚔️ BDF", value="**K = 100**", inline=True)

            info.set_footer(text="Use /config_constante para personalizar os valores")

            await interact.edit_original_response(embed=info)

# Necessário para o bot carregar a extensão
async def setup(bot):
    await bot.add_cog(VerConstantes(bot))
