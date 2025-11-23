import discord, config_bot, emojis, db
from asyncio import sleep
from discord import app_commands, Embed
from discord.ext.commands import Cog

class Gerenciarelo(Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Gerenciar os mmr dos players")
    @app_commands.choices(action=[
        app_commands.Choice(name="somar", value="+"),
        app_commands.Choice(name="subtrair", value="-"),
        app_commands.Choice(name="multiplicar", value="*"),
        app_commands.Choice(name="dividir", value="/")
    ])
    @app_commands.describe(user="O usuario que deseja mudar os mmr", action="A acão que deseja: soma, subtrair, multiplicar ou dividir", value="O valor")
    async def gerenciarelo(self, interact: discord.Interaction, user: discord.Member, action: app_commands.Choice[str], value: int):
        await interact.response.defer(ephemeral=True)
        load = Embed(
            description=f" {emojis.LOADING} | Carregando... ",
            color=discord.Color.light_embed()
        )

        await interact.edit_original_response(embed=load)
        guild = db.session.query(db.Guild_Config).filter_by(guild_id=interact.guild.id).first()

        await sleep(2)

        if guild:
            print("guild")
            if interact.user.get_role(guild.perm_cmd_role_id):
                print("Verifique")
                user_db = db.session.query(db.Users).filter_by(discord_id=user.id).first()
                if not user_db:
                    failed = Embed(
                    title=f"{emojis.FAILED} | O usuario precisa está registrado!",
                    description="Para registrar-se use: **/register!**",
                    color=discord.Color.red()
                    )
                    return await interact.edit_original_response(embed=failed)

                mmr_antigo = user_db.MRR
                soma = 0
                if action.value == "+":
                    soma = user_db.MRR + value
                elif action.value == "-":
                    soma = user_db.MRR - value
                elif action.value == "*":
                    soma = user_db.MRR * value
                elif action.value == "/":
                    soma = user_db.MRR / value
                
                user_db.MRR = soma
                db.session.add(user_db)
                db.session.commit()

                sucess = Embed(
                    title=f"Valor alterado com sucesso!",
                    description="**Informações:**",
                    color=discord.Color.green()
                )
                sucess.add_field(name="Usuario modificaodo:", value=user.mention, inline=False)
                sucess.add_field(name="Ação:", value=action.name, inline=False)
                sucess.add_field(name="MMR antigo:", value=mmr_antigo, inline=False)
                sucess.add_field(name="Valor Adicionado:", value=f"{action.value}{value}", inline=False)
                sucess.add_field(name="Valor atual:", value=user_db.MRR, inline=False)
                await interact.edit_original_response(embed=sucess)
                return
            else:
                failed = Embed(
                title=f"{emojis.FAILED} | Sem permissão para usar esse comando!",
                color=discord.Color.red()
                )
                return await interact.edit_original_response(embed=failed)
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | O servidor precisa está registrado para essa ação!",
                color=discord.Color.red()
            )
            return await interact.edit_original_response(embed=failed)

# Necessário para o bot carregar a extensão
async def setup(bot):
    await bot.add_cog(Gerenciarelo(bot))
