import discord, emojis, functions, config_bot
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


class ClassificacaoSelect(Select):
    def __init__(self, participantes, num_posicoes):
        """
        Dropdown único que permite selecionar participante + posição

        Args:
            participantes: Lista de participantes
            num_posicoes: Número de posições no torneio (baseado em vagas, não em participantes)
        """
        emojis_posicoes = {
            1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣",
            7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟", 11: "1️⃣1️⃣", 12: "1️⃣2️⃣",
            13: "1️⃣3️⃣", 14: "1️⃣4️⃣", 15: "1️⃣5️⃣", 16: "1️⃣6️⃣"
        }

        options = []

        # Criar opções no formato: "🥇 1º - PlayerName"
        for posicao in range(1, num_posicoes + 1):
            emoji = emojis_posicoes.get(posicao, f"{posicao}º")
            for p in participantes:
                label = f"{emoji} {posicao}º - {p['user'].name}"
                value = f"{posicao}:{p['user'].id}"
                options.append(discord.SelectOption(
                    label=label[:100],  # Discord limit
                    value=value,
                    description=f"MMR: {p['mmr']}"
                ))

        super().__init__(
            placeholder="Selecione a posição e o jogador...",
            min_values=1,
            max_values=1,
            options=options[:25],  # Discord limit
            custom_id="classificacao_select"
        )

    async def callback(self, interaction: discord.Interaction):
        view: FinalizarTorneioView = self.view

        # Parsear valor: "posicao:user_id"
        posicao_str, user_id_str = self.values[0].split(":")
        posicao = int(posicao_str)
        user_id = int(user_id_str)

        # Remover jogador de posição anterior se já foi classificado
        for pos, user_ids in list(view.classificacao.items()):
            if user_id in user_ids:
                user_ids.remove(user_id)
                # Remover posição se ficar vazia
                if not user_ids:
                    del view.classificacao[pos]

        # Calcular tamanho do time
        tamanho_time = int(view.formato.split("x")[0])

        # Verificar se a posição já está cheia
        if posicao in view.classificacao:
            jogadores_na_posicao = len(view.classificacao[posicao])
            if jogadores_na_posicao >= tamanho_time:
                await interaction.response.send_message(
                    f"{emojis.FAILED} | Esta posição já está completa ({jogadores_na_posicao}/{tamanho_time} jogadores)!",
                    ephemeral=True
                )
                return

        # Registrar classificação (permite múltiplos na mesma posição apenas para times)
        if posicao not in view.classificacao:
            view.classificacao[posicao] = []

        view.classificacao[posicao].append(user_id)

        # Atualizar o embed original
        await view.atualizar_embed(interaction)

        # Encontrar nome do participante
        participante = next((p for p in view.participantes if p['user'].id == user_id), None)
        nome = participante['user'].name if participante else "Desconhecido"

        emoji_posicao = {
            1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣",
            7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
        }.get(posicao, f"{posicao}º")

        # Contar total de classificados
        total_classificados = sum(len(jogadores) for jogadores in view.classificacao.values())

        await interaction.response.send_message(
            f"{emojis.SUCESS} | **{nome}** classificado em **{emoji_posicao} {posicao}º lugar**!\n\n"
            f"Classificados: {total_classificados}/{len(view.participantes)}",
            ephemeral=True
        )


class FinalizarTorneioView(View):
    def __init__(self, bot, autor: discord.Member, participantes, formato: str, tipo_evento: str = "aberto"):
        super().__init__(timeout=300)
        self.bot = bot
        self.autor = autor
        self.participantes = participantes
        self.formato = formato
        self.tipo_evento = tipo_evento
        self.classificacao = {}  # {posicao: [user_ids]}  - Lista de user_ids por posição
        self.mensagem_original = None  # Para armazenar a mensagem e poder editá-la

        # Calcular número de posições baseado nas vagas do torneio
        # Exemplo: 2x2 com 8 participantes = 4 vagas (4 times) = 4 posições
        # Exemplo: 3x3 com 12 participantes = 4 vagas (4 times) = 4 posições
        num_participantes = len(participantes)

        # Extrair tamanho do time do formato (ex: "2x2" -> 2)
        self.tamanho_time = int(formato.split("x")[0])

        # Calcular número de vagas (times)
        self.num_vagas = num_participantes // self.tamanho_time

        # Adicionar dropdown de classificação
        dropdown = ClassificacaoSelect(participantes, self.num_vagas)
        self.add_item(dropdown)

    def criar_embed_classificacao(self):
        """Cria o embed mostrando a classificação atual"""
        num_participantes = len(self.participantes)

        if self.tamanho_time == 1:
            descricao_formato = f"{num_participantes} jogadores competindo individualmente"
        else:
            descricao_formato = f"{self.num_vagas} times de {self.tamanho_time} jogadores ({num_participantes} pessoas total)"

        embed = Embed(
            title="📋 Classificar Participantes",
            description=(
                f"**Torneio:** {self.formato}\n"
                f"**Formato:** {descricao_formato}\n\n"
                "**Como funciona:**\n"
                f"1️⃣ Selecione no dropdown: **Posição + Jogador**\n"
                f"   • Exemplo: '🥇 1º - PlayerName'\n"
                f"2️⃣ Repita para todos os {num_participantes} participantes\n"
                f"3️⃣ Clique em **Confirmar Classificação**\n\n"
                f"💡 **Posições disponíveis:** 1º ao {self.num_vagas}º lugar"
            ),
            color=discord.Color.blurple()
        )

        # Adicionar classificação atual
        emojis_posicoes = {
            1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣",
            7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟", 11: "1️⃣1️⃣", 12: "1️⃣2️⃣",
            13: "1️⃣3️⃣", 14: "1️⃣4️⃣", 15: "1️⃣5️⃣", 16: "1️⃣6️⃣"
        }

        total_classificados = sum(len(jogadores) for jogadores in self.classificacao.values())

        if self.classificacao:
            classificacao_texto = ""
            for posicao in sorted(self.classificacao.keys()):
                emoji = emojis_posicoes.get(posicao, f"{posicao}º")
                jogadores_nomes = []
                for user_id in self.classificacao[posicao]:
                    participante = next((p for p in self.participantes if p['user'].id == user_id), None)
                    if participante:
                        jogadores_nomes.append(participante['user'].name)

                jogadores_str = ", ".join(jogadores_nomes)
                classificacao_texto += f"{emoji} **{posicao}º lugar:** {jogadores_str}\n"

            embed.add_field(
                name=f"📊 Classificação Atual ({total_classificados}/{num_participantes})",
                value=classificacao_texto,
                inline=False
            )
        else:
            embed.add_field(
                name=f"📊 Classificação Atual (0/{num_participantes})",
                value="*Nenhum jogador classificado ainda*",
                inline=False
            )

        return embed

    async def atualizar_embed(self, interaction: discord.Interaction):
        """Atualiza o embed da mensagem original"""
        if self.mensagem_original:
            try:
                novo_embed = self.criar_embed_classificacao()
                await self.mensagem_original.edit(embed=novo_embed, view=self)
            except:
                pass  # Se falhar ao editar, não faz nada

    @discord.ui.button(label="Confirmar Classificação", style=discord.ButtonStyle.green, emoji="✅", row=4)
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        # Verificar permissão
        guild_config = session.query(Guild_Config).filter_by(guild_id=interaction.guild.id).first()
        if guild_config:
            if interaction.user.id != self.autor.id and interaction.user.id != config_bot.OWNER_ID and not interaction.user.get_role(guild_config.perm_cmd_role_id):
                failed = Embed(
                    title=f"{emojis.FAILED} | Sem permissão!",
                    description=f"Apenas {self.autor.mention} ou membros com permissão podem finalizar.",
                    color=discord.Color.red()
                )
                return await interaction.response.send_message(embed=failed, ephemeral=True)

        # Contar total de jogadores classificados
        total_classificados = sum(len(jogadores) for jogadores in self.classificacao.values())
        num_participantes = len(self.participantes)

        # Validar se todos os participantes foram classificados
        if total_classificados < num_participantes:
            failed = Embed(
                title=f"{emojis.FAILED} | Classificação incompleta!",
                description=f"Classifique todos os {num_participantes} participantes antes de confirmar.\n\n"
                           f"**Classificados:** {total_classificados}/{num_participantes}",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=failed, ephemeral=True)

        # Processar finalização direto (sem pedir valor, K é fixo agora)
        await interaction.response.defer(ephemeral=True)

        # Converter classificacao de {posicao: [user_ids]} para {posicao_sequencial: user_id}
        # Exemplo: {1: [uid1, uid2], 2: [uid3, uid4]} vira {1: uid1, 1: uid2, 2: uid3, 2: uid4}
        # Todos da mesma posição original recebem a mesma posição
        classificacao_expandida = {}
        posicao_map = {}  # {user_id: posicao_original}

        for posicao, user_ids in sorted(self.classificacao.items()):
            for user_id in user_ids:
                posicao_map[user_id] = posicao

        # Criar dict no formato esperado: {posicao_final: user_id}
        # Mantendo a posição do time para todos os membros
        posicao_atual = 1
        for posicao_time in sorted(self.classificacao.keys()):
            for user_id in self.classificacao[posicao_time]:
                classificacao_expandida[posicao_atual] = user_id
                posicao_atual += 1

        # Processar finalização
        resultado = await functions.finalizar_torneio(
            session,
            self.autor.id,
            classificacao_expandida,
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
            if interaction.user.id != self.autor.id and interaction.user.id != config_bot.OWNER_ID and not interaction.user.get_role(guild.perm_cmd_role_id):
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

        # Criar embed inicial
        embed = view.criar_embed_classificacao()

        # Enviar mensagem e armazenar referência
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.mensagem_original = await interaction.original_response()
