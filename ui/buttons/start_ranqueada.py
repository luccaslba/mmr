import discord, emojis, asyncio, random, config_bot
from discord import Embed
from discord.ui import View, Button, Select
from db import session, Users, Guild_Config, InscricaoEvento, InscricaoEventoParticipante
from ui.buttons.finalizar_matchmaking import FinalizarMatchmaking

class StartRanqueadaView(View):
    """View inicial com botões para escolher formato 1x1, 2x2 ou 3x3"""
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="1x1", style=discord.ButtonStyle.blurple, emoji="👤", custom_id="ranqueada_1x1")
    async def btn_1x1(self, interaction: discord.Interaction, button: Button):
        await self.iniciar_ranqueada(interaction, "1x1")

    @discord.ui.button(label="2x2", style=discord.ButtonStyle.blurple, emoji="👥", custom_id="ranqueada_2x2")
    async def btn_2x2(self, interaction: discord.Interaction, button: Button):
        await self.iniciar_ranqueada(interaction, "2x2")

    @discord.ui.button(label="3x3", style=discord.ButtonStyle.blurple, emoji="👥", custom_id="ranqueada_3x3")
    async def btn_3x3(self, interaction: discord.Interaction, button: Button):
        await self.iniciar_ranqueada(interaction, "3x3")

    async def iniciar_ranqueada(self, interaction: discord.Interaction, formato: str):
        # Verificar permissão para puxar ranqueada deste formato
        config = session.query(Guild_Config).filter_by(guild_id=interaction.guild.id).first()
        if config:
            tem_permissao = False
            cargo_necessario = None

            # Verificar permissões hierárquicas (3x3 pode tudo, 2x2 pode 1x1 e 2x2, 1x1 só 1x1)
            # Cargo 3x3 pode puxar qualquer formato
            if config.ranqueada_perm_3x3_role_id:
                role_3x3 = interaction.guild.get_role(config.ranqueada_perm_3x3_role_id)
                if role_3x3 and role_3x3 in interaction.user.roles:
                    tem_permissao = True

            # Cargo 2x2 pode puxar 1x1 e 2x2
            if not tem_permissao and formato in ["1x1", "2x2"] and config.ranqueada_perm_2x2_role_id:
                role_2x2 = interaction.guild.get_role(config.ranqueada_perm_2x2_role_id)
                if role_2x2 and role_2x2 in interaction.user.roles:
                    tem_permissao = True

            # Cargo 1x1 pode puxar apenas 1x1
            if not tem_permissao and formato == "1x1" and config.ranqueada_perm_1x1_role_id:
                role_1x1 = interaction.guild.get_role(config.ranqueada_perm_1x1_role_id)
                if role_1x1 and role_1x1 in interaction.user.roles:
                    tem_permissao = True

            # Se não tem nenhum cargo configurado, permite todos (comportamento padrão)
            if not config.ranqueada_perm_1x1_role_id and not config.ranqueada_perm_2x2_role_id and not config.ranqueada_perm_3x3_role_id:
                tem_permissao = True

            # OWNER sempre pode
            if interaction.user.id == config_bot.OWNER_ID:
                tem_permissao = True

            if not tem_permissao:
                # Determinar qual cargo é necessário
                if formato == "1x1":
                    cargo_id = config.ranqueada_perm_1x1_role_id or config.ranqueada_perm_2x2_role_id or config.ranqueada_perm_3x3_role_id
                elif formato == "2x2":
                    cargo_id = config.ranqueada_perm_2x2_role_id or config.ranqueada_perm_3x3_role_id
                else:  # 3x3
                    cargo_id = config.ranqueada_perm_3x3_role_id

                cargo_mention = f"<@&{cargo_id}>" if cargo_id else "configurado"

                return await interaction.response.send_message(
                    f"❌ Você não tem permissão para puxar ranqueada **{formato}**!\n\n"
                    f"Cargo necessário: {cargo_mention}",
                    ephemeral=True
                )

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

        # Obter canal de confronto
        confronto_channel = interaction.guild.get_channel(config.ranqueada_confronto_channel_id) if config.ranqueada_confronto_channel_id else None

        # Criar view de inscrição (agora sem botões de participar/sair)
        view = InscricaoRanqueadaView(
            self.bot,
            self.organizador,
            self.formato,
            participando,
            confronto_channel,
            interaction.guild.id
        )

        # Criar embed da ranqueada
        embed = view.criar_embed_atualizado()

        await interaction.response.edit_message(
            embed=Embed(title="✅ Ranqueada criada!", description=f"Veja no canal {channel.mention}.", color=discord.Color.green()),
            view=None
        )

        message = await channel.send(embed=embed, view=view)
        view.message = message

        # Criar registro de inscrição aberta
        inscricao = InscricaoEvento(
            guild_id=interaction.guild.id,
            channel_id=channel.id,
            message_id=message.id,
            autor_id=interaction.user.id,
            formato=self.formato,
            vagas=view.max_jogadores,
            tipo_evento="ranqueada",
            modo_sorteio="unico"
        )
        session.add(inscricao)
        session.commit()

        view.inscricao_id = inscricao.id

        # Se organizador vai participar, inscrever automaticamente
        if participando:
            user_db = session.query(Users).filter_by(discord_id=interaction.user.id).first()
            participante = InscricaoEventoParticipante(
                inscricao_id=inscricao.id,
                user_id=interaction.user.id,
                user_name=interaction.user.name
            )
            session.add(participante)
            session.commit()

        # Iniciar timer de 5 minutos
        asyncio.create_task(view.iniciar_timer(message, channel))


class InscricaoRanqueadaView(View):
    """View para inscrição na ranqueada com timer (usando mensagem '.')"""
    def __init__(self, bot, organizador, formato, organizador_participando, confronto_channel=None, guild_id=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.organizador = organizador
        self.formato = formato
        self.organizador_participando = organizador_participando
        self.confronto_channel = confronto_channel
        self.guild_id = guild_id
        self.message = None
        self.finalizado = False
        self.tempo_restante = 300  # 5 minutos
        self.inscricao_id = None  # Será definido após criar a inscrição

        # Configurações baseadas no formato
        # 1x1: max 8, min 4, sorteia 4
        # 2x2: max 16, min 8, sorteia 8 (4 duplas)
        # 3x3: max 24, min 12, sorteia 12 (4 trios)
        if formato == "1x1":
            self.max_jogadores = 8
            self.min_jogadores = 4
            self.jogadores_sorteio = 4
        elif formato == "2x2":
            self.max_jogadores = 16
            self.min_jogadores = 8
            self.jogadores_sorteio = 8
        else:  # 3x3
            self.max_jogadores = 24
            self.min_jogadores = 12
            self.jogadores_sorteio = 12

    def buscar_inscritos(self):
        """Busca os inscritos da tabela e retorna lista formatada"""
        if not self.inscricao_id:
            return []

        participantes_db = session.query(InscricaoEventoParticipante).filter_by(inscricao_id=self.inscricao_id).all()
        guild = self.bot.get_guild(self.guild_id)

        inscritos = []
        for i, participante in enumerate(participantes_db):
            member = guild.get_member(participante.user_id) if guild else None
            user_db = session.query(Users).filter_by(discord_id=participante.user_id).first()

            # Verificar se é o organizador (garantido)
            eh_organizador = participante.user_id == self.organizador.id and self.organizador_participando

            inscritos.append({
                'user': member,
                'user_id': participante.user_id,
                'user_name': participante.user_name,
                'mmr': user_db.MRR if user_db else 0,
                'garantido': eh_organizador
            })

        return inscritos

    @discord.ui.button(label="Cancelar Ranqueada", style=discord.ButtonStyle.gray, emoji="🗑️", custom_id="ranqueada_cancelar")
    async def btn_cancelar(self, interaction: discord.Interaction, button: Button):
        # Apenas organizador ou OWNER pode cancelar
        if interaction.user.id != self.organizador.id and interaction.user.id != config_bot.OWNER_ID:
            return await interaction.response.send_message("Apenas o organizador pode cancelar!", ephemeral=True)

        if self.finalizado:
            return await interaction.response.send_message("Esta ranqueada já foi finalizada!", ephemeral=True)

        self.finalizado = True

        # Marcar inscrição como inativa
        if self.inscricao_id:
            inscricao = session.query(InscricaoEvento).filter_by(id=self.inscricao_id).first()
            if inscricao:
                inscricao.ativo = False
                session.commit()

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

        # Buscar inscritos da tabela
        inscritos = self.buscar_inscritos()

        inscritos_texto = ""
        if inscritos:
            for i, inscrito in enumerate(inscritos, 1):
                garantido = " ⭐" if inscrito.get('garantido') else ""
                if inscrito['user']:
                    inscritos_texto += f"`{i}.` {inscrito['user'].mention} (MMR: {inscrito['mmr']}){garantido}\n"
                else:
                    inscritos_texto += f"`{i}.` {inscrito['user_name']} (MMR: {inscrito['mmr']}){garantido}\n"
        else:
            inscritos_texto = "*Nenhum inscrito ainda*"

        # Texto das regras baseado no formato
        if self.formato == "1x1":
            regras = (
                f"• Se bater **{self.max_jogadores} inscritos** → Inicia imediatamente\n"
                f"• Se não bater em 5min → Sorteia **{self.jogadores_sorteio} jogadores**\n"
                f"• Mínimo **{self.min_jogadores} jogadores** para acontecer"
            )
        elif self.formato == "2x2":
            regras = (
                f"• Se bater **{self.max_jogadores} inscritos** → Inicia imediatamente\n"
                f"• Se não bater em 5min → Sorteia **{self.jogadores_sorteio} jogadores** (4 duplas)\n"
                f"• Mínimo **{self.min_jogadores} jogadores** para acontecer\n"
                f"• As duplas serão sorteadas automaticamente!"
            )
        else:  # 3x3
            regras = (
                f"• Se bater **{self.max_jogadores} inscritos** → Inicia imediatamente\n"
                f"• Se não bater em 5min → Sorteia **{self.jogadores_sorteio} jogadores** (4 trios)\n"
                f"• Mínimo **{self.min_jogadores} jogadores** para acontecer\n"
                f"• Os trios serão sorteados automaticamente!"
            )

        embed = Embed(
            title=f"🏆 Ranqueada {self.formato}",
            description=(
                f"**Organizador:** {self.organizador.mention}\n"
                f"**Formato:** `{self.formato}`\n"
                f"**Tempo restante:** `{minutos:02d}:{segundos:02d}`\n\n"
                f"**Regras:**\n{regras}\n\n"
                f"**Digite `.` no chat para participar!**"
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name=f"📋 Inscritos ({len(inscritos)}/{self.max_jogadores})",
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

            # Buscar inscritos atuais
            inscritos = self.buscar_inscritos()

            # Atualizar embed com tempo restante
            await self.atualizar_embed()

            # Verificar se já bateu o máximo
            if len(inscritos) >= self.max_jogadores:
                await self.iniciar_partida(channel, modo="completo")
                return

        # Tempo acabou
        if not self.finalizado:
            inscritos = self.buscar_inscritos()
            if len(inscritos) >= self.min_jogadores:
                await self.iniciar_partida(channel, modo="sorteio")
            else:
                await self.cancelar_por_falta_jogadores(channel)

    async def iniciar_partida(self, channel, modo: str):
        """Inicia a partida com jogadores completos ou sorteados"""
        if self.finalizado:
            return

        self.finalizado = True

        # Marcar inscrição como inativa
        if self.inscricao_id:
            inscricao = session.query(InscricaoEvento).filter_by(id=self.inscricao_id).first()
            if inscricao:
                inscricao.ativo = False
                session.commit()

        # Buscar inscritos da tabela
        inscritos = self.buscar_inscritos()

        if modo == "completo":
            # Pegar os jogadores até o máximo
            jogadores_selecionados = inscritos[:self.max_jogadores]
            titulo = f"🏆 Ranqueada Iniciada! ({self.max_jogadores} jogadores)"
        else:
            # Sortear jogadores, garantindo o organizador se estiver participando
            garantidos = [i for i in inscritos if i.get('garantido')]
            nao_garantidos = [i for i in inscritos if not i.get('garantido')]

            vagas_sorteio = self.jogadores_sorteio - len(garantidos)

            if vagas_sorteio > 0 and len(nao_garantidos) > 0:
                sorteados = random.sample(nao_garantidos, min(vagas_sorteio, len(nao_garantidos)))
                jogadores_selecionados = garantidos + sorteados
            else:
                jogadores_selecionados = garantidos[:self.jogadores_sorteio]

            titulo = f"🏆 Ranqueada Iniciada! ({len(jogadores_selecionados)} jogadores sorteados)"

        # Formar times baseado no formato
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
                    j1_mention = j1['user'].mention if j1['user'] else j1['user_name']
                    j2_mention = j2['user'].mention if j2['user'] else j2['user_name']
                    jogadores_texto += f"**Dupla {dupla_num}:** {j1_mention} + {j2_mention}\n"
                    jogadores_ids.append(j1['user_id'])
                    jogadores_ids.append(j2['user_id'])

            # Atualizar jogadores_selecionados com a ordem embaralhada
            jogadores_selecionados = jogadores_embaralhados

        elif self.formato == "3x3":
            # Embaralhar jogadores para formar trios aleatórios
            jogadores_embaralhados = jogadores_selecionados.copy()
            random.shuffle(jogadores_embaralhados)

            # Criar texto com trios
            jogadores_texto = "**Trios sorteados:**\n"
            jogadores_ids = []
            for i in range(0, len(jogadores_embaralhados), 3):
                if i + 2 < len(jogadores_embaralhados):
                    j1 = jogadores_embaralhados[i]
                    j2 = jogadores_embaralhados[i + 1]
                    j3 = jogadores_embaralhados[i + 2]
                    trio_num = (i // 3) + 1
                    j1_mention = j1['user'].mention if j1['user'] else j1['user_name']
                    j2_mention = j2['user'].mention if j2['user'] else j2['user_name']
                    j3_mention = j3['user'].mention if j3['user'] else j3['user_name']
                    jogadores_texto += f"**Trio {trio_num}:** {j1_mention} + {j2_mention} + {j3_mention}\n"
                    jogadores_ids.append(j1['user_id'])
                    jogadores_ids.append(j2['user_id'])
                    jogadores_ids.append(j3['user_id'])

            # Atualizar jogadores_selecionados com a ordem embaralhada
            jogadores_selecionados = jogadores_embaralhados

        else:
            # 1x1 - lista normal
            jogadores_texto = ""
            jogadores_ids = []
            for i, jogador in enumerate(jogadores_selecionados, 1):
                jogador_mention = jogador['user'].mention if jogador['user'] else jogador['user_name']
                jogadores_texto += f"`{i}.` {jogador_mention} (MMR: {jogador['mmr']})\n"
                jogadores_ids.append(jogador['user_id'])

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

        # Mencionar jogadores no canal de inscrição (apenas os que ainda estão no servidor)
        mencoes = " ".join([f"<@{j['user_id']}>" for j in jogadores_selecionados])
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

        # Marcar inscrição como inativa
        if self.inscricao_id:
            inscricao = session.query(InscricaoEvento).filter_by(id=self.inscricao_id).first()
            if inscricao:
                inscricao.ativo = False
                session.commit()

        # Buscar inscritos para mostrar a quantidade
        inscritos = self.buscar_inscritos()

        embed = Embed(
            title="❌ Ranqueada Cancelada",
            description=(
                f"Não houve jogadores suficientes.\n\n"
                f"**Inscritos:** {len(inscritos)}/{self.min_jogadores} (mínimo)\n"
                f"**Organizador:** {self.organizador.mention}"
            ),
            color=discord.Color.red()
        )

        await self.message.edit(embed=embed, view=None)
