import discord, config_bot, os, db, functions
from discord.ext import commands
from discord.ext.commands import Bot
from db import MatchParticipantes
from ui.buttons.start_matchmaking import StartMatchMakingV2
from ui.buttons.finalizar_matchmaking import FinalizarMatchmaking

bot = Bot(command_prefix=config_bot.PREFIX, intents=discord.Intents.all())

async def load_commands():
    for filename in os.listdir("commands"):
        if filename.endswith(".py") and not filename.startswith("_"):
            await bot.load_extension(f"commands.{filename[:-3]}")
            print(f"🔧 comandos carregados: {filename}")


@bot.event
async def on_ready():
    print("Bot online: ", bot.user)
    bot.add_view(StartMatchMakingV2(bot))
    user = bot.get_user(config_bot.OWNER_ID)
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
        import sqlite3

        try:
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()

            # Verificar se a coluna já existe
            cursor.execute("PRAGMA table_info(GuildConfig)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'bdf_role_id' not in columns:
                cursor.execute("ALTER TABLE GuildConfig ADD COLUMN bdf_role_id INTEGER")
                conn.commit()
                e = discord.Embed(
                    title="✅ Migração concluída!",
                    description="Coluna `bdf_role_id` adicionada com sucesso.",
                    color=discord.Color.green()
                )
            else:
                e = discord.Embed(
                    title="⚠️ Migração desnecessária",
                    description="Coluna `bdf_role_id` já existe no banco de dados.",
                    color=discord.Color.orange()
                )

            conn.close()
            await ctx.reply(embed=e)

        except Exception as ex:
            e = discord.Embed(
                title="❌ Erro na migração",
                description=f"```{str(ex)}```",
                color=discord.Color.red()
            )
            await ctx.reply(embed=e)

bot.run(config_bot.TOKEN)
