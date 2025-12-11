import discord, emojis, functions, config_bot, random
from discord import Embed
from discord.ui import View, Button, Modal, TextInput, Select
from db import session, Users, Guild_Config, MatchParticipantes


class JogadorSelect(Select):
    """Dropdown para selecionar um jogador para uma posição específica"""
    def __init__(self, participantes_disponiveis, posicao, jogador_num, tamanho_time):
        self.posicao = posicao
        self.jogador_num = jogador_num
        self.tamanho_time = tamanho_time

        emojis_posicoes = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣",
                          7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"}
        emoji = emojis_posicoes.get(posicao, f"{posicao}º")

        options = []
        for p in participantes_disponiveis:
            options.append(discord.SelectOption(
                label=p['user'].name[:100],
                value=str(p['user'].id),
                description=f"MMR: {p['mmr']}"
            ))

        if tamanho_time == 1:
            placeholder = f"{emoji} Quem ficou em {posicao}º lugar?"
        else:
            placeholder = f"{emoji} {posicao}º lugar - Jogador {jogador_num}/{tamanho_time}"

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options[:25],
            custom_id=f"jogador_select_{posicao}_{jogador_num}"
        )

    async def callback(self, interaction: discord.Interaction):
        view: ClassificacaoPorPosicaoView = self.view
        user_id = int(self.values[0])

        # Registrar a seleção
        if self.posicao not in view.classificacao:
            view.classificacao[self.posicao] = []
        view.classificacao[self.posicao].append(user_id)

        # Remover jogador da lista de disponíveis
        view.participantes_disponiveis = [p for p in view.participantes_disponiveis if p['user'].id != user_id]

        # Encontrar nome do jogador
        participante = next((p for p in view.participantes if p['user'].id == user_id), None)
        nome = participante['user'].name if participante else "Desconhecido"

        emojis_posicoes = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣",
                          7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"}
        emoji = emojis_posicoes.get(self.posicao, f"{self.posicao}º")

        # Avançar para próxima pergunta
        view.jogador_atual += 1

        # Verificar se terminou todos os jogadores desta posição
        if view.jogador_atual > view.tamanho_time:
            view.posicao_atual += 1
            view.jogador_atual = 1

        # Verificar se terminou todas as posições
        if view.posicao_atual > view.num_vagas:
            # Classificação completa - mostrar resumo e botão de confirmar
            await view.mostrar_resumo(interaction)
        else:
            # Atualizar para próxima pergunta
            await view.atualizar_pergunta(interaction)


class ClassificacaoPorPosicaoView(View):
    """View que pergunta posição por posição"""
    def __init__(self, bot, autor, participantes, formato, tipo_evento):
        super().__init__(timeout=300)
        self.bot = bot
        self.autor = autor
        self.participantes = participantes
        self.participantes_disponiveis = participantes.copy()
        self.formato = formato
        self.tipo_evento = tipo_evento
        self.classificacao = {}  # {posicao: [user_ids]}

        self.tamanho_time = int(formato.split("x")[0])
        self.num_vagas = len(participantes) // self.tamanho_time

        self.posicao_atual = 1
        self.jogador_atual = 1

        self.mensagem = None

        # Adicionar primeiro dropdown
        self._adicionar_dropdown()

    def _adicionar_dropdown(self):
        # Limpar items existentes (exceto botão cancelar)
        self.clear_items()

        if self.participantes_disponiveis:
            dropdown = JogadorSelect(
                self.participantes_disponiveis,
                self.posicao_atual,
                self.jogador_atual,
                self.tamanho_time
            )
            self.add_item(dropdown)

        # Adicionar botão cancelar
        cancelar_btn = Button(label="Cancelar", style=discord.ButtonStyle.red, emoji="❌", row=4)
        cancelar_btn.callback = self.cancelar_callback
        self.add_item(cancelar_btn)

    async def cancelar_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content="❌ Classificação cancelada.",
            embed=None,
            view=None
        )

    def criar_embed_pergunta(self):
        emojis_posicoes = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣",
                          7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"}
        emoji = emojis_posicoes.get(self.posicao_atual, f"{self.posicao_atual}º")

        if self.tamanho_time == 1:
            titulo = f"{emoji} Quem ficou em {self.posicao_atual}º lugar?"
            descricao = f"Selecione o jogador que ficou em **{self.posicao_atual}º lugar**."
        else:
            titulo = f"{emoji} {self.posicao_atual}º Lugar - Jogador {self.jogador_atual}/{self.tamanho_time}"
            descricao = f"Selecione o **jogador {self.jogador_atual}** do time que ficou em **{self.posicao_atual}º lugar**."

        embed = Embed(
            title=titulo,
            description=descricao,
            color=discord.Color.blurple()
        )

        # Mostrar progresso
        total_jogadores = len(self.participantes)
        classificados = sum(len(jogadores) for jogadores in self.classificacao.values())
        embed.add_field(
            name="📊 Progresso",
            value=f"{classificados}/{total_jogadores} jogadores classificados",
            inline=False
        )

        # Mostrar classificação atual
        if self.classificacao:
            classificacao_texto = ""
            for pos in sorted(self.classificacao.keys()):
                pos_emoji = emojis_posicoes.get(pos, f"{pos}º")
                nomes = []
                for uid in self.classificacao[pos]:
                    p = next((x for x in self.participantes if x['user'].id == uid), None)
                    if p:
                        nomes.append(p['user'].name)
                classificacao_texto += f"{pos_emoji} **{pos}º:** {', '.join(nomes)}\n"

            embed.add_field(
                name="✅ Já classificados",
                value=classificacao_texto,
                inline=False
            )

        return embed

    async def atualizar_pergunta(self, interaction: discord.Interaction):
        self._adicionar_dropdown()
        embed = self.criar_embed_pergunta()
        await interaction.response.edit_message(embed=embed, view=self)

    async def mostrar_resumo(self, interaction: discord.Interaction):
        """Mostra resumo final e botão de confirmar"""
        emojis_posicoes = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣",
                          7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"}

        embed = Embed(
            title="📋 Confirmar Classificação",
            description="Verifique se a classificação está correta:",
            color=discord.Color.green()
        )

        classificacao_texto = ""
        for pos in sorted(self.classificacao.keys()):
            pos_emoji = emojis_posicoes.get(pos, f"{pos}º")
            nomes = []
            for uid in self.classificacao[pos]:
                p = next((x for x in self.participantes if x['user'].id == uid), None)
                if p:
                    nomes.append(f"{p['user'].name} ({p['mmr']} MMR)")
            classificacao_texto += f"{pos_emoji} **{pos}º lugar:** {', '.join(nomes)}\n"

        embed.add_field(name="🏆 Classificação Final", value=classificacao_texto, inline=False)

        # Criar view com botões de confirmar/refazer
        view = ConfirmarClassificacaoView(
            self.bot, self.autor, self.participantes,
            self.formato, self.tipo_evento, self.classificacao
        )

        await interaction.response.edit_message(embed=embed, view=view)


class ConfirmarClassificacaoView(View):
    """View final para confirmar ou refazer a classificação"""
    def __init__(self, bot, autor, participantes, formato, tipo_evento, classificacao):
        super().__init__(timeout=300)
        self.bot = bot
        self.autor = autor
        self.participantes = participantes
        self.formato = formato
        self.tipo_evento = tipo_evento
        self.classificacao = classificacao

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.green, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

        # Converter classificacao de {posicao: [user_ids]} para {posicao_sequencial: user_id}
        classificacao_expandida = {}
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
            0,
            interaction.guild.id,
            self.tipo_evento
        )

        if resultado['sucesso']:
            embed = Embed(
                title=f"🏆 Torneio Finalizado - {self.formato}",
                description=f"**Organizador:** {self.autor.mention}\n**K usado:** {resultado.get('k_usado', 'N/A')}\n",
                color=discord.Color.gold()
            )

            emojis_posicoes = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣",
                              7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"}

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

            # Enviar no canal de confrontos
            guild_config = session.query(Guild_Config).filter_by(guild_id=interaction.guild.id).first()
            if guild_config and guild_config.confronto_channel_id:
                confronto_channel = interaction.guild.get_channel(guild_config.confronto_channel_id)
                if confronto_channel:
                    await confronto_channel.send(embed=embed)

            success_msg = Embed(
                title=f"{emojis.SUCESS} | Torneio finalizado com sucesso!",
                description="Os resultados foram enviados no canal de confrontos.",
                color=discord.Color.green()
            )
            await interaction.edit_original_response(embed=success_msg, view=None)

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

    @discord.ui.button(label="Refazer", style=discord.ButtonStyle.gray, emoji="🔄")
    async def refazer(self, interaction: discord.Interaction, button: Button):
        # Reiniciar classificação
        view = ClassificacaoPorPosicaoView(
            self.bot, self.autor, self.participantes,
            self.formato, self.tipo_evento
        )
        embed = view.criar_embed_pergunta()
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="❌ Classificação cancelada.",
            embed=None,
            view=None
        )


class FinalizarMatchmaking(View):
    def __init__(self, bot, autor: discord.Member, jogadores_sorteados_ids=None, formato="1x1", tipo_evento="aberto"):
        super().__init__(timeout=None)
        self.bot = bot
        self.autor = autor
        self.jogadores_sorteados_ids = jogadores_sorteados_ids or []
        self.formato = formato
        self.tipo_evento = tipo_evento

    @discord.ui.button(label="Gerar Confrontos", style=discord.ButtonStyle.blurple, emoji="⚔️", custom_id="gerar_confrontos")
    async def gerar_confrontos(self, interaction: discord.Interaction, btn: Button):
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

        if not self.jogadores_sorteados_ids:
            failed = Embed(
                title=f"{emojis.FAILED} | Erro ao carregar participantes!",
                description="Lista de jogadores sorteados não encontrada.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=failed, ephemeral=True)

        # Buscar dados dos jogadores
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

        if len(participantes) < 2:
            failed = Embed(
                title=f"{emojis.FAILED} | Jogadores insuficientes!",
                description="É necessário pelo menos 2 jogadores para gerar confrontos.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=failed, ephemeral=True)

        # Calcular tamanho do time
        tamanho_time = int(self.formato.split("x")[0])

        # Para 1x1: cada participante é um competidor
        # Para 2x2: cada 2 participantes formam um time
        # Para 3x3: cada 3 participantes formam um time

        if tamanho_time == 1:
            # Modo individual - embaralhar jogadores e formar pares
            jogadores_embaralhados = participantes.copy()
            random.shuffle(jogadores_embaralhados)

            confrontos = []
            for i in range(0, len(jogadores_embaralhados) - 1, 2):
                if i + 1 < len(jogadores_embaralhados):
                    confrontos.append((
                        [jogadores_embaralhados[i]],
                        [jogadores_embaralhados[i + 1]]
                    ))
        else:
            # Modo equipes - primeiro formar times, depois embaralhar e formar confrontos
            # Assumindo que os jogadores já estão agrupados por times na ordem
            num_times = len(participantes) // tamanho_time
            times = []

            for i in range(num_times):
                time = participantes[i * tamanho_time : (i + 1) * tamanho_time]
                times.append(time)

            # Embaralhar times
            random.shuffle(times)

            confrontos = []
            for i in range(0, len(times) - 1, 2):
                if i + 1 < len(times):
                    confrontos.append((times[i], times[i + 1]))

        # Criar embed com os confrontos
        embed = Embed(
            title=f"⚔️ Confrontos Gerados - {self.formato}",
            description=f"**Organizador:** {self.autor.mention}\n**Total de confrontos:** {len(confrontos)}",
            color=discord.Color.orange()
        )

        for idx, (time1, time2) in enumerate(confrontos, 1):
            if tamanho_time == 1:
                jogador1 = time1[0]['user'].mention
                jogador2 = time2[0]['user'].mention
                embed.add_field(
                    name=f"🎮 Confronto {idx}",
                    value=f"{jogador1} **VS** {jogador2}",
                    inline=False
                )
            else:
                jogadores_time1 = ", ".join([j['user'].mention for j in time1])
                jogadores_time2 = ", ".join([j['user'].mention for j in time2])
                embed.add_field(
                    name=f"🎮 Confronto {idx}",
                    value=f"**Time A:** {jogadores_time1}\n**VS**\n**Time B:** {jogadores_time2}",
                    inline=False
                )

        # Verificar se sobrou alguém (número ímpar)
        if tamanho_time == 1 and len(participantes) % 2 == 1:
            sobrou = participantes[-1]['user'].mention
            embed.add_field(
                name="⏳ Aguardando",
                value=f"{sobrou} aguarda o vencedor de um confronto",
                inline=False
            )
        elif tamanho_time > 1 and (len(participantes) // tamanho_time) % 2 == 1:
            time_sobrou = participantes[-(tamanho_time):]
            jogadores_sobrou = ", ".join([j['user'].mention for j in time_sobrou])
            embed.add_field(
                name="⏳ Aguardando",
                value=f"**Time:** {jogadores_sobrou}\nAguarda o vencedor de um confronto",
                inline=False
            )

        embed.set_footer(text="Clique em 'Gerar Confrontos' novamente para embaralhar")

        await interaction.response.send_message(embed=embed)

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

        # Mostrar view de classificação por posição
        view = ClassificacaoPorPosicaoView(
            self.bot, self.autor, participantes,
            self.formato, self.tipo_evento
        )
        embed = view.criar_embed_pergunta()

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
