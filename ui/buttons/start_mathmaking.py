import discord, emojis, asyncio, pytz, functions
from datetime import datetime, timezone, time
from discord import Embed
from discord.ui import View, Button, Modal, TextInput, Select
from db import session, Users, Guild_Config

# Modal simplificado - apenas Data e Horário
class DataHorarioModal(Modal, title="Data e Horário do Evento"):
    data = TextInput(
        label="Data do evento (dd/mm/aaaa)",
        placeholder="31/12/2025",
        required=True,
        style=discord.TextStyle.short
    )
    horario = TextInput(
        label="Horário do evento (HH:MM)",
        placeholder="18:30",
        required=True,
        style=discord.TextStyle.short
    )

    def __init__(self, bot, formato: str, vagas: int, tipo_evento: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.formato = formato
        self.vagas = vagas
        self.tipo_evento = tipo_evento

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        config = session.query(Guild_Config).filter_by(guild_id=interaction.guild.id).first()
        if not config:
            return await interaction.followup.send("Servidor não configurado.", ephemeral=True)

        try:
            datahora_naive = datetime.strptime(f"{self.data.value} {self.horario.value}", "%d/%m/%Y %H:%M")
            timezone_sp = pytz.timezone("America/Sao_Paulo")
            datahora = timezone_sp.localize(datahora_naive)
        except:
            failure = Embed(
                title=f"{emojis.FAILED} | Formato da data ou hora está errado!",
                color=discord.Color.red()
            )
            failure.add_field(name="Formato Data:", value="dd/mm/aaaa (ex: 31/12/2025)")
            failure.add_field(name="Formato Hora:", value="HH:MM (ex: 18:30)", inline=False)
            await interaction.followup.send(embed=failure, ephemeral=True)
            return

        agora = datetime.now(pytz.timezone("America/Sao_Paulo"))
        tempo_restante = (datahora - agora).total_seconds()

        if tempo_restante < 0:
            failure = Embed(
                title=f"{emojis.FAILED} | A data/hora deve ser no futuro!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=failure, ephemeral=True)
            return

        # Mapear tipo_evento para nome legível
        tipo_nome = {
            "aberto": "Aberto",
            "fechado": "Fechado",
            "bdf": "BDF"
        }.get(self.tipo_evento, self.tipo_evento)

        embed = Embed(
            title="🎯 Matchmaking Aberto!",
            description=(
                f"**Evento:** `{tipo_nome}`\n"
                f"**Formato:** `{self.formato}`\n"
                f"**Vagas:** `{self.vagas}`\n"
                f"**Data:** `{self.data.value}` às `{self.horario.value}`\n\n"
                f"Reaja com ✅ para participar!"
            ),
            color=discord.Color.green()
        )

        channel = interaction.guild.get_channel(config.matchmaking_channel_id)
        if not channel:
            return await interaction.followup.send("Canal de matchmaking não encontrado.", ephemeral=True)

        message = await channel.send(embed=embed)
        await message.add_reaction("✅")

        asyncio.create_task(functions.aguardar_e_iniciar_matchmaking(
            self.bot,
            interaction.guild.id,
            channel.id,
            message.id,
            self.formato,
            self.vagas,
            self.tipo_evento,
            datahora,
            interaction.user
        ))

        await interaction.followup.send(f"✅ Evento de matchmaking criado com **{self.vagas} vagas**!", ephemeral=True)


# Select Menu para Formato
class FormatoSelect(Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            discord.SelectOption(label="1x1", value="1x1", emoji="👤", description="2 jogadores (1 vs 1)"),
            discord.SelectOption(label="2x2", value="2x2", emoji="👥", description="4 jogadores (2 vs 2)"),
            discord.SelectOption(label="3x3", value="3x3", emoji="👥", description="6 jogadores (3 vs 3)"),
            discord.SelectOption(label="4x4", value="4x4", emoji="👥", description="8 jogadores (4 vs 4)"),
            discord.SelectOption(label="5x5", value="5x5", emoji="👥", description="10 jogadores (5 vs 5)"),
        ]
        super().__init__(
            placeholder="📋 Selecione o formato da partida",
            options=options,
            custom_id="formato_select"
        )

    async def callback(self, interaction: discord.Interaction):
        # Atualizar view com próximo select
        view = VagasView(self.bot, self.values[0])

        embed = Embed(
            title="⚙️ Configurar Matchmaking - Passo 2/4",
            description=f"✅ **Formato selecionado:** `{self.values[0]}`\n\nAgora selecione a quantidade de vagas:",
            color=discord.Color.blurple()
        )

        await interaction.response.edit_message(embed=embed, view=view)


# Select Menu para Vagas
class VagasSelect(Select):
    def __init__(self, bot, formato: str):
        self.bot = bot
        self.formato = formato
        options = [
            discord.SelectOption(label="4 vagas", value="4", emoji="4️⃣", description="Partidas pequenas"),
            discord.SelectOption(label="8 vagas", value="8", emoji="8️⃣", description="Partidas médias"),
            discord.SelectOption(label="16 vagas", value="16", emoji="🔢", description="Partidas grandes"),
        ]
        super().__init__(
            placeholder="📊 Selecione a quantidade de vagas",
            options=options,
            custom_id="vagas_select"
        )

    async def callback(self, interaction: discord.Interaction):
        vagas = int(self.values[0])
        view = TipoEventoView(self.bot, self.formato, vagas)

        embed = Embed(
            title="⚙️ Configurar Matchmaking - Passo 3/4",
            description=(
                f"✅ **Formato:** `{self.formato}`\n"
                f"✅ **Vagas:** `{vagas}`\n\n"
                f"Agora selecione o tipo de evento:"
            ),
            color=discord.Color.blurple()
        )

        await interaction.response.edit_message(embed=embed, view=view)


# Select Menu para Tipo de Evento
class TipoEventoSelect(Select):
    def __init__(self, bot, formato: str, vagas: int):
        self.bot = bot
        self.formato = formato
        self.vagas = vagas

        config = session.query(Guild_Config).first()
        mmr_minimo = config.match_close_count if config else 100

        options = [
            discord.SelectOption(
                label="Aberto",
                value="aberto",
                emoji="🌍",
                description="Todos podem participar, sem restrição de MMR"
            ),
            discord.SelectOption(
                label="Fechado",
                value="fechado",
                emoji="🔒",
                description=f"Apenas jogadores com MMR ≥ {mmr_minimo}"
            ),
            discord.SelectOption(
                label="BDF",
                value="bdf",
                emoji="⚔️",
                description="Batalha de Free (modo especial)"
            ),
        ]
        super().__init__(
            placeholder="🎮 Selecione o tipo de evento",
            options=options,
            custom_id="tipo_evento_select"
        )

    async def callback(self, interaction: discord.Interaction):
        tipo_evento = self.values[0]

        # Abrir modal para data/horário
        await interaction.response.send_modal(
            DataHorarioModal(self.bot, self.formato, self.vagas, tipo_evento)
        )


# Views
class FormatoView(View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot
        self.add_item(FormatoSelect(bot))

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red, emoji="❌", row=1)
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="❌ Configuração cancelada.",
            embed=None,
            view=None
        )


class VagasView(View):
    def __init__(self, bot, formato: str):
        super().__init__(timeout=180)
        self.bot = bot
        self.formato = formato
        self.add_item(VagasSelect(bot, formato))

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.gray, emoji="⬅️", row=1)
    async def voltar(self, interaction: discord.Interaction, button: Button):
        view = FormatoView(self.bot)
        embed = Embed(
            title="⚙️ Configurar Matchmaking - Passo 1/4",
            description="Selecione o formato da partida:",
            color=discord.Color.blurple()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red, emoji="❌", row=1)
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="❌ Configuração cancelada.",
            embed=None,
            view=None
        )


class TipoEventoView(View):
    def __init__(self, bot, formato: str, vagas: int):
        super().__init__(timeout=180)
        self.bot = bot
        self.formato = formato
        self.vagas = vagas
        self.add_item(TipoEventoSelect(bot, formato, vagas))

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.gray, emoji="⬅️", row=1)
    async def voltar(self, interaction: discord.Interaction, button: Button):
        view = VagasView(self.bot, self.formato)
        embed = Embed(
            title="⚙️ Configurar Matchmaking - Passo 2/4",
            description=f"✅ **Formato:** `{self.formato}`\n\nSelecione a quantidade de vagas:",
            color=discord.Color.blurple()
        )
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red, emoji="❌", row=1)
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="❌ Configuração cancelada.",
            embed=None,
            view=None
        )


# Botão principal (mantém compatibilidade)
class StartMatchMakingV2(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Iniciar Matchmaking", style=discord.ButtonStyle.green, emoji=emojis.SUCESS, custom_id="start_matchmaking_v2")
    async def start(self, interaction: discord.Interaction, btn: Button):
        embed = Embed(
            title="⚙️ Configurar Matchmaking - Passo 1/4",
            description="Selecione o formato da partida:",
            color=discord.Color.blurple()
        )
        view = FormatoView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
