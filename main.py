import discord, config_bot, os, db, functions, sqlite3
from discord.ext import commands
from discord.ext.commands import Bot
from db import MatchParticipantes, InscricaoEvento, InscricaoEventoParticipante, Users, session
from ui.buttons.start_matchmaking import StartMatchMakingV2
from ui.buttons.finalizar_matchmaking import FinalizarMatchmaking
from ui.buttons.start_ranqueada import StartRanqueadaView

bot = Bot(command_prefix=config_bot.PREFIX, intents=discord.Intents.all())

def run_auto_migrations():
    """Executa migrações automaticamente ao iniciar o bot"""
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(GuildConfig)")
        columns = [column[1] for column in cursor.fetchall()]

        # Migração: ranqueada_channel_id
        if 'ranqueada_channel_id' not in columns:
            cursor.execute("ALTER TABLE GuildConfig ADD COLUMN ranqueada_channel_id INTEGER")
            conn.commit()
            print("✅ Migração: coluna ranqueada_channel_id adicionada")

        # Migração: bdf_role_id
        if 'bdf_role_id' not in columns:
            cursor.execute("ALTER TABLE GuildConfig ADD COLUMN bdf_role_id INTEGER")
            conn.commit()
            print("✅ Migração: coluna bdf_role_id adicionada")

        # Migração: ranqueada_inscricao_channel_id
        if 'ranqueada_inscricao_channel_id' not in columns:
            cursor.execute("ALTER TABLE GuildConfig ADD COLUMN ranqueada_inscricao_channel_id INTEGER")
            conn.commit()
            print("✅ Migração: coluna ranqueada_inscricao_channel_id adicionada")

        # Migração: ranqueada_confronto_channel_id
        if 'ranqueada_confronto_channel_id' not in columns:
            cursor.execute("ALTER TABLE GuildConfig ADD COLUMN ranqueada_confronto_channel_id INTEGER")
            conn.commit()
            print("✅ Migração: coluna ranqueada_confronto_channel_id adicionada")

        # Migração: equipe_id em InscricaoEventoParticipante
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='InscricaoEventoParticipante'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(InscricaoEventoParticipante)")
            columns_participante = [column[1] for column in cursor.fetchall()]
            if 'equipe_id' not in columns_participante:
                cursor.execute("ALTER TABLE InscricaoEventoParticipante ADD COLUMN equipe_id INTEGER")
                conn.commit()
                print("✅ Migração: coluna equipe_id adicionada à InscricaoEventoParticipante")

        conn.close()
        print("✅ Migrações verificadas com sucesso")
    except Exception as e:
        print(f"⚠️ Erro nas migrações: {e}")

async def load_commands():
    for filename in os.listdir("commands"):
        if filename.endswith(".py") and not filename.startswith("_"):
            await bot.load_extension(f"commands.{filename[:-3]}")
            print(f"🔧 comandos carregados: {filename}")


@bot.event
async def on_ready():
    print("Bot online: ", bot.user)
    run_auto_migrations()
    bot.add_view(StartMatchMakingV2(bot))
    bot.add_view(StartRanqueadaView(bot))
    await load_commands()


@bot.event
async def on_message(message):
    # Ignorar mensagens de bots
    if message.author.bot:
        return

    # Verificar se começa com "." para inscrição em evento/ranqueada
    conteudo = message.content.strip()
    if conteudo.startswith("."):
        try:
            # Refresh da sessão para pegar dados atualizados
            session.expire_all()

            # Verificar se há inscrição aberta neste canal
            inscricao = session.query(InscricaoEvento).filter_by(
                channel_id=message.channel.id,
                ativo=True
            ).first()

            if inscricao:

                # Pegar menções da mensagem (excluindo bots)
                mencoes = [m for m in message.mentions if not m.bot and m.id != message.author.id]

                # Determinar tamanho máximo do time baseado no formato
                formato = inscricao.formato
                if formato and "x" in formato:
                    tamanho_time = int(formato.split("x")[0])
                else:
                    tamanho_time = 1

                # Validar quantidade de menções
                max_mencoes = tamanho_time - 1  # 1x1=0, 2x2=1, 3x3=2
                if len(mencoes) > max_mencoes:
                    return await bot.process_commands(message)

                # Verificar se autor já está inscrito
                autor_inscrito = session.query(InscricaoEventoParticipante).filter_by(
                    inscricao_id=inscricao.id,
                    user_id=message.author.id
                ).first()

                if autor_inscrito:
                    # Se autor já está inscrito mas mandou menções, pode estar formando time
                    if mencoes and tamanho_time > 1:
                        # Verificar se autor já tem equipe completa
                        if autor_inscrito.equipe_id:
                            membros_equipe = session.query(InscricaoEventoParticipante).filter_by(
                                inscricao_id=inscricao.id,
                                equipe_id=autor_inscrito.equipe_id
                            ).count()
                            if membros_equipe >= tamanho_time:
                                # Equipe já completa
                                return await bot.process_commands(message)

                        # Definir equipe_id como o ID do autor (líder)
                        equipe_id = message.author.id
                        autor_inscrito.equipe_id = equipe_id
                        session.commit()

                        # Processar menções para adicionar à equipe
                        for mencionado in mencoes:
                            # Verificar se mencionado já está inscrito
                            mencionado_inscrito = session.query(InscricaoEventoParticipante).filter_by(
                                inscricao_id=inscricao.id,
                                user_id=mencionado.id
                            ).first()

                            if mencionado_inscrito:
                                # Se já está em outra equipe, não pode
                                if mencionado_inscrito.equipe_id and mencionado_inscrito.equipe_id != equipe_id:
                                    continue
                                # Adicionar à equipe do autor
                                mencionado_inscrito.equipe_id = equipe_id
                                session.commit()
                            else:
                                # Registrar mencionado no bot se necessário
                                user_db = session.query(Users).filter_by(discord_id=mencionado.id).first()
                                if not user_db:
                                    add_user = Users(mencionado.id, mencionado.name, 0, message.guild.id)
                                    session.add(add_user)
                                    session.commit()

                                # Verificar restrição de MMR para eventos fechados
                                if inscricao.tipo_evento in ["f", "fechado"]:
                                    user_db = session.query(Users).filter_by(discord_id=mencionado.id).first()
                                    guild_config = session.query(Guild_Config).filter_by(guild_id=message.guild.id).first()
                                    if guild_config and user_db.MRR < guild_config.match_close_count:
                                        continue  # MMR insuficiente - não adiciona

                                # Inscrever mencionado na equipe
                                participante = InscricaoEventoParticipante(
                                    inscricao_id=inscricao.id,
                                    user_id=mencionado.id,
                                    user_name=mencionado.name,
                                    equipe_id=equipe_id
                                )
                                session.add(participante)
                                session.commit()
                else:
                    # Autor não está inscrito - registrar
                    # Verificar se usuário está registrado no bot, se não, registrar
                    user_db = session.query(Users).filter_by(discord_id=message.author.id).first()
                    if not user_db:
                        add_user = Users(message.author.id, message.author.name, 0, message.guild.id)
                        session.add(add_user)
                        session.commit()

                    # Verificar restrição de MMR para eventos fechados
                    if inscricao.tipo_evento in ["f", "fechado"]:
                        user_db = session.query(Users).filter_by(discord_id=message.author.id).first()
                        guild_config = session.query(Guild_Config).filter_by(guild_id=message.guild.id).first()
                        if guild_config and user_db.MRR < guild_config.match_close_count:
                            # MMR insuficiente - não inscreve
                            return await bot.process_commands(message)

                    # Definir equipe_id se tiver menções
                    equipe_id = message.author.id if mencoes else None

                    # Inscrever autor
                    participante = InscricaoEventoParticipante(
                        inscricao_id=inscricao.id,
                        user_id=message.author.id,
                        user_name=message.author.name,
                        equipe_id=equipe_id
                    )
                    session.add(participante)
                    session.commit()

                    # Processar menções para adicionar à equipe
                    for mencionado in mencoes:
                        # Verificar se mencionado já está inscrito
                        mencionado_inscrito = session.query(InscricaoEventoParticipante).filter_by(
                            inscricao_id=inscricao.id,
                            user_id=mencionado.id
                        ).first()

                        if mencionado_inscrito:
                            # Se já está em outra equipe, não pode
                            if mencionado_inscrito.equipe_id and mencionado_inscrito.equipe_id != equipe_id:
                                continue
                            # Adicionar à equipe do autor
                            mencionado_inscrito.equipe_id = equipe_id
                            session.commit()
                        else:
                            # Registrar mencionado no bot se necessário
                            user_db = session.query(Users).filter_by(discord_id=mencionado.id).first()
                            if not user_db:
                                add_user = Users(mencionado.id, mencionado.name, 0, message.guild.id)
                                session.add(add_user)
                                session.commit()

                            # Verificar restrição de MMR para eventos fechados
                            if inscricao.tipo_evento in ["f", "fechado"]:
                                user_db = session.query(Users).filter_by(discord_id=mencionado.id).first()
                                guild_config = session.query(Guild_Config).filter_by(guild_id=message.guild.id).first()
                                if guild_config and user_db.MRR < guild_config.match_close_count:
                                    continue  # MMR insuficiente - não adiciona

                            # Inscrever mencionado na equipe
                            participante = InscricaoEventoParticipante(
                                inscricao_id=inscricao.id,
                                user_id=mencionado.id,
                                user_name=mencionado.name,
                                equipe_id=equipe_id
                            )
                            session.add(participante)
                            session.commit()
        except Exception as e:
            print(f"Erro na inscrição via mensagem: {e}")

    # Processar comandos normalmente
    await bot.process_commands(message)

@bot.command()
async def sync(ctx: commands.Context):
    if ctx.author.id == config_bot.OWNER_ID:
        s = await bot.tree.sync()
        e = discord.Embed(
            title=f"Comandos sincronizados: {len(s)} com sucesso",
            color=discord.Color.green()
        )
        await ctx.reply(embed=e)

@bot.command()
async def clearsync(ctx: commands.Context):
    if ctx.author.id == config_bot.OWNER_ID:
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        s = await bot.tree.sync()
        e = discord.Embed(
            title=f"Comandos limpos e re-sincronizados: {len(s)}",
            color=discord.Color.green()
        )
        await ctx.reply(embed=e)

@bot.command()
async def teste(ctx: commands.Context):
    if ctx.author.id == config_bot.OWNER_ID:
        user = bot.get_user(config_bot.OWNER_ID)
        members = [member async for member in ctx.guild.fetch_members(limit=4)]
        for member in members:
            user_db = db.session.query(db.Users).filter_by(discord_id=member.id).first()
            if not user_db:
                add_user = db.Users(member.id, member.name, 0, ctx.guild.id)
                db.session.add(add_user)
                db.session.commit()
            add = db.MatchParticipantes(member.id, member.name, user.id)
            db.session.add(add)
            db.session.commit()

@bot.command()
async def migrate(ctx: commands.Context):
    """Comando para executar migração do banco de dados"""
    if ctx.author.id == config_bot.OWNER_ID:
        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()

            migracoes_aplicadas = []
            migracoes_desnecessarias = []

            # Verificar colunas existentes
            cursor.execute("PRAGMA table_info(GuildConfig)")
            columns = [column[1] for column in cursor.fetchall()]

            # Migração 1: Adicionar coluna bdf_role_id
            if 'bdf_role_id' not in columns:
                cursor.execute("ALTER TABLE GuildConfig ADD COLUMN bdf_role_id INTEGER")
                conn.commit()
                migracoes_aplicadas.append("✅ Coluna `bdf_role_id` adicionada à GuildConfig")
            else:
                migracoes_desnecessarias.append("Coluna `bdf_role_id` já existe")

            # Migração 2: Adicionar coluna ranqueada_channel_id
            if 'ranqueada_channel_id' not in columns:
                cursor.execute("ALTER TABLE GuildConfig ADD COLUMN ranqueada_channel_id INTEGER")
                conn.commit()
                migracoes_aplicadas.append("✅ Coluna `ranqueada_channel_id` adicionada à GuildConfig")
            else:
                migracoes_desnecessarias.append("Coluna `ranqueada_channel_id` já existe")

            # Migração 3: Adicionar coluna ranqueada_inscricao_channel_id
            if 'ranqueada_inscricao_channel_id' not in columns:
                cursor.execute("ALTER TABLE GuildConfig ADD COLUMN ranqueada_inscricao_channel_id INTEGER")
                conn.commit()
                migracoes_aplicadas.append("✅ Coluna `ranqueada_inscricao_channel_id` adicionada à GuildConfig")
            else:
                migracoes_desnecessarias.append("Coluna `ranqueada_inscricao_channel_id` já existe")

            # Migração 4: Adicionar coluna ranqueada_confronto_channel_id
            if 'ranqueada_confronto_channel_id' not in columns:
                cursor.execute("ALTER TABLE GuildConfig ADD COLUMN ranqueada_confronto_channel_id INTEGER")
                conn.commit()
                migracoes_aplicadas.append("✅ Coluna `ranqueada_confronto_channel_id` adicionada à GuildConfig")
            else:
                migracoes_desnecessarias.append("Coluna `ranqueada_confronto_channel_id` já existe")

            # Migração 5: Criar tabela ConstantesK
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ConstantesK'")
            tabela_existe = cursor.fetchone()

            if not tabela_existe:
                cursor.execute("""
                    CREATE TABLE ConstantesK (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        k_ranqueada INTEGER DEFAULT 5,
                        k_aberto INTEGER DEFAULT 20,
                        k_fechado INTEGER DEFAULT 40,
                        k_bdf INTEGER DEFAULT 100
                    )
                """)
                conn.commit()
                migracoes_aplicadas.append("✅ Tabela `ConstantesK` criada com sucesso")
            else:
                migracoes_desnecessarias.append("Tabela `ConstantesK` já existe")

            # Migração 6: Adicionar colunas de permissão para ranqueadas por formato
            if 'ranqueada_perm_1x1_role_id' not in columns:
                cursor.execute("ALTER TABLE GuildConfig ADD COLUMN ranqueada_perm_1x1_role_id INTEGER")
                conn.commit()
                migracoes_aplicadas.append("✅ Coluna `ranqueada_perm_1x1_role_id` adicionada à GuildConfig")
            else:
                migracoes_desnecessarias.append("Coluna `ranqueada_perm_1x1_role_id` já existe")

            if 'ranqueada_perm_2x2_role_id' not in columns:
                cursor.execute("ALTER TABLE GuildConfig ADD COLUMN ranqueada_perm_2x2_role_id INTEGER")
                conn.commit()
                migracoes_aplicadas.append("✅ Coluna `ranqueada_perm_2x2_role_id` adicionada à GuildConfig")
            else:
                migracoes_desnecessarias.append("Coluna `ranqueada_perm_2x2_role_id` já existe")

            if 'ranqueada_perm_3x3_role_id' not in columns:
                cursor.execute("ALTER TABLE GuildConfig ADD COLUMN ranqueada_perm_3x3_role_id INTEGER")
                conn.commit()
                migracoes_aplicadas.append("✅ Coluna `ranqueada_perm_3x3_role_id` adicionada à GuildConfig")
            else:
                migracoes_desnecessarias.append("Coluna `ranqueada_perm_3x3_role_id` já existe")

            # Migração 7: Adicionar colunas de canais de estatísticas
            if 'organizador_ranqueada_stats_channel_id' not in columns:
                cursor.execute("ALTER TABLE GuildConfig ADD COLUMN organizador_ranqueada_stats_channel_id INTEGER")
                conn.commit()
                migracoes_aplicadas.append("✅ Coluna `organizador_ranqueada_stats_channel_id` adicionada à GuildConfig")
            else:
                migracoes_desnecessarias.append("Coluna `organizador_ranqueada_stats_channel_id` já existe")

            if 'organizador_evento_stats_channel_id' not in columns:
                cursor.execute("ALTER TABLE GuildConfig ADD COLUMN organizador_evento_stats_channel_id INTEGER")
                conn.commit()
                migracoes_aplicadas.append("✅ Coluna `organizador_evento_stats_channel_id` adicionada à GuildConfig")
            else:
                migracoes_desnecessarias.append("Coluna `organizador_evento_stats_channel_id` já existe")

            if 'jurado_stats_channel_id' not in columns:
                cursor.execute("ALTER TABLE GuildConfig ADD COLUMN jurado_stats_channel_id INTEGER")
                conn.commit()
                migracoes_aplicadas.append("✅ Coluna `jurado_stats_channel_id` adicionada à GuildConfig")
            else:
                migracoes_desnecessarias.append("Coluna `jurado_stats_channel_id` já existe")

            # Migração 8: Criar tabela OrganizadorContador
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='OrganizadorContador'")
            tabela_org_existe = cursor.fetchone()

            if not tabela_org_existe:
                cursor.execute("""
                    CREATE TABLE OrganizadorContador (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        contador_ranqueada INTEGER DEFAULT 0,
                        contador_evento INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
                migracoes_aplicadas.append("✅ Tabela `OrganizadorContador` criada com sucesso")
            else:
                migracoes_desnecessarias.append("Tabela `OrganizadorContador` já existe")

            # Migração 9: Criar tabela JuradoContador
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='JuradoContador'")
            tabela_jur_existe = cursor.fetchone()

            if not tabela_jur_existe:
                cursor.execute("""
                    CREATE TABLE JuradoContador (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        contador_ranqueada INTEGER DEFAULT 0,
                        contador_evento INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
                migracoes_aplicadas.append("✅ Tabela `JuradoContador` criada com sucesso")
            else:
                migracoes_desnecessarias.append("Tabela `JuradoContador` já existe")

            # Migração 10: Criar tabela InscricaoEvento
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='InscricaoEvento'")
            tabela_inscricao_existe = cursor.fetchone()

            if not tabela_inscricao_existe:
                cursor.execute("""
                    CREATE TABLE InscricaoEvento (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        guild_id INTEGER NOT NULL,
                        channel_id INTEGER NOT NULL,
                        message_id INTEGER UNIQUE NOT NULL,
                        autor_id INTEGER NOT NULL,
                        formato TEXT,
                        vagas INTEGER,
                        tipo_evento TEXT,
                        modo_sorteio TEXT,
                        ativo BOOLEAN DEFAULT 1
                    )
                """)
                conn.commit()
                migracoes_aplicadas.append("✅ Tabela `InscricaoEvento` criada com sucesso")
            else:
                migracoes_desnecessarias.append("Tabela `InscricaoEvento` já existe")

            # Migração 11: Criar tabela InscricaoEventoParticipante
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='InscricaoEventoParticipante'")
            tabela_participante_existe = cursor.fetchone()

            if not tabela_participante_existe:
                cursor.execute("""
                    CREATE TABLE InscricaoEventoParticipante (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        inscricao_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        user_name TEXT,
                        equipe_id INTEGER
                    )
                """)
                conn.commit()
                migracoes_aplicadas.append("✅ Tabela `InscricaoEventoParticipante` criada com sucesso")
            else:
                migracoes_desnecessarias.append("Tabela `InscricaoEventoParticipante` já existe")

            # Migração 12: Adicionar coluna equipe_id em InscricaoEventoParticipante
            cursor.execute("PRAGMA table_info(InscricaoEventoParticipante)")
            columns_participante = [column[1] for column in cursor.fetchall()]

            if 'equipe_id' not in columns_participante:
                cursor.execute("ALTER TABLE InscricaoEventoParticipante ADD COLUMN equipe_id INTEGER")
                conn.commit()
                migracoes_aplicadas.append("✅ Coluna `equipe_id` adicionada à InscricaoEventoParticipante")
            else:
                migracoes_desnecessarias.append("Coluna `equipe_id` já existe em InscricaoEventoParticipante")

            conn.close()

            # Criar embed de resultado
            if migracoes_aplicadas:
                e = discord.Embed(
                    title="✅ Migrações concluídas!",
                    description="\n".join(migracoes_aplicadas),
                    color=discord.Color.green()
                )
                if migracoes_desnecessarias:
                    e.add_field(name="⚠️ Já existentes", value="\n".join(migracoes_desnecessarias), inline=False)
            else:
                e = discord.Embed(
                    title="⚠️ Migrações desnecessárias",
                    description="Todas as migrações já foram aplicadas:\n" + "\n".join(migracoes_desnecessarias),
                    color=discord.Color.orange()
                )

            await ctx.reply(embed=e)

        except Exception as ex:
            e = discord.Embed(
                title="❌ Erro na migração",
                description=f"```{str(ex)}```",
                color=discord.Color.red()
            )
            await ctx.reply(embed=e)

bot.run(config_bot.TOKEN)
