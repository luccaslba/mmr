import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog
from ui.buttons.add_role import AddRoleView

class UpdateRole(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Atualizar seu cargos de acordo com seu MMR")
    async def updaterole(self, interact: discord.Interaction):
        await interact.response.defer(ephemeral=True)
        load = Embed(
            description=f" {emojis.LOADING} | Carregando... ",
            color=discord.Color.light_embed()
        )
        await interact.edit_original_response(embed=load)

        await sleep(2)

        guild = db.session.query(db.Guild_Config).filter_by(guild_id=interact.guild.id).first()
        if guild:
            user = db.session.query(db.Users).filter_by(discord_id=interact.user.id).first()
            if user:
                roles = db.session.query(db.RolesMMR).filter_by(MRR=user.MRR).all()
                if roles:
                    sucess = Embed(
                        title=f"{emojis.SUCESS} | Caegos adicionados com sucesso!",
                        description="Cargos adicionados:",
                        color=discord.Color.red()
                    )

                    for role in interact.user.roles:
                        r = db.session.query(db.RolesMMR).filter_by(role_id=role.id).all()
                        if r:
                            await interact.user.remove_roles(role)


                    for role in roles:
                        add_role = interact.guild.get_role(role.role_id)
                        await interact.user.add_roles(add_role)
                        sucess.add_field(name=role.role_name, value=f"MMR Necessario: {role.MRR}")
                    
                    await interact.edit_original_response(embed=sucess)

                else:
                    failed = Embed(
                        title=f"{emojis.FAILED} | Nenhum cargo para a sua quantidade de MMR!",
                        color=discord.Color.red()
                    )
                    await interact.edit_original_response(embed=failed)
            else:
                failed = Embed(
                    title=f"{emojis.FAILED} | O usuario não está registrado!",
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
    await bot.add_cog(UpdateRole(bot))
