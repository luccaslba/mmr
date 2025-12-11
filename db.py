from sqlalchemy import create_engine, Column, String, Integer, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

db = create_engine("sqlite:///database.db")
Session = sessionmaker(bind=db)
session = Session()

Base = declarative_base()

class Users(Base):
    __tablename__ = "Users"

    id = Column("id", Integer, primary_key=True)
    discord_id = Column("discord_id", Integer)
    discord_name = Column("discord_name", String)
    MRR = Column("MRR", Integer)
    guild_id = Column("guild_id", Integer)

    def __init__(self, discord_id, discord_name, MRR, guild_id):
        self.discord_id = discord_id
        self.discord_name = discord_name
        self.MRR = MRR
        self.guild_id = guild_id

class Guild_Config(Base):
    __tablename__ = "GuildConfig"

    id = Column("id", Integer, primary_key=True)
    guild_id = Column("guild_id", Integer)
    guild_name = Column("guild_name", String)
    mrr_channel_id = Column("mrr_channel_id", Integer)
    matchmaking_channel_id = Column("matchmaking_channel_id", Integer)
    confronto_channel_id = Column("confronto_channel_id", Integer)
    perm_cmd_role_id = Column("perm_cmd_role_id", Integer)
    match_close_count = Column("match_close_count", Integer)
    bdf_role_id = Column("bdf_role_id", Integer, nullable=True)
    ranqueada_channel_id = Column("ranqueada_channel_id", Integer, nullable=True)

    def __init__(self, guild_id, guild_name, mrr_channel_id, matchmaking_channel_id, perm_cmd_role_id, match_close_count, confronto_channel_id, bdf_role_id=None, ranqueada_channel_id=None):
        self.guild_id = guild_id
        self.guild_name = guild_name
        self.mrr_channel_id = mrr_channel_id
        self.matchmaking_channel_id = matchmaking_channel_id
        self.perm_cmd_role_id = perm_cmd_role_id
        self.match_close_count = match_close_count
        self.confronto_channel_id = confronto_channel_id
        self.bdf_role_id = bdf_role_id
        self.ranqueada_channel_id = ranqueada_channel_id

class CloseMatchMember(Base):
    __tablename__ = "CloseMatchMember"

    id = Column(Integer, primary_key=True)
    player_pos = Column(Integer)
    discord_id = Column(Integer)
    discord_name = Column(String)
    autor_id = Column(Integer)
    equipe_id = Column(Integer)

    def __init__(self, discord_id, discord_name, autor_id, player_pos, equipe_id):
        self.discord_id = discord_id
        self.discord_name = discord_name
        self.autor_id = autor_id
        self.player_pos = player_pos
        self.equipe_id = equipe_id

class MatchParticipantes(Base):
    __tablename__ = "MatchParticipantes"

    id = Column(Integer, primary_key=True)
    discord_id = Column(Integer)
    discord_name = Column(String)
    autor_id = Column(Integer)

    def __init__(self, discord_id, discord_name, autor_id):
        self.discord_id = discord_id
        self.discord_name = discord_name
        self.autor_id = autor_id

class MatchPartidaParticipantes(Base):
    __tablename__ = "MatchPartidaParticipantes"

    id = Column(Integer, primary_key=True)
    discord_id = Column(Integer)
    discord_name = Column(String)
    autor_id = Column(Integer)
    equipe_id = Column(Integer)
    player_pos = Column(Integer)

    def __init__(self, discord_id, discord_name, autor_id, player_pos, equipe_id):
        self.discord_id = discord_id
        self.discord_name = discord_name
        self.autor_id = autor_id
        self.player_pos = player_pos
        self.equipe_id = equipe_id

class RolesMMR(Base):
    __tablename__ = "RolesMMR"

    id = Column(Integer, primary_key=True)
    role_name = Column(String)
    role_id = Column(Integer)
    MRR = Column(String)

    def __init__(self, role_name, role_id, MRR):
        self.role_name = role_name
        self.role_id = role_id
        self.MRR = MRR

class RolesVips(Base):
    __tablename__ = "RolesVips"

    id = Column(Integer, primary_key=True)
    role_name = Column(String)
    role_id = Column(Integer)
    peso = Column(String)

    def __init__(self, role_name, role_id, peso):
        self.role_name = role_name
        self.role_id = role_id
        self.peso = peso

class ConstantesK(Base):
    __tablename__ = "ConstantesK"

    id = Column(Integer, primary_key=True)
    guild_id = Column(Integer)
    k_ranqueada = Column(Integer, default=5)
    k_aberto = Column(Integer, default=20)
    k_fechado = Column(Integer, default=40)
    k_bdf = Column(Integer, default=100)

    def __init__(self, guild_id, k_ranqueada=5, k_aberto=20, k_fechado=40, k_bdf=100):
        self.guild_id = guild_id
        self.k_ranqueada = k_ranqueada
        self.k_aberto = k_aberto
        self.k_fechado = k_fechado
        self.k_bdf = k_bdf

Base.metadata.create_all(bind=db)