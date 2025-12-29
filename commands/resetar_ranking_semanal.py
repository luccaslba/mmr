import discord, config_bot, emojis, db
from discord import app_commands, Embed
from discord.ext.commands import Cog


class ResetarRankingSemanal(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Resetar o ranking semanal de todos os jogadores")
    async def resetar_ranking_semanal(self, interact: discord.Interaction):
        await interact.response.defer(ephemeral=True)

        guild = db.session.query(db.Guild_Config).filter_by(guild_id=interact.guild.id).first()

        if not guild:
            failed = Embed(
                title=f"{emojis.FAILED} | Servidor não configurado!",
                color=discord.Color.red()
            )
            return await interact.edit_original_response(embed=failed)

        # Verificar permissão
        if not interact.user.get_role(guild.perm_cmd_role_id) and interact.user.id != config_bot.OWNER_ID:
            failed = Embed(
                title=f"{emojis.FAILED} | Não possui permissão!",
                color=discord.Color.red()
            )
            return await interact.edit_original_response(embed=failed)

        # Buscar todos os usuários do ranking semanal deste servidor
        users_weekly = db.session.query(db.UsersWeekly).filter_by(guild_id=interact.guild.id).all()

        if not users_weekly:
            info = Embed(
                title=f"{emojis.FAILED} | Nenhum jogador no ranking semanal!",
                description="O ranking semanal está vazio.",
                color=discord.Color.orange()
            )
            return await interact.edit_original_response(embed=info)

        # Contar quantos tinham pontos
        usuarios_resetados = 0
        for user in users_weekly:
            if user.MRR != 0:
                user.MRR = 0
                usuarios_resetados += 1

        db.session.commit()

        success = Embed(
            title=f"{emojis.SUCESS} | Ranking Semanal Resetado!",
            description=(
                f"**{usuarios_resetados}** jogadores tiveram seus pontos semanais zerados.\n\n"
                f"O ranking principal **não foi afetado**."
            ),
            color=discord.Color.green()
        )
        success.set_footer(text=f"Resetado por {interact.user.name}", icon_url=interact.user.display_avatar.url)

        await interact.edit_original_response(embed=success)


async def setup(bot):
    await bot.add_cog(ResetarRankingSemanal(bot))
