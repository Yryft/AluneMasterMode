import json
import nextcord
import sqlite3
import time
from core import client
from datetime import datetime
from nextcord.ext import tasks
from tasks import update_roles_and_nicknames, add_all_members
from tasks.users.update_user import on_member_join, on_member_remove, on_member_update

# Load the JSON file
with open("core/secret.json", "r") as file:
    secrets = json.load(file)

with open("utils/IDs.json", "r") as file:
    IDs = json.load(file)
    GUILD_ID = IDs["GUILD_ID"]

@tasks.loop(minutes=30)
async def update_roles_and_nicknames_periodically():
    start_time = time.perf_counter()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Running scheduled role and nickname update...\n\n")
    for member in client.get_guild(GUILD_ID).members:
        if member.bot or member == member.guild.owner:
            continue
        await update_roles_and_nicknames(member)
    end_time = time.perf_counter()
    duration = end_time - start_time
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Finished in {duration:.2f} seconds.")
    
@client.event
async def on_ready():
    conn = sqlite3.connect("utils/database/players.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            discord_id INTEGER PRIMARY KEY,
            ign TEXT NOT NULL,
            uuid TEXT NOT NULL,
            profile INTEGER
        )
    """)
    try:
        c.execute("ALTER TABLE players ADD COLUMN profile INTEGER DEFAULT NULL")
        print("Column 'profile' added as nullable.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            pass
            
    conn.commit()
    conn.close()
    print(f"Connected as {client.user}\n\n")
    await client.wait_until_ready()
    if not update_roles_and_nicknames_periodically.is_running():
        update_roles_and_nicknames_periodically.start()
        print("Started the periodic role and nickname update loop.")

client.run(secrets["TOKEN"])