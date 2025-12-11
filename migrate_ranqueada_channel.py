#!/usr/bin/env python3
"""
Script de migração para adicionar coluna ranqueada_channel_id na tabela GuildConfig
Execute este script UMA VEZ após fazer deploy da nova versão
"""

import sqlite3

def migrate():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Verificar se a coluna já existe
    cursor.execute("PRAGMA table_info(GuildConfig)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'ranqueada_channel_id' not in columns:
        print("Adicionando coluna ranqueada_channel_id...")
        cursor.execute("ALTER TABLE GuildConfig ADD COLUMN ranqueada_channel_id INTEGER")
        conn.commit()
        print("✅ Coluna ranqueada_channel_id adicionada com sucesso!")
    else:
        print("⚠️ Coluna ranqueada_channel_id já existe. Migração não necessária.")

    conn.close()

if __name__ == "__main__":
    migrate()
