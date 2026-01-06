import discord, config_bot, os, db, functions, sqlite3
from discord.ext import commands
from discord.ext.commands import Bot
from db import MatchParticipantes
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
