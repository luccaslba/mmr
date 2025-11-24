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


class ClassificacaoSelect(Select):
    def __init__(self, posicao: int, participantes, placeholder: str):
        self.posicao = posicao

        options = [
            discord.SelectOption(
                label=p['user'].name,
                value=str(p['user'].id),
                description=f"MMR: {p['mmr']}"
            )
            for p in participantes
        ]

        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"classificacao_{posicao}"
        )

    async def callback(self, interaction: discord.Interaction):
        # Apenas atualiza a view, não envia nada
        await interaction.response.defer()


class FinalizarTorneioView(View):
    def __init__(self, bot, autor: discord.Member, participantes, formato: str, tipo_evento: str = "aberto"):
        super().__init__(timeout=300)
        self.bot = bot
        self.autor = autor
        self.participantes = participantes
        self.formato = formato
        self.tipo_evento = tipo_evento
        self.classificacao = {}  # {posicao: user_id}

        num_participantes = len(participantes)

        # Adicionar selects baseado no número de participantes
        if num_participantes >= 1:
            self.add_item(ClassificacaoSelect(1, participantes, "🥇 1º Lugar (Campeão)"))
        if num_participantes >= 2:
            self.add_item(ClassificacaoSelect(2, participantes, "🥈 2º Lugar (Vice)"))
        if num_participantes >= 3:
            self.add_item(ClassificacaoSelect(3, participantes, "🥉 3º Lugar"))
        if num_participantes >= 4:
            self.add_item(ClassificacaoSelect(4, participantes, "4️⃣ 4º Lugar"))

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

        # Coletar seleções dos selects
        classificacao_temp = {}
        for child in self.children:
            if isinstance(child, ClassificacaoSelect) and child.values:
                classificacao_temp[child.posicao] = int(child.values[0])

        # Validar se todas as posições foram preenchidas
        num_participantes = len(self.participantes)
        if len(classificacao_temp) < num_participantes:
            failed = Embed(
                title=f"{emojis.FAILED} | Classificação incompleta!",
                description=f"Selecione a posição de todos os {num_participantes} participantes.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=failed, ephemeral=True)

        # Validar se não há duplicatas
        if len(set(classificacao_temp.values())) != len(classificacao_temp):
            failed = Embed(
                title=f"{emojis.FAILED} | Jogadores duplicados!",
                description="Você selecionou o mesmo jogador em posições diferentes.",
                color=discord.Color.red()
            )
            return await interaction.response.send_message(embed=failed, ephemeral=True)

        # Processar finalização direto (sem pedir valor, K é fixo agora)
        await interaction.response.defer(ephemeral=True)

        # Processar finalização
        resultado = await functions.finalizar_torneio(
            session,
            self.autor.id,
            classificacao_temp,
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

            for pos, dados in sorted(resultado['resultados'].items()):
                emoji = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣"}.get(pos, f"{pos}º")
                user = discord.utils.get(interaction.guild.members, id=dados['user_id'])

                delta = dados['delta_mmr']
                sinal = "+" if delta >= 0 else ""

                embed.add_field(
                    name=f"{emoji} {pos}º Lugar",
                    value=f"{user.mention}\n{sinal}{delta} MMR → **{dados['mmr_novo']} MMR**",
                    inline=True
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

            for pos, dados in sorted(resultado['resultados'].items()):
                emoji = {1: "🥇", 2: "🥈", 3: "🥉", 4: "4️⃣"}.get(pos, f"{pos}º")
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
                "Selecione a posição final de cada jogador nos dropdowns abaixo:"
            ),
            color=discord.Color.blurple()
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
