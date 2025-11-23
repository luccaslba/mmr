import discord, emojis, asyncio, pytz, functions
from datetime import datetime, timezone, time
from discord import Embed
from discord.ui import View, Button, Modal, TextInput
from db import session, Users, Guild_Config

class MatchmakingModal(Modal, title="Configurar Matchmaking"):
    formato = TextInput(label="Formato (ex: 1x1, 2x2, 3x3)", placeholder="2x2", required=True)
    vagas = TextInput(label="Quantidade de vagas (ex: 4, 8, 16)", placeholder="8", required=True)
    tipo_evento = TextInput(label="Tipo de evento (Aberto, Fechado, BDF)", placeholder="Aberto/a ; Fechado/f ; BDF/b", required=True)
    data = TextInput(label="Data do evento (dd/mm/aaaa)", placeholder="31/12/2025", required=True)
    horario = TextInput(label="Horário do evento (HH:MM)", placeholder=f"18:30", required=True)

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        config = session.query(Guild_Config).filter_by(guild_id=interaction.guild.id).first()
        if not config:
            return await interaction.followup.send("Servidor não configurado.", ephemeral=True)
       
        evento_failure = Embed(
            title=f"{emojis.FAILED} | O formato do evento precisa ser: a ou Aberto ; f ou Fechado ; b ou BDF",
            color=discord.Color.red()
        )

        tipo = self.tipo_evento.value.strip().lower()
        if tipo not in ["a", "aberto", "f", "fechado", "b", "bdf"]:
            print(self.tipo_evento)
            await interaction.followup.send(embed=evento_failure, ephemeral=True)
            return


        try:
            vagas = int(str(self.vagas).strip())
            formato_str = str(self.formato).strip().lower()
            jogadores_por_time = int(formato_str.split("x")[0])
            print(jogadores_por_time)
        except:
            return await interaction.response.send_message("Erro no formato ou nas vagas.", ephemeral=True)

        try:
            datahora_naive = datetime.strptime(f"{self.data} {self.horario}", "%d/%m/%Y %H:%M")
            timezone_sp = pytz.timezone("America/Sao_Paulo")
            datahora = timezone_sp.localize(datahora_naive)
        except:
            failure = Embed(
                title=f"{emojis.FAILED} | o formato da data ou hora está errado!",
                color=discord.Color.red()
            )
            failure.add_field(name="Formato Data:", value="Dia/Mês/Ano")
            failure.add_field(name="Formato Hora:", value="Hora:Minutos", inline=False)
            await interaction.followup.send(embed=failure, ephemeral=True)
            return

        if vagas not in [4, 8, 16]:
            failure = Embed(
                title=f"{emojis.FAILED} | Quantidade de vagas está errada, só podera ser entre 4, 8 ou 16",
                color=discord.Color.red()
            )
            return await interaction.followup.send(embed=failure, ephemeral=True)

        # Corrija isso na função aguardar_e_iniciar_matchmaking:
        agora = datetime.now(pytz.timezone("America/Sao_Paulo"))
        tempo_restante = (datahora - agora).total_seconds()

        embed = Embed(
            title="🎯 Matchmaking Aberto!",
            description=(
                f"**Evento:** `{self.tipo_evento}`\n"
                f"**Formato:** `{formato_str}`\n"
                f"**Vagas:** `{vagas}`\n"
                f"**Data:** `{self.data}` \u00e0s `{self.horario}`\n\n"
                f"Reaja com ✅ para participar!"
            ),
            color=discord.Color.green()
        )

        channel = interaction.guild.get_channel(config.matchmaking_channel_id)
        if not channel:
            return await interaction.response.send_message("Canal de matchmaking não encontrado.", ephemeral=True)

        message = await channel.send(embed=embed)
        await message.add_reaction("✅")

        asyncio.create_task(functions.aguardar_e_iniciar_matchmaking(
            self.bot,
            interaction.guild.id,
            channel.id,
            message.id,
            formato_str,
            vagas,
            tipo,
            datahora,
            interaction.user
        ))

        await interaction.followup.send(f"✅ Evento de matchmaking criado com **{vagas} vagas**!", ephemeral=True)


class StartMatchMaking(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Iniciar Matchmaking", style=discord.ButtonStyle.green, emoji=emojis.SUCESS, custom_id="start_matchmaking")
    async def start(self, interaction: discord.Interaction, btn: Button):
        await interaction.response.send_modal(MatchmakingModal(self.bot))

