import discord, emojis, asyncio, random, config_bot
from discord import Embed
from discord.ui import View, Button, Select
from db import session, Users, Guild_Config
from ui.buttons.finalizar_matchmaking import FinalizarMatchmaking

class StartRanqueadaView(View):
    """View inicial com botões para escolher formato 1x1 ou 2x2"""
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="1x1", style=discord.ButtonStyle.blurple, emoji="👤", custom_id="ranqueada_1x1")
    async def btn_1x1(self, interaction: discord.Interaction, button: Button):
        await self.iniciar_ranqueada(interaction, "1x1")

    @discord.ui.button(label="2x2", style=discord.ButtonStyle.blurple, emoji="👥", custom_id="ranqueada_2x2")
    async def btn_2x2(self, interaction: discord.Interaction, button: Button):
        await self.iniciar_ranqueada(interaction, "2x2")

    async def iniciar_ranqueada(self, interaction: discord.Interaction, formato: str):
        # Verificar se usuário está registrado, se não, registrar automaticamente
        user_db = session.query(Users).filter_by(discord_id=interaction.user.id).first()
        if not user_db:
            add_user = Users(interaction.user.id, interaction.user.name, 0, interaction.guild.id)
            session.add(add_user)
            session.commit()
            user_db = session.query(Users).filter_by(discord_id=interaction.user.id).first()

        # Perguntar se vai participar
        embed = Embed(
            title="🏆 Iniciando Ranqueada",
            description=f"**Formato:** `{formato}`\n\n**Você vai rimar na ranqueada?**",
            color=discord.Color.gold()
        )

        view = ConfirmarParticipacaoView(self.bot, interaction.user, formato)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ConfirmarParticipacaoView(View):
    """View para confirmar se o organizador vai participar"""
    def __init__(self, bot, organizador, formato):
        super().__init__(timeout=60)
        self.bot = bot
        self.organizador = organizador
        self.formato = formato

    @discord.ui.button(label="Sim, vou participar!", style=discord.ButtonStyle.green, emoji="✅")
    async def btn_sim(self, interaction: discord.Interaction, button: Button):
        await self.criar_sala_ranqueada(interaction, participando=True)

    @discord.ui.button(label="Não, só vou organizar", style=discord.ButtonStyle.gray, emoji="❌")
    async def btn_nao(self, interaction: discord.Interaction, button: Button):
        await self.criar_sala_ranqueada(interaction, participando=False)

    async def criar_sala_ranqueada(self, interaction: discord.Interaction, participando: bool):
        config = session.query(Guild_Config).filter_by(guild_id=interaction.guild.id).first()
        if not config:
            return await interaction.response.send_message("Servidor não configurado.", ephemeral=True)

        # Usar canal de inscrição da ranqueada
        if not config.ranqueada_inscricao_channel_id:
            return await interaction.response.send_message("Canal de inscrições da ranqueada não configurado. Use `/config_ranqueada`.", ephemeral=True)

        channel = interaction.guild.get_channel(config.ranqueada_inscricao_channel_id)
        if not channel:
            return await interaction.response.send_message("Canal de inscrições da ranqueada não encontrado.", ephemeral=True)

        # Criar lista de inscritos
        inscritos = []
        organizador_participando = participando

        if participando:
            user_db = session.query(Users).filter_by(discord_id=interaction.user.id).first()
            inscritos.append({
                'user': interaction.user,
                'mmr': user_db.MRR if user_db else 0,
                'garantido': True  # Organizador é garantido
            })

        # Obter canal de confronto
        confronto_channel = interaction.guild.get_channel(config.ranqueada_confronto_channel_id) if config.ranqueada_confronto_channel_id else None

        # Criar view de inscrição
        view = InscricaoRanqueadaView(
            self.bot,
            self.organizador,
            self.formato,
            inscritos,
            organizador_participando,
            confronto_channel
        )

        # Criar embed da ranqueada
        embed = view.criar_embed_atualizado()

        await interaction.response.edit_message(
            embed=Embed(title="✅ Ranqueada criada!", description=f"Veja no canal {channel.mention}.", color=discord.Color.green()),
            view=None
        )

        message = await channel.send(embed=embed, view=view)
        view.message = message

        # Iniciar timer de 5 minutos
        asyncio.create_task(view.iniciar_timer(message, channel))


class InscricaoRanqueadaView(View):
    """View para inscrição na ranqueada com timer"""
    def __init__(self, bot, organizador, formato, inscritos, organizador_participando, confronto_channel=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.organizador = organizador
        self.formato = formato
        self.inscritos = inscritos
        self.organizador_participando = organizador_participando
        self.confronto_channel = confronto_channel
        self.message = None
        self.finalizado = False
        self.tempo_restante = 300  # 5 minutos

        # Configurações baseadas no formato
        # 1x1: max 8, min 4, sorteia 4
        # 2x2: max 16, min 8, sorteia 8
        if formato == "1x1":
            self.max_jogadores = 8
            self.min_jogadores = 4
            self.jogadores_sorteio = 4
        else:  # 2x2
            self.max_jogadores = 16
            self.min_jogadores = 8
            self.jogadores_sorteio = 8

    @discord.ui.button(label="Participar", style=discord.ButtonStyle.green, emoji="✅", custom_id="ranqueada_participar")
    async def btn_participar(self, interaction: discord.Interaction, button: Button):
        if self.finalizado:
            return await interaction.response.send_message("Esta ranqueada já foi finalizada!", ephemeral=True)

        # Verificar se já está inscrito
        for inscrito in self.inscritos:
            if inscrito['user'].id == interaction.user.id:
                return await interaction.response.send_message("Você já está inscrito!", ephemeral=True)

        # Verificar se está registrado, se não, registrar automaticamente
        user_db = session.query(Users).filter_by(discord_id=interaction.user.id).first()
        if not user_db:
            add_user = Users(interaction.user.id, interaction.user.name, 0, interaction.guild.id)
            session.add(add_user)
            session.commit()
            user_db = session.query(Users).filter_by(discord_id=interaction.user.id).first()

        # Adicionar à lista
        self.inscritos.append({
            'user': interaction.user,
            'mmr': user_db.MRR,
            'garantido': False
        })

        await interaction.response.send_message(f"✅ Você foi inscrito na ranqueada!", ephemeral=True)

        # Atualizar embed
        await self.atualizar_embed()

        # Se bateu o máximo, iniciar imediatamente
        if len(self.inscritos) >= self.max_jogadores:
            await self.iniciar_partida(self.message.channel, modo="completo")

    @discord.ui.button(label="Sair", style=discord.ButtonStyle.red, emoji="❌", custom_id="ranqueada_sair")
    async def btn_sair(self, interaction: discord.Interaction, button: Button):
        if self.finalizado:
            return await interaction.response.send_message("Esta ranqueada já foi finalizada!", ephemeral=True)

        # Verificar se está inscrito
        inscrito_encontrado = None
        for inscrito in self.inscritos:
            if inscrito['user'].id == interaction.user.id:
                inscrito_encontrado = inscrito
                break

        if not inscrito_encontrado:
            return await interaction.response.send_message("Você não está inscrito!", ephemeral=True)

        # Remover da lista
        self.inscritos.remove(inscrito_encontrado)

        await interaction.response.send_message(f"❌ Você saiu da ranqueada!", ephemeral=True)

        # Atualizar embed
        await self.atualizar_embed()

    @discord.ui.button(label="Cancelar Ranqueada", style=discord.ButtonStyle.gray, emoji="🗑️", custom_id="ranqueada_cancelar", row=1)
    async def btn_cancelar(self, interaction: discord.Interaction, button: Button):
        # Apenas organizador ou OWNER pode cancelar
        if interaction.user.id != self.organizador.id and interaction.user.id != config_bot.OWNER_ID:
            return await interaction.response.send_message("Apenas o organizador pode cancelar!", ephemeral=True)

        if self.finalizado:
            return await interaction.response.send_message("Esta ranqueada já foi finalizada!", ephemeral=True)

        self.finalizado = True

        embed = Embed(
            title="❌ Ranqueada Cancelada",
            description=f"A ranqueada foi cancelada por {interaction.user.mention}.",
            color=discord.Color.red()
        )

        await self.message.edit(embed=embed, view=None)
        await interaction.response.send_message("Ranqueada cancelada!", ephemeral=True)

    async def atualizar_embed(self):
        if not self.message or self.finalizado:
            return

        embed = self.criar_embed_atualizado()
        try:
            await self.message.edit(embed=embed, view=self)
        except:
            pass

    def criar_embed_atualizado(self):
        minutos = self.tempo_restante // 60
        segundos = self.tempo_restante % 60

        inscritos_texto = ""
        if self.inscritos:
            for i, inscrito in enumerate(self.inscritos, 1):
                garantido = " ⭐" if inscrito.get('garantido') else ""
                inscritos_texto += f"`{i}.` {inscrito['user'].mention} (MMR: {inscrito['mmr']}){garantido}\n"
        else:
            inscritos_texto = "*Nenhum inscrito ainda*"

        # Texto das regras baseado no formato
        if self.formato == "1x1":
            regras = (
                f"• Se bater **{self.max_jogadores} inscritos** → Inicia imediatamente\n"
                f"• Se não bater em 5min → Sorteia **{self.jogadores_sorteio} jogadores**\n"
                f"• Mínimo **{self.min_jogadores} jogadores** para acontecer"
            )
        else:  # 2x2
            regras = (
                f"• Se bater **{self.max_jogadores} inscritos** → Inicia imediatamente\n"
                f"• Se não bater em 5min → Sorteia **{self.jogadores_sorteio} jogadores** (4 duplas)\n"
                f"• Mínimo **{self.min_jogadores} jogadores** para acontecer\n"
                f"• As duplas serão sorteadas automaticamente!"
            )

        embed = Embed(
            title=f"🏆 Ranqueada {self.formato}",
            description=(
                f"**Organizador:** {self.organizador.mention}\n"
                f"**Formato:** `{self.formato}`\n"
                f"**Tempo restante:** `{minutos:02d}:{segundos:02d}`\n\n"
                f"**Regras:**\n{regras}\n\n"
                f"**Clique em 'Participar' para entrar!**"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name=f"📋 Inscritos ({len(self.inscritos)}/{self.max_jogadores})",
            value=inscritos_texto,
            inline=False
        )

        embed.set_footer(text="⭐ = Vaga garantida (organizador)")
        return embed

    async def iniciar_timer(self, message, channel):
        """Timer de 5 minutos com atualização a cada 30 segundos"""
        while self.tempo_restante > 0 and not self.finalizado:
            await asyncio.sleep(30)
            self.tempo_restante -= 30

            if self.finalizado:
                return

            # Atualizar embed com tempo restante
            await self.atualizar_embed()

            # Verificar se já bateu o máximo
            if len(self.inscritos) >= self.max_jogadores:
                await self.iniciar_partida(channel, modo="completo")
                return

        # Tempo acabou
        if not self.finalizado:
            if len(self.inscritos) >= self.min_jogadores:
                await self.iniciar_partida(channel, modo="sorteio")
            else:
                await self.cancelar_por_falta_jogadores(channel)

    async def iniciar_partida(self, channel, modo: str):
        """Inicia a partida com jogadores completos ou sorteados"""
        if self.finalizado:
            return

        self.finalizado = True

        if modo == "completo":
            # Pegar os jogadores até o máximo
            jogadores_selecionados = self.inscritos[:self.max_jogadores]
            titulo = f"🏆 Ranqueada Iniciada! ({self.max_jogadores} jogadores)"
        else:
            # Sortear jogadores, garantindo o organizador se estiver participando
            garantidos = [i for i in self.inscritos if i.get('garantido')]
            nao_garantidos = [i for i in self.inscritos if not i.get('garantido')]

            vagas_sorteio = self.jogadores_sorteio - len(garantidos)

            if vagas_sorteio > 0 and len(nao_garantidos) > 0:
                sorteados = random.sample(nao_garantidos, min(vagas_sorteio, len(nao_garantidos)))
                jogadores_selecionados = garantidos + sorteados
            else:
                jogadores_selecionados = garantidos[:self.jogadores_sorteio]

            titulo = f"🏆 Ranqueada Iniciada! ({len(jogadores_selecionados)} jogadores sorteados)"

        # Para 2x2, sortear as duplas
        if self.formato == "2x2":
            # Embaralhar jogadores para formar duplas aleatórias
            jogadores_embaralhados = jogadores_selecionados.copy()
            random.shuffle(jogadores_embaralhados)

            # Criar texto com duplas
            jogadores_texto = "**Duplas sorteadas:**\n"
            jogadores_ids = []
            for i in range(0, len(jogadores_embaralhados), 2):
                if i + 1 < len(jogadores_embaralhados):
                    j1 = jogadores_embaralhados[i]
                    j2 = jogadores_embaralhados[i + 1]
                    dupla_num = (i // 2) + 1
                    jogadores_texto += f"**Dupla {dupla_num}:** {j1['user'].mention} + {j2['user'].mention}\n"
                    jogadores_ids.append(j1['user'].id)
                    jogadores_ids.append(j2['user'].id)

            # Atualizar jogadores_selecionados com a ordem embaralhada
            jogadores_selecionados = jogadores_embaralhados
        else:
            # 1x1 - lista normal
            jogadores_texto = ""
            jogadores_ids = []
            for i, jogador in enumerate(jogadores_selecionados, 1):
                jogadores_texto += f"`{i}.` {jogador['user'].mention} (MMR: {jogador['mmr']})\n"
                jogadores_ids.append(jogador['user'].id)

        embed = Embed(
            title=titulo,
            description=(
                f"**Organizador:** {self.organizador.mention}\n"
                f"**Formato:** `{self.formato}`\n"
                f"**Tipo:** Ranqueada (K=5)\n\n"
                f"{jogadores_texto}"
            ),
            color=discord.Color.green()
        )

        # Criar view de finalização
        view = FinalizarMatchmaking(
            self.bot,
            self.organizador,
            jogadores_ids,
            self.formato,
            "ranqueada"
        )

        # Atualizar embed no canal de inscrição
        await self.message.edit(embed=embed, view=None)

        # Mencionar jogadores no canal de inscrição
        mencoes = " ".join([j['user'].mention for j in jogadores_selecionados])
        await channel.send(f"🎮 **Ranqueada iniciada!** {mencoes}")

        # Enviar para o canal de confronto se configurado
        if self.confronto_channel:
            confronto_msg = await self.confronto_channel.send(embed=embed, view=view)
        else:
            # Se não tiver canal de confronto, usa o canal de inscrição
            confronto_msg = await channel.send(embed=embed, view=view)

    async def cancelar_por_falta_jogadores(self, channel):
        """Cancela se não tiver jogadores suficientes"""
        if self.finalizado:
            return

        self.finalizado = True

        embed = Embed(
            title="❌ Ranqueada Cancelada",
            description=(
                f"Não houve jogadores suficientes.\n\n"
                f"**Inscritos:** {len(self.inscritos)}/{self.min_jogadores} (mínimo)\n"
                f"**Organizador:** {self.organizador.mention}"
            ),
            color=discord.Color.red()
        )

        await self.message.edit(embed=embed, view=None)
