import discord, emojis, asyncio, pytz, functions, config_bot
from datetime import datetime, timezone, time
from discord import Embed
from discord.ui import View, Button, Modal, TextInput
from db import session, Users, Guild_Config, CloseMatchMember, MatchParticipantes

class FinalizarConfig(Modal, title="Finalizar Matchmaking"):
    valor_da_batalha = TextInput(label="Valor padrão da batalha:", placeholder="Ex: 12132", required=True)
    def __init__(self, bot, autor: discord.Member):
        super().__init__(timeout=None)
        self.bot = bot
        self.autor = autor

    async def on_submit(self, interact: discord.Interaction):
        bll_value = 0
        try:
            bll_value = int(self.valor_da_batalha.value)
        except:
            failed = Embed(
                title=f"{emojis.FAILED} | O valor da batalha precisa ser numeros!",
                color=discord.Color.red()
            )
            return await interact.response.send_message(embed=failed, ephemeral=True)
        
        sucess = Embed(
            title=f"{emojis.SUCESS} | Selecione um participante para adicionar na lista",
            description="Ele será adicionado a lista, e depois basta você continuar adicionando",
            color=discord.Color.green()
        )
        users = session.query(MatchParticipantes).filter_by(autor_id=self.autor.id).all()
        print(self.autor.id)
        my_view = Finalizar(self.bot, self.autor, bll_value)
        if not users:
            failed = Embed(
                title=f"{emojis.FAILED} | Nem um usuario registrado!",
                color=discord.Color.red()
            )
            return await interact.response.send_message(embed=failed, ephemeral=True)
        
        my_view.add_item(ClassificacaoSelect(self.bot, self.autor, users))
        await interact.response.send_message(embed=sucess, view=my_view, ephemeral=True)

class AdicionarParticcipante(Modal, title="Adicionar Participante"):
    player_pos = TextInput(label="Posição do player:", placeholder="Numero daa colocação, Ex: 1(primeiro lugar), assim por diante", required=True)
    equipe_id = TextInput(label="Id da equipe(se não tiver coloque: 0):", placeholder="Ex: 1", required=True)

    def __init__(self, bot, autor: discord.Member, player_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.autor = autor
        self.player_id = player_id

    async def on_submit(self, interact: discord.Interaction):
        guild = session.query(Guild_Config).filter_by(guild_id=interact.guild.id).first()
        player_id = self.player_id
        player_pos = 0
        equipe_id = 0
        try:
            player_pos = int(self.player_pos.value)
            equipe_id = int(self.equipe_id.value)
        except:
            failed = Embed(
                title=f"{emojis.FAILED} | Alguns formatos está errado!",
                color=discord.Color.red()
            )
            return await interact.response.send_message(embed=failed, ephemeral=True)
        
        member = session.query(Users).filter_by(discord_id=player_id).first()
        db_member_match_close = session.query(CloseMatchMember).filter_by(discord_id=player_id).first()
        if guild and member and not db_member_match_close:
            if interact.user.id == self.autor.id or interact.user.get_role(guild.perm_cmd_role_id):
                add_member = CloseMatchMember(member.discord_id, member.discord_name, self.autor.id, player_pos, equipe_id)
                session.add(add_member)
                session.commit()
                sucess = Embed(
                    title=f"{emojis.SUCESS} | Usuario adicionado na lista!",
                    color=discord.Color.green()
                )
                await interact.response.send_message(embed=sucess, ephemeral=True)
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Error",
                description="**pode ser um desses erros:**",
                color=discord.Color.red()
            )
            failed.add_field(name="Erro 1:", value="Pode ser porque o servidor não está configurado.")
            failed.add_field(name="Erro 2:", value="Pode ser porque o membro não está registrado.")
            failed.add_field(name="Erro 3:", value="Pode ser porque o membro já está na finalização.")
            await interact.response.send_message(embed=failed, ephemeral=True)

class ClassificacaoSelect(discord.ui.Select):
    def __init__(self, bot, autor: discord.Member, users):
        self.bot = bot
        self.autor = autor

        options = [
            discord.SelectOption(label=user.discord_name, value=str(user.discord_id))
            for user in users
        ]
        super().__init__(
            placeholder="Selecione um jogador para continuar:",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AdicionarParticcipante(self.bot, self.autor, self.values[0]))
        

class FinalizarMatchmaking(View):
    def __init__(self, bot, autor: discord.Member):
        super().__init__(timeout=None)
        self.bot = bot
        self.autor = autor

    @discord.ui.button(label="Finalizar Matchmaking", style=discord.ButtonStyle.red, emoji=emojis.FAILED, custom_id="finalizar_matchmaking")
    async def finalizar(self, interaction: discord.Interaction, btn: Button):
        guild = session.query(Guild_Config).filter_by(guild_id=interaction.guild.id).first()
        if guild:
            perm_role = interaction.guild.get_role(guild.perm_cmd_role_id)
            if interaction.user.id == self.autor.id or interaction.user.get_role(guild.perm_cmd_role_id):
                await interaction.response.send_modal(FinalizarConfig(self.bot, self.autor))
            else:
                failed = Embed(
                    title=f"{emojis.FAILED} | Você não possui permissão!",
                    description=f"**Apenas: {self.autor.mention} ou pessoas com o cargo: {perm_role.mention}, podem usar esse botão**",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=failed, ephemeral=True)
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | O servidor não está registrado!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=failed, ephemeral=True)

class Finalizar(View):
    def __init__(self, bot, autor: discord.Member, bll_value):
        super().__init__(timeout=None)
        self.bot = bot
        self.autor = autor
        self.bll_value = bll_value

    @discord.ui.button(label="Finalizar Partida", style=discord.ButtonStyle.green, emoji=emojis.SUCESS, custom_id="finalizar_partida")
    async def finalizar_partida(self, interaction: discord.Interaction, btn: Button):
        process = functions.processar_matchmaking(session, self.autor.id, self.bll_value)
        if process:
            sucess = Embed(
                title=f"{emojis.SUCESS} | Partida finalizada e valores entregues!",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=sucess, ephemeral=True)
            participantes = session.query(MatchParticipantes).filter_by(autor_id=self.autor.id).all()
            for part in participantes:
                session.delete(part)
                session.commit()
        else:
            Erro = Embed(
                title=f"{emojis.FAILED} | Error: **{process}**",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=Erro, ephemeral=True)

    @discord.ui.button(label="Finalizar Batalha", style=discord.ButtonStyle.red, emoji=emojis.FAILED, custom_id="finalizar_batalha")
    async def finalizar_batalha(self, interaction: discord.Interaction, btn: Button):
        guild = session.query(Guild_Config).filter_by(guild_id=interaction.guild.id).first()
        if not guild:
            failed = Embed(
                title=f"{emojis.FAILED} | O servidor não está registrado!",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=failed, ephemeral=True)
        
        process = await functions.finalizar_batalha(interaction, session, self.autor.id, self.bll_value, guild.confronto_channel_id)
        if process[0] == True:
            channel = interaction.guild.get_channel(guild.confronto_channel_id)
            sucess = Embed(
                title=f"{emojis.SUCESS} | Detalhes do confronto, enviado em: {channel.mention}",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=sucess, ephemeral=True)
        else:
            Erro = Embed(
                title=f"{emojis.FAILED} | Error: **{process[0]}**",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=Erro, ephemeral=True)


