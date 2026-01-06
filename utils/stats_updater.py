import discord
from discord import Embed
from db import session, Guild_Config, OrganizadorContador, JuradoContador


async def atualizar_stats_organizador_ranqueada(guild: discord.Guild):
    """Atualiza o embed de estatísticas de organizadores em RANQUEADAS"""
    guild_config = session.query(Guild_Config).filter_by(guild_id=guild.id).first()

    if not guild_config or not guild_config.organizador_ranqueada_stats_channel_id:
        return

    channel = guild.get_channel(guild_config.organizador_ranqueada_stats_channel_id)
    if not channel:
        return

    # Buscar todos organizadores com ranqueadas neste servidor
    organizadores = session.query(OrganizadorContador).filter_by(guild_id=guild.id).filter(
        OrganizadorContador.contador_ranqueada > 0
    ).order_by(OrganizadorContador.contador_ranqueada.desc()).all()

    embed = Embed(
        title="📊 Estatísticas de Organizadores - Ranqueadas",
        description="Ranking de organizadores por quantidade de ranqueadas finalizadas.",
        color=discord.Color.gold()
    )

    if organizadores:
        ranking_texto = ""
        for i, org in enumerate(organizadores, 1):
            member = guild.get_member(org.user_id)
            nome = member.mention if member else f"<@{org.user_id}>"

            # Emoji para top 3
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"`{i}.`"

            ranking_texto += f"{emoji} {nome} - **{org.contador_ranqueada}** partidas\n"

        embed.add_field(name="🏆 Ranking", value=ranking_texto[:1024], inline=False)
    else:
        embed.add_field(name="🏆 Ranking", value="*Nenhum organizador ainda*", inline=False)

    embed.set_footer(text="Atualizado automaticamente ao finalizar partidas")

    # Procurar mensagem existente do bot ou enviar nova
    async for msg in channel.history(limit=50):
        if msg.author == guild.me and msg.embeds:
            if msg.embeds[0].title and "Organizadores - Ranqueadas" in msg.embeds[0].title:
                await msg.edit(embed=embed)
                return

    # Se não encontrou, envia nova mensagem
    await channel.send(embed=embed)


async def atualizar_stats_organizador_evento(guild: discord.Guild):
    """Atualiza o embed de estatísticas de organizadores em EVENTOS"""
    guild_config = session.query(Guild_Config).filter_by(guild_id=guild.id).first()

    if not guild_config or not guild_config.organizador_evento_stats_channel_id:
        return

    channel = guild.get_channel(guild_config.organizador_evento_stats_channel_id)
    if not channel:
        return

    # Buscar todos organizadores com eventos neste servidor
    organizadores = session.query(OrganizadorContador).filter_by(guild_id=guild.id).filter(
        OrganizadorContador.contador_evento > 0
    ).order_by(OrganizadorContador.contador_evento.desc()).all()

    embed = Embed(
        title="📊 Estatísticas de Organizadores - Eventos",
        description="Ranking de organizadores por quantidade de eventos finalizados.",
        color=discord.Color.blue()
    )

    if organizadores:
        ranking_texto = ""
        for i, org in enumerate(organizadores, 1):
            member = guild.get_member(org.user_id)
            nome = member.mention if member else f"<@{org.user_id}>"

            # Emoji para top 3
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"`{i}.`"

            ranking_texto += f"{emoji} {nome} - **{org.contador_evento}** partidas\n"

        embed.add_field(name="🎮 Ranking", value=ranking_texto[:1024], inline=False)
    else:
        embed.add_field(name="🎮 Ranking", value="*Nenhum organizador ainda*", inline=False)

    embed.set_footer(text="Atualizado automaticamente ao finalizar partidas")

    # Procurar mensagem existente do bot ou enviar nova
    async for msg in channel.history(limit=50):
        if msg.author == guild.me and msg.embeds:
            if msg.embeds[0].title and "Organizadores - Eventos" in msg.embeds[0].title:
                await msg.edit(embed=embed)
                return

    # Se não encontrou, envia nova mensagem
    await channel.send(embed=embed)


async def atualizar_stats_jurado(guild: discord.Guild):
    """Atualiza o embed de estatísticas de jurados (ranqueadas + eventos)"""
    guild_config = session.query(Guild_Config).filter_by(guild_id=guild.id).first()

    if not guild_config or not guild_config.jurado_stats_channel_id:
        return

    channel = guild.get_channel(guild_config.jurado_stats_channel_id)
    if not channel:
        return

    # Buscar todos jurados neste servidor (ordenar por total)
    jurados = session.query(JuradoContador).filter_by(guild_id=guild.id).all()

    # Ordenar por total (ranqueada + evento)
    jurados_ordenados = sorted(
        [j for j in jurados if j.contador_ranqueada > 0 or j.contador_evento > 0],
        key=lambda x: x.contador_ranqueada + x.contador_evento,
        reverse=True
    )

    embed = Embed(
        title="⚖️ Estatísticas de Jurados",
        description="Ranking de jurados por quantidade de partidas que participaram.",
        color=discord.Color.purple()
    )

    if jurados_ordenados:
        ranking_texto = ""
        for i, jur in enumerate(jurados_ordenados, 1):
            member = guild.get_member(jur.user_id)
            nome = member.mention if member else f"<@{jur.user_id}>"

            # Emoji para top 3
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"`{i}.`"

            total = jur.contador_ranqueada + jur.contador_evento
            ranking_texto += f"{emoji} {nome}\n   🏆 Ranqueadas: **{jur.contador_ranqueada}** | 🎮 Eventos: **{jur.contador_evento}** | Total: **{total}**\n"

        embed.add_field(name="⚖️ Ranking", value=ranking_texto[:1024], inline=False)
    else:
        embed.add_field(name="⚖️ Ranking", value="*Nenhum jurado ainda*", inline=False)

    embed.set_footer(text="Atualizado automaticamente ao finalizar partidas")

    # Procurar mensagem existente do bot ou enviar nova
    async for msg in channel.history(limit=50):
        if msg.author == guild.me and msg.embeds:
            if msg.embeds[0].title and "Estatísticas de Jurados" in msg.embeds[0].title:
                await msg.edit(embed=embed)
                return

    # Se não encontrou, envia nova mensagem
    await channel.send(embed=embed)


async def incrementar_organizador(guild_id: int, user_id: int, tipo_evento: str, guild: discord.Guild):
    """
    Incrementa o contador do organizador e atualiza os embeds.

    tipo_evento: "ranqueada" ou qualquer outro valor (evento)
    """
    # Buscar ou criar contador do organizador
    org = session.query(OrganizadorContador).filter_by(guild_id=guild_id, user_id=user_id).first()

    if not org:
        org = OrganizadorContador(guild_id, user_id)
        session.add(org)

    if tipo_evento == "ranqueada":
        org.contador_ranqueada += 1
    else:
        org.contador_evento += 1

    session.commit()

    # Atualizar embed correspondente
    if tipo_evento == "ranqueada":
        await atualizar_stats_organizador_ranqueada(guild)
    else:
        await atualizar_stats_organizador_evento(guild)


async def incrementar_jurado(guild_id: int, user_id: int, tipo_evento: str, guild: discord.Guild):
    """
    Incrementa o contador do jurado e atualiza o embed.

    tipo_evento: "ranqueada" ou qualquer outro valor (evento)
    """
    # Buscar ou criar contador do jurado
    jur = session.query(JuradoContador).filter_by(guild_id=guild_id, user_id=user_id).first()

    if not jur:
        jur = JuradoContador(guild_id, user_id)
        session.add(jur)

    if tipo_evento == "ranqueada":
        jur.contador_ranqueada += 1
    else:
        jur.contador_evento += 1

    session.commit()

    # Atualizar embed de jurados
    await atualizar_stats_jurado(guild)
