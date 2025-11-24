import discord, emojis, config_bot, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog

class ConfigConstantes(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Configurar constantes K para cálculo de MMR")
    @app_commands.describe(
        k_ranqueada="Constante K para partidas ranqueadas (padrão: 5)",
        k_aberto="Constante K para eventos abertos (padrão: 20)",
        k_fechado="Constante K para eventos fechados (padrão: 40)",
        k_bdf="Constante K para eventos BDF (padrão: 100)"
    )
    async def config_constante(
        self,
        interact: discord.Interaction,
        k_ranqueada: int = 5,
        k_aberto: int = 20,
        k_fechado: int = 40,
        k_bdf: int = 100
    ):
        await interact.response.defer(ephemeral=True)

        load = Embed(
            description=f" {emojis.LOADING} | Carregando... ",
            color=discord.Color.light_embed()
        )
        await interact.edit_original_response(embed=load)

        await sleep(2)

        if interact.user.id == config_bot.OWNER_ID:
            # Buscar ou criar configuração de constantes
            constantes = db.session.query(db.ConstantesK).filter_by(guild_id=interact.guild.id).first()

            if not constantes:
                # Criar nova configuração
                constantes = db.ConstantesK(
                    guild_id=interact.guild.id,
                    k_ranqueada=k_ranqueada,
                    k_aberto=k_aberto,
                    k_fechado=k_fechado,
                    k_bdf=k_bdf
                )
                db.session.add(constantes)
                db.session.commit()

                success = Embed(
                    title=f"{emojis.SUCESS} | Constantes K configuradas com sucesso!",
                    description="As constantes foram salvas e serão usadas nos cálculos de MMR.",
                    color=discord.Color.green()
                )
            else:
                # Atualizar configuração existente
                constantes.k_ranqueada = k_ranqueada
                constantes.k_aberto = k_aberto
                constantes.k_fechado = k_fechado
                constantes.k_bdf = k_bdf
                db.session.commit()

                success = Embed(
                    title=f"{emojis.SUCESS} | Constantes K atualizadas!",
                    description="As novas constantes serão usadas nos próximos cálculos de MMR.",
                    color=discord.Color.green()
                )

            # Adicionar campos mostrando os valores
            success.add_field(name="🎯 Ranqueada", value=f"K = {k_ranqueada}", inline=True)
            success.add_field(name="🌍 Aberto", value=f"K = {k_aberto}", inline=True)
            success.add_field(name="🔒 Fechado", value=f"K = {k_fechado}", inline=True)
            success.add_field(name="⚔️ BDF", value=f"K = {k_bdf}", inline=True)

            success.set_footer(text="💡 Quanto maior o K, maior a variação de MMR por partida")

            await interact.edit_original_response(embed=success)

        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Não possui permissão!",
                description="Apenas o proprietário do bot pode configurar as constantes K.",
                color=discord.Color.red()
            )
            await interact.edit_original_response(embed=failed)

# Necessário para o bot carregar a extensão
async def setup(bot):
    await bot.add_cog(ConfigConstantes(bot))
