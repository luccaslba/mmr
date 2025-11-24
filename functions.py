import asyncio, discord, random, pytz
from datetime import datetime, timezone, date
from sqlalchemy.orm import sessionmaker
from db import session, Users, Guild_Config, CloseMatchMember, MatchParticipantes, MatchPartidaParticipantes, RolesVips
from discord import Embed
from ui.buttons.finalizar_matchmaking import FinalizarMatchmaking

async def aguardar_e_iniciar_matchmaking(bot, guild_id, channel_id, message_id, formato, vagas, tipo_evento, datahora, autor):

    # Ajuste para timezone aware (horário de Brasília)
    now = datetime.now(pytz.timezone("America/Sao_Paulo"))
    tempo_espera = (datahora - now).total_seconds()
    print(now)
    print(tempo_espera)

    if tempo_espera > 0:
        print(f"[Matchmaking] Aguardando {tempo_espera} segundos até o horário marcado.")
        await asyncio.sleep(tempo_espera)

    print("[Matchmaking] Hora de iniciar o matchmaking!")


    channel = bot.get_channel(channel_id)
    await asyncio.sleep(1)  # Garante tempo para reações serem processadas
    message = await channel.fetch_message(message_id)

    reaction = next((r for r in message.reactions if str(r.emoji) == "✅"), None)
    if not reaction:
        return await channel.send("❌ Nenhuma reação encontrada.")

    guild = session.query(Guild_Config).filter_by(guild_id=guild_id).first()

    print(f"Tipo de evento: {tipo_evento}")
    print(f"Guilda match_close_count: {guild.match_close_count}")

    jogadores = []
    async for user in reaction.users():
        user_db = session.query(Users).filter_by(discord_id=user.id).first()

        if not user.bot:
            if not user_db:
                add_user = Users(user.id, user.name, 0, user.guild.id)
                session.add(add_user)
                session.commit()

            if tipo_evento in ["f", "fechado"]:
                user_db = session.query(Users).filter_by(discord_id=user.id).first()
                if user_db.MRR < guild.match_close_count:
                    continue
            
            member = session.query(MatchParticipantes).filter_by(discord_id=user.id).first()
            if not member:
                add_member = MatchParticipantes(user.id, user.name, autor.id)
                session.add(add_member)
                session.commit()
            jogadores.append(user)
            print(f"{user.name} adicionado à lista de jogadores")



    print(f"Total de jogadores válidos: {len(jogadores)}")


    jogadores_por_time = int(formato.split("x")[0])
    jogadores_por_partida = jogadores_por_time * 2  # Exemplo: 2x2 = 4 pessoas por partida

    # Calcular total de pessoas necessárias
    # vagas = número de vagas do torneio (exemplo: 8 vagas)
    # Para 1x1: 8 vagas = 8 pessoas
    # Para 2x2: 8 vagas = 8 equipes = 16 pessoas
    # Para 3x3: 8 vagas = 8 equipes = 24 pessoas
    if formato == "1x1":
        total_pessoas_necessarias = vagas
    else:
        total_pessoas_necessarias = vagas * jogadores_por_time

    cargos_vip_db = session.query(RolesVips).order_by(RolesVips.peso.desc()).all()
    cargos_vip = {int(cargo.role_id): cargo.peso for cargo in cargos_vip_db}

    # Jogadores com seus respectivos pesos
    jogadores_com_peso = []
    for jogador in jogadores:
        peso = 0
        for role in jogador.roles:
            if role.id in cargos_vip:
                peso = max(peso, cargos_vip[role.id])  # pega o maior peso que o jogador tem
        jogadores_com_peso.append((jogador, peso))

    # Ordenar por peso (VIPs mais prioritários primeiro)
    jogadores_com_peso.sort(key=lambda x: x[1], reverse=True)

    # Selecionar apenas o número exato de vagas do torneio
    # Para 1x1: vagas = jogadores (ex: 4 vagas = 4 jogadores)
    # Para 2x2: vagas = equipes (ex: 4 vagas = 8 jogadores)
    # Para 3x3: vagas = equipes (ex: 4 vagas = 12 jogadores)
    jogadores_selecionados = [j for j, _ in jogadores_com_peso[:total_pessoas_necessarias]]

    if len(jogadores_selecionados) < total_pessoas_necessarias:
        texto_formato = f"{vagas} vagas ({total_pessoas_necessarias} pessoas)" if formato != "1x1" else f"{vagas} jogadores"
        embed = discord.Embed(
            title="❌ Jogadores insuficientes!",
            description=(
                f"Eram necessários pelo menos **{jogadores_por_partida}** jogadores para formar uma partida no formato `{formato}`.\n"
                f"Apenas **{len(jogadores)}** reagiram ao evento válidos. Nenhuma partida foi formada."
            ),
            color=discord.Color.red()
        )
        member = session.query(MatchParticipantes).filter_by(autor_id=autor.id).all()
        if member:
            for m in member:
                session.delete(m)
            session.commit()
        await channel.send(embed=embed)
        return

    # Prosseguir com matchmaking com jogadores selecionados
    partidas = sortear_partidas(jogadores_selecionados, formato)
    embed = gerar_embed_partidas(partidas, formato, tipo_evento)
    await channel.send(embed=embed, view=FinalizarMatchmaking(bot, autor))


def sortear_partidas(jogadores_discord, formato: str):
    jogadores_por_time = int(formato.split("x")[0])

    jogadores_com_mmr = []

    for user in jogadores_discord:
        jogador_db = session.query(Users).filter_by(discord_id=str(user.id)).first()
        if not jogador_db:
            continue  # Ignora quem não está no banco
        jogadores_com_mmr.append({
            "user": user,
            "mmr": jogador_db.MRR
        })

    # Ordena por MMR (maior para menor) - SEM shuffle global
    jogadores_ordenados = sorted(jogadores_com_mmr, key=lambda j: j["mmr"], reverse=True)

    # Embaralha para confrontos aleatórios
    random.shuffle(jogadores_ordenados)

    # Criar confrontos do torneio
    # Para 1x1: cada confronto tem 2 jogadores
    # Para 2x2: cada confronto tem 2 equipes de 2 jogadores (4 pessoas)
    # Para 3x3: cada confronto tem 2 equipes de 3 jogadores (6 pessoas)
    confrontos = []
    jogadores_por_confronto = jogadores_por_time * 2

    for i in range(0, len(jogadores_ordenados), jogadores_por_confronto):
        grupo = jogadores_ordenados[i:i+jogadores_por_confronto]
        if len(grupo) < jogadores_por_confronto:
            break

        time1 = grupo[:jogadores_por_time]
        time2 = grupo[jogadores_por_time:]

        confrontos.append((time1, time2))

    return confrontos

def gerar_embed_partidas(partidas, formato, tipo_evento):
    # Determinar nome da rodada baseado no número de confrontos
    num_confrontos = len(partidas)
    if num_confrontos == 1:
        rodada_nome = "Final"
    elif num_confrontos == 2:
        rodada_nome = "Semifinal"
    elif num_confrontos == 4:
        rodada_nome = "Quartas de Final"
    elif num_confrontos == 8:
        rodada_nome = "Oitavas de Final"
    else:
        rodada_nome = f"Rodada 1 ({num_confrontos} confrontos)"

    embed = Embed(
        title=f"⚔️ {rodada_nome} - Torneio {formato}",
        description=f"**Evento:** `{tipo_evento.capitalize()}`\n",
        color=0x2F3136
    )

    for idx, (time1, time2) in enumerate(partidas, start=1):
        def formatar_time(time):
            if len(time) == 1:
                # 1x1: apenas o jogador
                return f"<@{time[0]['user'].id}> ({time[0]['mmr']} MMR)"
            else:
                # 2x2 ou 3x3: equipe
                return " & ".join(f"<@{j['user'].id}> ({j['mmr']})" for j in time)

        t1 = formatar_time(time1)
        t2 = formatar_time(time2)

        embed.add_field(name=f"Batalha {idx}", value=f"{t1}\n**VS**\n{t2}", inline=False)

    return embed

async def finalizar_torneio(session, autor_id, classificacao, participantes, formato, valor_partida):
    """
    Finaliza o torneio e calcula MMR baseado na classificação final

    Args:
        session: Sessão do banco de dados
        autor_id: ID do organizador
        classificacao: Dict {posicao: user_id}
        participantes: Lista de dicts com 'user' e 'mmr'
        formato: String do formato (1x1, 2x2, 3x3)
        valor_partida: Valor da partida

    Returns:
        Dict com 'sucesso' e 'resultados' ou 'erro'
    """
    try:
        num_jogadores = len(participantes)

        # Calcular MMR médio
        mmr_total = sum(p['mmr'] for p in participantes)
        mmr_medio = mmr_total / num_jogadores

        K = 32  # Constante K do ELO

        resultados = {}

        for posicao, user_id in classificacao.items():
            # Buscar jogador no banco
            user_db = session.query(Users).filter_by(discord_id=user_id).first()
            if not user_db:
                continue

            mmr_antigo = user_db.MRR

            # Calcular delta de MMR
            delta_mmr = calcular_mmr(
                mmr_jogador=mmr_antigo,
                mmr_medio=mmr_medio,
                colocacao=posicao,
                k=K,
                jogadores_quantity=num_jogadores
            )

            # Atualizar MMR
            mmr_novo = mmr_antigo + int(delta_mmr)
            user_db.MRR = mmr_novo

            resultados[posicao] = {
                'user_id': user_id,
                'mmr_antigo': mmr_antigo,
                'mmr_novo': mmr_novo,
                'delta_mmr': int(delta_mmr)
            }

        session.commit()

        return {
            'sucesso': True,
            'resultados': resultados
        }

    except Exception as e:
        session.rollback()
        return {
            'sucesso': False,
            'erro': str(e)
        }

def coletar_dados_usuarios(users):
    dados = []
    for u in users:
        db_user = session.query(Users).filter_by(id=u.id).first()
        if db_user:
            dados.append({
                "id": u.id,
                "mmr": db_user.mmr or 1000  # Valor default caso nulo
            })
    return dados

def calcular_mmr(mmr_jogador: float, mmr_medio: float, colocacao: int, k: int, jogadores_quantity: int) -> float:
   ## Para partida de 4 pessoas
#1º Lugar RR = 0.8
#2º Lugar RR = 0.65
#3º e 4º Lugar RR = 0.3

## Para partida de 8 pessoas
#1º Lugar RR = 1
#2º Lugar RR = 0.8 
#3º e 4º lugar RR = 0.625 
#5º-8º lugar RR = 0.25

## Para partida de 16 pessoas
#1º Lugar RR = 1.2
#2º Lugar RR = 1.0 
#3º e 4º lugar RR = 0.8 
#5º-8º lugar RR = 0.5
#9º-16º Lugar RR = 0.25
    rr = 0
    # Verificar do maior para o menor para evitar conflitos
    if jogadores_quantity >= 16:
        if colocacao == 1:
            rr = 1.2
        elif colocacao == 2:
            rr = 1.0
        elif colocacao in [3, 4]:
            rr = 0.8
        elif colocacao in range(5, 9):  # 5, 6, 7, 8
            rr = 0.5
        elif colocacao in range(9, 17):  # 9 até 16
            rr = 0.25

    elif jogadores_quantity >= 8:
        if colocacao == 1:
            rr = 1.0
        elif colocacao == 2:
            rr = 0.8
        elif colocacao in [3, 4]:
            rr = 0.625
        elif colocacao in range(5, 9):  # 5, 6, 7, 8
            rr = 0.25

    elif jogadores_quantity >= 4:
        if colocacao == 1:
            rr = 0.8
        elif colocacao == 2:
            rr = 0.65
        elif colocacao in [3, 4]:
            rr = 0.3
    else:
        return 0

    re = 1 / (1 + 10 ** ((mmr_medio - mmr_jogador) / 600))

    return round(k * (rr - re), 2)

def processar_matchmaking(session, autor_id: int, k: int):

    membros = session.query(CloseMatchMember).filter_by(autor_id=autor_id).all()
    if not membros:
        print("Nenhum jogador encontrado.")
        return "Nenhum jogador encontrado."

    # Agrupar todos os dados: [(user, colocacao, equipe_id)]
    dados = []
    mmrs = []

    for membro in membros:
        user = session.query(Users).filter_by(discord_id=membro.discord_id).first()
        if user:
            dados.append((user, membro.player_pos, membro.equipe_id))
            mmrs.append(user.MRR)

    if not dados:
        print("Nenhum usuário válido encontrado.")
        return "Nenhum usuário válido encontrado."

    # Média de MMR da partida
    mmr_medio = sum(mmrs) / len(mmrs)

    # Agrupar por equipe (ou individual)
    grupos = {}  # {equipe_id: [(user, colocacao)]}
    for user, colocacao, equipe_id in dados:
        chave = f"solo-{user.discord_id}" if equipe_id == 0 else f"equipe-{equipe_id}"
        if chave not in grupos:
            grupos[chave] = {"colocacao": colocacao, "membros": []}
        grupos[chave]["membros"].append(user)

    # Calcular e aplicar MMR
    for chave, info in grupos.items():
        colocacao = info["colocacao"]
        for user in info["membros"]:
            member = []
            for membro in membros:
                member.append(membro)
            delta = calcular_mmr(user.MRR, mmr_medio, colocacao, k, len(member))
            print(f"[{chave}] {user.discord_name} - Colocação {colocacao} - MMR: {user.MRR} → {user.MRR + delta:+.2f}")
            user.MRR += delta

    for membro in membros:
        membro_db = session.query(MatchPartidaParticipantes).filter_by(discord_id=membro.discord_id).first()
        if not membro_db:
            print("Adicionando")
            add_member = MatchPartidaParticipantes(membro.discord_id, membro.discord_name, autor_id, membro.player_pos, membro.equipe_id)
            session.add(add_member)
            session.commit()
            print("Adicionado")
        session.delete(membro)
    session.commit()
    print("MMRs atualizados com sucesso.")
    return True

async def finalizar_batalha(interact: discord.Interaction, session, autor_id: int, k: int, canal_id):

    membros = session.query(MatchPartidaParticipantes).filter_by(autor_id=autor_id).all()
    if not membros:
        print("Nenhum jogador encontrado.")
        return ["Nenhum jogador encontrado."]

    # Agrupar todos os dados: [(user, colocacao, equipe_id)]
    dados = []
    mmrs = []

    for membro in membros:
        user = session.query(Users).filter_by(discord_id=membro.discord_id).first()
        if user:
            dados.append((user, membro.player_pos, membro.equipe_id))
            mmrs.append(user.MRR)

    if not dados:
        print("Nenhum usuário válido encontrado.")
        return ["Nenhum usuário válido encontrado."]

    # Agrupar por equipe (ou individual)
    grupos = {}  # {equipe_id: [(user, colocacao)]}
    for user, colocacao, equipe_id in dados:
        chave = f"solo-{user.discord_id}" if equipe_id == 0 else f"equipe-{equipe_id}"
        if chave not in grupos:
            grupos[chave] = {"colocacao": colocacao, "membros": []}
        grupos[chave]["membros"].append(user)

    organizador = interact.guild.get_member(autor_id)
    embed = await enviar_resultado_final(interact, grupos, organizador, k, canal_id)

    for membro in membros:
        session.delete(membro)
    session.commit()
    print("MMRs atualizados com sucesso.")
    return [True]

async def enviar_resultado_final(interaction: discord.Interaction, grupos: dict, organizador: discord.User, k: int, canal_id: int):
    canal = interaction.guild.get_channel(canal_id)
    if not canal:
        await interaction.followup.send("❌ Canal de resultados não encontrado.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🏁 Resultado Final do Matchmaking",
        description=f"Organizado por: **{organizador.mention}**\nConstante **K = {k}**",
        color=discord.Color.blurple()
    )

    # Ordenar grupos pela colocação (1º lugar primeiro)
    grupos_ordenados = sorted(grupos.items(), key=lambda x: x[1]["colocacao"])

    for chave, info in grupos_ordenados:
        colocacao = info["colocacao"]
        membros = info["membros"]

        # Nome da equipe ou jogador solo
        if chave.startswith("solo-"):
            nome = f"🧍 Solo - {membros[0].discord_name}"
        else:
            nome = f"👥 Equipe {chave.split('-')[1]}"

        lista = "\n".join(f"• {m.discord_name}" for m in membros)

        embed.add_field(
            name=f"{colocacao}º Lugar - {nome}",
            value=lista,
            inline=False
        )

    now = datetime.now(pytz.timezone("America/Sao_Paulo"))
    month = "0"
    if now.month >= 10:
        month = ""
    embed.set_footer(text=f"Finalizado em: {now.day}/{month}{now.month}/{now.year} as {now.hour}:{now.minute}:{now.second}")

    await canal.send(embed=embed)
