import sqlite3

def upsert_player(discord_id: int, ign: str, uuid: str):
    conn = sqlite3.connect("utils/database/players.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO players (discord_id, ign, uuid, profile)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(discord_id) DO UPDATE SET ign=excluded.ign, uuid=excluded.uuid, profile=excluded.profile
    """, (discord_id, ign, uuid))
    conn.commit()
    conn.close()

def get_all_players():
    conn = sqlite3.connect("utils/database/players.db")
    c = conn.cursor()
    c.execute("SELECT discord_id, ign, uuid, profile FROM players")
    players = c.fetchall()
    conn.close()
    return players

def get_player_by_discord_id(discord_id: int):
    conn = sqlite3.connect("utils/database/players.db")
    c = conn.cursor()
    c.execute("SELECT discord_id, ign, uuid, profile FROM players WHERE discord_id = ?", (discord_id,))
    player = c.fetchone()
    conn.close()
    return player

def update_ign(discord_id: int, new_ign: str):
    conn = sqlite3.connect("utils/database/players.db")
    c = conn.cursor()
    c.execute("UPDATE players SET ign = ? WHERE discord_id = ?", (new_ign, discord_id))
    conn.commit()
    conn.close()
    
def update_profile(discord_id: int, profile_index: str):
    conn = sqlite3.connect("utils/database/players.db")
    c = conn.cursor()
    c.execute("UPDATE players SET profile = ? WHERE discord_id = ?", (profile_index, discord_id))
    conn.commit()
    conn.close()
    
def update_uuid(discord_id: int, new_uuid: str):
    conn = sqlite3.connect("utils/database/players.db")
    c = conn.cursor()
    c.execute("UPDATE players SET uuid = ? WHERE discord_id = ?", (new_uuid, discord_id))
    conn.commit()
    conn.close()   
     
def delete_player(discord_id: int):
    conn = sqlite3.connect("utils/database/players.db")
    c = conn.cursor()
    c.execute("DELETE FROM players WHERE discord_id = ?", (discord_id,))
    conn.commit()
    conn.close()

