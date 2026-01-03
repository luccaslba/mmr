import discord
from discord import app_commands
from discord.ext import commands
from db import session, Guild_Config
import emojis


class ConfigRanqueadaPermissoes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="config_ranqueada_permissoes", description="Configura os cargos de permissão para puxar ranqueadas")
    @app_commands.describe(
        cargo_1x1="Cargo que pode puxar ranqueada 1x1 (apenas 1x1)",
        cargo_2x2="Cargo que pode puxar ranqueada 2x2 (pode 1x1 e 2x2)",
        cargo_3x3="Cargo que pode puxar ranqueada 3x3 (pode 1x1, 2x2 e 3x3)"
    )
    async def config_ranqueada_permissoes(
        self,
        interact: discord.Interaction,
        cargo_1x1: discord.Role = None,
        cargo_2x2: discord.Role = None,
        cargo_3x3: discord.Role = None
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

        # Atualizar cargos
        alteracoes = []

        if cargo_1x1 is not None:
            antigo = interact.guild.get_role(guild.ranqueada_perm_1x1_role_id) if guild.ranqueada_perm_1x1_role_id else None
            guild.ranqueada_perm_1x1_role_id = cargo_1x1.id
            alteracoes.append(f"**Cargo 1x1:** {antigo.mention if antigo else 'Nenhum'} → {cargo_1x1.mention}")

        if cargo_2x2 is not None:
            antigo = interact.guild.get_role(guild.ranqueada_perm_2x2_role_id) if guild.ranqueada_perm_2x2_role_id else None
            guild.ranqueada_perm_2x2_role_id = cargo_2x2.id
            alteracoes.append(f"**Cargo 2x2:** {antigo.mention if antigo else 'Nenhum'} → {cargo_2x2.mention}")

        if cargo_3x3 is not None:
            antigo = interact.guild.get_role(guild.ranqueada_perm_3x3_role_id) if guild.ranqueada_perm_3x3_role_id else None
            guild.ranqueada_perm_3x3_role_id = cargo_3x3.id
            alteracoes.append(f"**Cargo 3x3:** {antigo.mention if antigo else 'Nenhum'} → {cargo_3x3.mention}")

        if not alteracoes:
            # Mostrar configuração atual
            role_1x1 = interact.guild.get_role(guild.ranqueada_perm_1x1_role_id) if guild.ranqueada_perm_1x1_role_id else None
            role_2x2 = interact.guild.get_role(guild.ranqueada_perm_2x2_role_id) if guild.ranqueada_perm_2x2_role_id else None
            role_3x3 = interact.guild.get_role(guild.ranqueada_perm_3x3_role_id) if guild.ranqueada_perm_3x3_role_id else None

            embed = discord.Embed(
                title="⚙️ Permissões de Ranqueada",
                description=(
                    "**Hierarquia de permissões:**\n"
                    "• Cargo 3x3 pode puxar: 1x1, 2x2 e 3x3\n"
                    "• Cargo 2x2 pode puxar: 1x1 e 2x2\n"
                    "• Cargo 1x1 pode puxar: apenas 1x1\n\n"
                    "**Configuração atual:**"
                ),
                color=discord.Color.blurple()
            )
            embed.add_field(name="👤 Cargo 1x1", value=role_1x1.mention if role_1x1 else "*Não configurado*", inline=True)
            embed.add_field(name="👥 Cargo 2x2", value=role_2x2.mention if role_2x2 else "*Não configurado*", inline=True)
            embed.add_field(name="👥 Cargo 3x3", value=role_3x3.mention if role_3x3 else "*Não configurado*", inline=True)

            if not role_1x1 and not role_2x2 and not role_3x3:
                embed.add_field(
                    name="⚠️ Aviso",
                    value="Nenhum cargo configurado = **todos podem puxar qualquer ranqueada**",
                    inline=False
                )

            return await interact.response.send_message(embed=embed, ephemeral=True)

        session.commit()

        sucess = discord.Embed(
            title=f"{emojis.SUCESS} | Permissões atualizadas!",
            description="\n".join(alteracoes),
            color=discord.Color.green()
        )

        # Mostrar resumo
        role_1x1 = interact.guild.get_role(guild.ranqueada_perm_1x1_role_id) if guild.ranqueada_perm_1x1_role_id else None
        role_2x2 = interact.guild.get_role(guild.ranqueada_perm_2x2_role_id) if guild.ranqueada_perm_2x2_role_id else None
        role_3x3 = interact.guild.get_role(guild.ranqueada_perm_3x3_role_id) if guild.ranqueada_perm_3x3_role_id else None

        sucess.add_field(name="👤 Cargo 1x1", value=role_1x1.mention if role_1x1 else "*Não configurado*", inline=True)
        sucess.add_field(name="👥 Cargo 2x2", value=role_2x2.mention if role_2x2 else "*Não configurado*", inline=True)
        sucess.add_field(name="👥 Cargo 3x3", value=role_3x3.mention if role_3x3 else "*Não configurado*", inline=True)

        await interact.response.send_message(embed=sucess, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ConfigRanqueadaPermissoes(bot))
