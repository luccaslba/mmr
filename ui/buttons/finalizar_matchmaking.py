import discord, emojis, functions
from discord import Embed
from discord.ui import View, Button, Modal, TextInput, Select
from db import session, Users, Guild_Config, MatchParticipantes

class FinalizarTorneioModal(Modal, title="Finalizar Torneio"):
    valor_partida = TextInput(
        label="Valor da Partida",
        placeholder="Ex: 15000",
        required=True,
        style=discord.TextStyle.short
    )

    def __init__(self, bot, autor: discord.Member, participantes, formato: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.autor = autor
        self.participantes = participantes  # Lista de dicts com user e mmr
        self.formato = formato

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            valor = int(self.valor_partida.value)
        except:
            failed = Embed(
                title=f"{emojis.FAILED} | O valor precisa ser um número!",
                color=discord.Color.red()
            )
            return await interaction.followup.send(embed=failed, ephemeral=True)

        # Aqui vamos pegar os dados da view que tem os selects
        # Por enquanto, vamos mostrar erro pedindo para usar a view
        failed = Embed(
            title=f"{emojis.FAILED} | Use os dropdowns para selecionar as posições!",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=failed, ephemeral=True)


class BotaoParticipante(Button):
    def __init__(self, user_id: int, user_name: str, mmr: int, row: int):
        super().__init__(
            label=user_name[:80],  # Discord limit
            style=discord.ButtonStyle.blurple,
            custom_id=f"participante_{user_id}",
            row=row
        )
        self.user_id = user_id
        self.user_name = user_name
        self.mmr = mmr

    async def callback(self, interaction: discord.Interaction):
        view: FinalizarTorneioView = self.view

        # Verificar se já foi classificado
        if self.user_id in view.classificacao.values():
            await interaction.response.send_message(
                f"{emojis.FAILED} | {self.user_name} já foi classificado!",
                ephemeral=True
            )
            return

        # Armazenar o participante selecionado
        view.participante_selecionado = self.user_id

        # Mostrar view de seleção de posição
        await interaction.response.send_message(
            f"Selecione a posição para **{self.user_name}**:",
            view=SelecionarPosicaoView(view),
            ephemeral=True
        )


class BotaoPosicao(Button):
    def __init__(self, posicao: int, emoji: str, label: str, row: int):
        super().__init__(
            label=f"{emoji} {label}",
            style=discord.ButtonStyle.gray,
            custom_id=f"posicao_{posicao}",
            row=row
        )
        self.posicao = posicao

    async def callback(self, interaction: discord.Interaction):
        view: SelecionarPosicaoView = self.view
        main_view = view.main_view

        # Verificar se a posição já foi preenchida
        if self.posicao in main_view.classificacao:
            await interaction.response.send_message(
                f"{emojis.FAILED} | Essa posição já foi preenchida!",
                ephemeral=True
            )
            return

        # Registrar a classificação
        user_id = main_view.participante_selecionado
        main_view.classificacao[self.posicao] = user_id

        # Encontrar o nome do participante
        participante = next((p for p in main_view.participantes if p['user'].id == user_id), None)
        nome = participante['user'].name if participante else "Desconhecido"

        emoji_posicao = {
            1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣",
            7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟", 11: "1️⃣1️⃣", 12: "1️⃣2️⃣",
            13: "1️⃣3️⃣", 14: "1️⃣4️⃣", 15: "1️⃣5️⃣", 16: "1️⃣6️⃣"
        }.get(self.posicao, f"{self.posicao}º")

        await interaction.response.send_message(
            f"{emojis.SUCESS} | **{nome}** classificado em **{emoji_posicao} {self.posicao}º lugar**!\n\n"
            f"Classificados: {len(main_view.classificacao)}/{len(main_view.participantes)}",
            ephemeral=True
        )


class SelecionarPosicaoView(View):
    def __init__(self, main_view):
        super().__init__(timeout=60)
        self.main_view = main_view

        emojis_posicoes = {
            1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣",
            7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟", 11: "1️⃣1️⃣", 12: "1️⃣2️⃣",
            13: "1️⃣3️⃣", 14: "1️⃣4️⃣", 15: "1️⃣5️⃣", 16: "1️⃣6️⃣"
        }

        nomes_posicoes = {
            1: "1º", 2: "2º", 3: "3º", 4: "4º", 5: "5º", 6: "6º",
            7: "7º", 8: "8º", 9: "9º", 10: "10º", 11: "11º", 12: "12º",
            13: "13º", 14: "14º", 15: "15º", 16: "16º"
        }

        num_posicoes = len(main_view.participantes)

        # Adicionar botões de posição (max 5 por row, max 5 rows = 25 buttons)
        for i in range(num_posicoes):
            posicao = i + 1
            row = i // 5  # 0-4
            emoji = emojis_posicoes.get(posicao, f"{posicao}º")
            label = nomes_posicoes.get(posicao, f"{posicao}º")

            # Desabilitar se já preenchido
            btn = BotaoPosicao(posicao, emoji, label, row)
            if posicao in main_view.classificacao:
                btn.disabled = True
                btn.style = discord.ButtonStyle.green

            self.add_item(btn)


class FinalizarTorneioView(View):
    def __init__(self, bot, autor: discord.Member, participantes, formato: str, tipo_evento: str = "aberto"):
        super().__init__(timeout=300)
        self.bot = bot
        self.autor = autor
        self.participantes = participantes
        self.formato = formato
        self.tipo_evento = tipo_evento
        self.classificacao = {}  # {posicao: user_id}
        self.participante_selecionado = None  # Para armazenar o participante sendo classificado

        # Adicionar botões dos participantes (max 5 por row)
        for i, participante in enumerate(participantes):
            row = i // 5  # 0-4 (max 5 rows)
            if row >= 4:  # Deixar row 4 para o botão de confirmar
                break

            btn = BotaoParticipante(
                participante['user'].id,
                participante['user'].name,
                participante['mmr'],
                row
            )
            self.add_item(btn)

    @discord.ui.button(label="Confirmar Classificação", style=discord.ButtonStyle.green, emoji="✅", row=4)
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        # Verificar permissão
        guild_config = session.query(Guild_Config).filter_by(guild_id=interaction.guild.id).first()
        if guild_config:
            if interaction.user.id != self.autor.id and not interaction.user.get_role(guild_config.perm_cmd_role_id):
                failed = Embed(
                    title=f"{emojis.FAILED} | Sem permissão!",
                    description=f"Apenas {self.autor.mention} ou membros com permissão podem finalizar.",
                    color=discord.Color.red()
                )
                return await interaction.response.send_message(embed=failed, ephemeral=True)

        # Validar se todas as posições foram preenchidas
        num_participantes = len(self.participantes)
        if len(self.classificacao) < num_participantes:
            failed = Embed(
                title=f"{emojis.FAILED} | Classificação incompleta!",
                description=f"Classifique todos os {num_participantes} participantes antes de confirmar.\n\n"
                           f"**Classificados:** {len(self.classificacao)}/{num_participantes}",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=failed, ephemeral=True)

        # Processar finalização direto (sem pedir valor, K é fixo agora)
        await interaction.response.defer(ephemeral=True)

        # Processar finalização
        resultado = await functions.finalizar_torneio(
            session,
            self.autor.id,
            self.classificacao,
            self.participantes,
            self.formato,
            0,  # valor_partida removido, não é mais usado
            interaction.guild.id,
            self.tipo_evento  # tipo_evento da View
        )

        if resultado['sucesso']:
            # Criar embed de resultado
            embed = Embed(
                title=f"🏆 Torneio Finalizado - {self.formato}",
                description=f"**Organizador:** {self.autor.mention}\n**K usado:** {resultado.get('k_usado', 'N/A')}\n",
                color=discord.Color.gold()
            )

            emojis_posicoes = {
                1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣",
                5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣",
                9: "9️⃣", 10: "🔟", 11: "1️⃣1️⃣", 12: "1️⃣2️⃣",
                13: "1️⃣3️⃣", 14: "1️⃣4️⃣", 15: "1️⃣5️⃣", 16: "1️⃣6️⃣"
            }

            for pos, dados in sorted(resultado['resultados'].items()):
                emoji = emojis_posicoes.get(pos, f"{pos}º")
                user = discord.utils.get(interaction.guild.members, id=dados['user_id'])

                delta = dados['delta_mmr']
                sinal = "+" if delta >= 0 else ""

                embed.add_field(
                    name=f"{emoji} {pos}º Lugar",
                    value=f"{user.mention}\n{sinal}{delta} MMR → **{dados['mmr_novo']} MMR**",
                    inline=True
                )

            embed.set_footer(text=f"Organizado por {self.autor.name}", icon_url=self.autor.display_avatar.url)

            # Enviar no canal de confrontos configurado
            guild_config = session.query(Guild_Config).filter_by(guild_id=interaction.guild.id).first()
            if guild_config and guild_config.confronto_channel_id:
                confronto_channel = interaction.guild.get_channel(guild_config.confronto_channel_id)
                if confronto_channel:
                    await confronto_channel.send(embed=embed)

            # Enviar confirmação ephemeral
            success_msg = Embed(
                title=f"{emojis.SUCESS} | Torneio finalizado com sucesso!",
                description="Os resultados foram enviados no canal de confrontos.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=success_msg, ephemeral=True)

            # Limpar participantes
            participantes_db = session.query(MatchParticipantes).filter_by(autor_id=self.autor.id).all()
            for part in participantes_db:
                session.delete(part)
            session.commit()

        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Erro ao finalizar!",
                description=f"```{resultado['erro']}```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=failed, ephemeral=True)


class FinalizarTorneioValorModal(Modal, title="Valor da Partida"):
    valor = TextInput(
        label="Valor da Partida",
        placeholder="Ex: 15000",
        required=True,
        style=discord.TextStyle.short
    )

    def __init__(self, bot, autor, participantes, formato, classificacao):
        super().__init__(timeout=None)
        self.bot = bot
        self.autor = autor
        self.participantes = participantes
        self.formato = formato
        self.classificacao = classificacao  # {posicao: user_id}

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            valor_partida = int(self.valor.value)
        except:
            failed = Embed(
                title=f"{emojis.FAILED} | Valor inválido!",
                description="O valor precisa ser um número.",
                color=discord.Color.red()
            )
            return await interaction.followup.send(embed=failed, ephemeral=True)

        # Processar finalização
        resultado = await functions.finalizar_torneio(
            session,
            self.autor.id,
            self.classificacao,
            self.participantes,
            self.formato,
            valor_partida,
            interaction.guild.id,
            self.tipo_evento
        )

        if resultado['sucesso']:
            # Criar embed de resultado
            embed = Embed(
                title=f"🏆 Torneio Finalizado - {self.formato}",
                description=f"**Organizador:** {self.autor.mention}\n",
                color=discord.Color.gold()
            )

            emojis_posicoes = {
                1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣",
                5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣",
                9: "9️⃣", 10: "🔟", 11: "1️⃣1️⃣", 12: "1️⃣2️⃣",
                13: "1️⃣3️⃣", 14: "1️⃣4️⃣", 15: "1️⃣5️⃣", 16: "1️⃣6️⃣"
            }

            for pos, dados in sorted(resultado['resultados'].items()):
                emoji = emojis_posicoes.get(pos, f"{pos}º")
                user = discord.utils.get(interaction.guild.members, id=dados['user_id'])

                delta = dados['delta_mmr']
                sinal = "+" if delta >= 0 else ""

                embed.add_field(
                    name=f"{emoji} {pos}º Lugar",
                    value=f"{user.mention}\n{sinal}{delta} MMR → **{dados['mmr_novo']} MMR**",
                    inline=True
                )

            embed.add_field(
                name="💰 Valor Total",
                value=f"{valor_partida * len(self.participantes):,}".replace(',', '.'),
                inline=False
            )

            embed.set_footer(text=f"Organizado por {self.autor.name}", icon_url=self.autor.display_avatar.url)

            await interaction.followup.send(embed=embed)

            # Limpar participantes
            participantes_db = session.query(MatchParticipantes).filter_by(autor_id=self.autor.id).all()
            for part in participantes_db:
                session.delete(part)
            session.commit()

        else:
            failed = Embed(
                title=f"{emojis.FAILED} | Erro ao finalizar!",
                description=f"```{resultado['erro']}```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=failed, ephemeral=True)


class FinalizarMatchmaking(View):
    def __init__(self, bot, autor: discord.Member, jogadores_sorteados_ids=None, formato="1x1", tipo_evento="aberto"):
        super().__init__(timeout=None)
        self.bot = bot
        self.autor = autor
        self.jogadores_sorteados_ids = jogadores_sorteados_ids or []
        self.formato = formato
        self.tipo_evento = tipo_evento

    @discord.ui.button(label="Finalizar Torneio", style=discord.ButtonStyle.green, emoji="🏆", custom_id="finalizar_torneio_v2")
    async def finalizar(self, interaction: discord.Interaction, btn: Button):
        # Verificar permissão
        guild = session.query(Guild_Config).filter_by(guild_id=interaction.guild.id).first()
        if guild:
            perm_role = interaction.guild.get_role(guild.perm_cmd_role_id)
            if interaction.user.id != self.autor.id and not interaction.user.get_role(guild.perm_cmd_role_id):
                failed = Embed(
                    title=f"{emojis.FAILED} | Você não possui permissão!",
                    description=f"**Apenas: {self.autor.mention} ou pessoas com o cargo: {perm_role.mention}, podem usar esse botão**",
                    color=discord.Color.red()
                )
                return await interaction.response.send_message(embed=failed, ephemeral=True)
        else:
            failed = Embed(
                title=f"{emojis.FAILED} | O servidor não está registrado!",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=failed, ephemeral=True)

        # Buscar apenas os participantes que foram SORTEADOS
        if not self.jogadores_sorteados_ids:
            failed = Embed(
                title=f"{emojis.FAILED} | Erro ao carregar participantes!",
                description="Lista de jogadores sorteados não encontrada.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=failed, ephemeral=True)

        # Buscar dados completos apenas dos jogadores sorteados
        participantes = []
        for user_id in self.jogadores_sorteados_ids:
            user_db = session.query(Users).filter_by(discord_id=user_id).first()
            if user_db:
                user = interaction.guild.get_member(user_id)
                if user:
                    participantes.append({
                        'user': user,
                        'mmr': user_db.MRR
                    })

        if not participantes:
            failed = Embed(
                title=f"{emojis.FAILED} | Erro ao carregar participantes!",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=failed, ephemeral=True)

        # Mostrar view de classificação
        view = FinalizarTorneioView(self.bot, self.autor, participantes, self.formato, self.tipo_evento)

        embed = Embed(
            title="📋 Classificar Participantes",
            description=(
                f"**Torneio:** {self.formato}\n"
                f"**Participantes:** {len(participantes)}\n\n"
                "**Como funciona:**\n"
                "1️⃣ Clique no botão do jogador\n"
                "2️⃣ Selecione a posição dele no torneio\n"
                "3️⃣ Repita para todos os participantes\n"
                "4️⃣ Clique em **Confirmar Classificação**"
            ),
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
