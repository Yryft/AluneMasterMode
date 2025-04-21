import nextcord
import aiohttp
import math
import json
import asyncio
import mojang
import re
from nextcord import Interaction
from core import client
from tasks.users.db import get_player_by_discord_id, update_uuid, upsert_player, update_profile

ID_index = 0
IGN_index = 1
UUID_index = 2
PROFILE_index = 3

with open("core/secret.json", "r") as file:
    secrets = json.load(file)
    HYPIXEL_API_KEY = secrets["HYPIXEL_API_KEY"]
    
with open("utils/links.json", "r") as file:
    links = json.load(file)
    HYPIXEL_API_URL = links["HYPIXEL_API_URL"]
    SKYCRYPT_URL = links["SKYCRYPT_URL"]

with open("utils/IDs.json", "r") as file:
    IDs = json.load(file)
    GUILD_ID = IDs["GUILD_ID"]
    ADMIN_CHANNEL = IDs["ADMIN_CHANNEL"]

async def get_uuid(IGN):
    max_retries = 3

    for attempt in range(1, max_retries + 1):
        try:
            uuid = mojang.API().get_uuid(IGN)
            return uuid
        except:
            if attempt < max_retries:
                await asyncio.sleep(2)
            else:
                print(f"User {IGN} doesn't have the right username after {max_retries} attempts.")
                return None
            
async def get_IGN(member: nextcord.Member):
    IGN = member.nick or member.global_name or member.display_name
    if re.match(r"^❮.*?❯", IGN):
        IGN = re.sub(r"^❮.*?❯", "", IGN)    
    return IGN

async def fetch_player_data(uuid):
    
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{HYPIXEL_API_URL}{HYPIXEL_API_KEY}&uuid={uuid}") as response:
            print(f"Hypixel API Response Code: {response.status}")
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                print(f"Error fetching Hypixel data for {uuid}: {error_text}")
            return None

async def calculate_lvl(xp):
    cata_lvl = {
        35: 13259640,
        40: 51559640,
        45: 177559640,
        50: 569809640
    }

    closest_level = max([level for level, xp_required in cata_lvl.items() if xp_required <= xp], default=None)
    
    return closest_level

def get_closest_cata_level(catacombs_xp):
    cata_lvl = {
        30: 3084640,
        31: 4149640,
        32: 5559640,
        33: 7459640,
        34: 9959640,
        35: 13259640,
        36: 17559640,
        37: 23159640,
        38: 30359640,
        39: 39559640,
        40: 51559640,
        41: 66559640,
        42: 85559640,
        43: 109559640,
        44: 139559640,
        45: 177559640,
        46: 225559640,
        47: 285559640,
        48: 360559640,
        49: 453559640,
        50: 569809640
    }
    if catacombs_xp < cata_lvl[30]:
        return None
    # Matches the closest inferior catacombs LvL for the user
    closest_level = max((lvl for lvl, xp in cata_lvl.items() if xp <= catacombs_xp), default=30)

    # Checks if LvL is above 50
    if catacombs_xp > cata_lvl[50]:
        extra_levels = (catacombs_xp - cata_lvl[50]) // 200_000_000
        closest_level = math.floor(min(50 + extra_levels, 100))

    return closest_level

async def update_profile_index(member: nextcord.Member, uuid: str, profile: list, profile_index):
    max_xp = -1  # Initialiser avec une valeur très basse
    max_xp_index = -1  # L'index du profil avec le plus d'XP

    for index, profiles in enumerate(profile):  # Utiliser `enumerate` pour avoir l'index
        try:
            skyblock_xp = profile[index]["members"][uuid]["leveling"]["experience"]
        except KeyError:
            continue
        
        # Comparer l'XP du profil actuel avec le maximum trouvé jusqu'à maintenant
        if skyblock_xp > max_xp:
            max_xp = skyblock_xp
            max_xp_index = index
    if profile_index != max_xp_index:
        update_profile(member.id, max_xp_index)
        print(f"Updated profile_index: {max_xp_index} - {profile[max_xp_index]["cute_name"]}")
    return max_xp_index

async def get_data(uuid, IGN, member: nextcord.Member, profile_index, anti_loop, data):
    count, last_id = anti_loop.get(member.id, (0, None))
    print(f"Retrying get_data for {IGN} (attempt {count + 1})")
    if count > 5 and last_id == member.id:
        anti_loop[member.id] = (0, member.id)
        last_uuid = uuid
        uuid = await get_uuid(IGN)
        if uuid and uuid != last_uuid:
            update_uuid(member.id, uuid)
            print(f"Updated UUID: {uuid}")
            anti_loop[member.id] = (count + 1, member.id)
            return await get_data(uuid, IGN, member, profile_index, anti_loop, None)
        print(f"Weird profile for {IGN}(Lower than 100 Sb Lvl)\n")
        channel = client.get_channel(ADMIN_CHANNEL)
        if channel:
            await channel.send(f"Weird profile found for {member.mention}\n{SKYCRYPT_URL}{IGN}")
        return
    else:
        if not data:
            if uuid == None or uuid == "0":
                uuid = await get_uuid(IGN)
                if uuid:
                    update_uuid(member.id, uuid)
                    print(f"Updated UUID: {uuid}")
                else:
                    print(f"Could not find UUID for {IGN}\n")
                    channel = client.get_channel(ADMIN_CHANNEL)
                    if channel:
                        await channel.send(f"{member.mention} doesn't have the right username!")
                    return
            data = await fetch_player_data(uuid)
        if data:
            profile = data.get("profiles")
            if not profile or profile_index >= len(profile):
                print(f"No valid profile at index {profile_index} for {IGN}\n")
                return
            skyblock_level = math.floor(profile[profile_index]["members"][uuid]["leveling"]["experience"]/100)
            print(f"Skyblock Level: {skyblock_level}")
            if skyblock_level < 100:
                print(f"Wrong index for {IGN} (ID: {member.id})- {profile_index} - {profile[profile_index]['cute_name']}\n")
                last_profile_index = profile_index
                profile_index = await update_profile_index(member, uuid, profile, profile_index)
                if last_profile_index != profile_index:
                    anti_loop[member.id] = (count + 1, member.id)
                    return await get_data(uuid, IGN, member, profile_index, anti_loop, data)
                return
            else:
                best_profile = profile[profile_index]["members"][uuid]
                print(f"Best profile for {IGN} (ID: {member.id})- {profile_index} - {profile[profile_index]['cute_name']}")
                return best_profile
        else:
            print(f"Could not retrieve data for {IGN}\n")
            channel = client.get_channel(ADMIN_CHANNEL)
            if channel:
                await channel.send(f"{member.mention} doesn't have the right username!(UUID not found on Hypixel API)")
            return

async def update_roles_and_nicknames(member: nextcord.Member):
    anti_loop = {}
    anti_loop[member.id] = (0, member.id)
    guild = client.get_guild(GUILD_ID)
    if not guild:
        print("Server not found!")
        return
    
    player_infos = get_player_by_discord_id(member.id)
    
    if player_infos:
        print(f"Found {player_infos[IGN_index]} (ID: {member.id}) in database with UUID: {player_infos[UUID_index]}")
        uuid = player_infos[UUID_index] if player_infos[UUID_index] != 0 else None
        username = player_infos[IGN_index]
        max_xp_index = player_infos[PROFILE_index]
    else:
        uuid = None
        username = await get_IGN(member)
        max_xp_index = None
        
    
    print(f"Processing {username}...")
    
    profile = await get_data(uuid, username, member, max_xp_index, anti_loop, None)
    if not profile:
        return

    try:
        catacombs_xp = profile["dungeons"]["dungeon_types"]["catacombs"]["experience"]
        archer_xp = profile["dungeons"]["player_classes"]["archer"]["experience"]
        berserk_xp = profile["dungeons"]["player_classes"]["berserk"]["experience"]
        healer_xp = profile["dungeons"]["player_classes"]["healer"]["experience"]
        mage_xp = profile["dungeons"]["player_classes"]["mage"]["experience"]
        tank_xp = profile["dungeons"]["player_classes"]["tank"]["experience"]
    except:
        return

    data = {
        "cata": catacombs_xp,
        "archer": archer_xp,
        "berserker": berserk_xp,
        "healer": healer_xp,
        "mage": mage_xp,
        "tank": tank_xp
    }
    
    catacombs_level = get_closest_cata_level(catacombs_xp)
    
    new_username = f"❮{catacombs_level}❯{username}"
    if len(new_username) <= 32 and catacombs_level != None:  
        await member.edit(nick=new_username)
        print(f"Updated nickname: {new_username}" if new_username != member.nick else f"No changes to nickname: {new_username}")
    else:
        await member.edit(nick=username)
        print(f"Failed to update nickname: {username}")
    
    role_name_list = []
    role_add_list = []
    role_remove_list = [] 
    current_roles = set(member.roles)
    for skill_name in data:
        xp = data[skill_name]
        skill_lvl = await calculate_lvl(xp)

        if skill_name == "cata" and skill_lvl == None:
            last_uuid = uuid
            uuid = await get_uuid(username)
            if uuid and uuid != last_uuid:
                update_uuid(member.id, uuid)
                print(f"Updated UUID: {uuid}")
                await update_roles_and_nicknames(member)
                return
            else:
                print(f"Low cata profile for {username}\n")
                channel = client.get_channel(ADMIN_CHANNEL)
                if channel:
                    await channel.send(f"Low cata profile found for {member.mention}\n{SKYCRYPT_URL}{username}")
                    return
                   
        if skill_lvl:
            role_name = f"{skill_name.capitalize()} - {skill_lvl}+" if skill_lvl < 50 else f"👑{skill_name.capitalize()} - 50"
            role = nextcord.utils.get(guild.roles, name=role_name)

            if role:
                role_name_list.append(f" (+ {role.name})")
                role_add_list.append(role)
                
            # Remove roles of lower levels for the same skill
            matching_roles = [role for role in current_roles if skill_name.capitalize() in role.name and role.name != skill_name.capitalize()]
            for role in matching_roles:
                try:   
                    role_level = int(role.name.split(" ")[-1].replace("+", ""))
                    if role_level < skill_lvl or role_level > skill_lvl:
                        role_name_list.append(f" (- {role.name})")
                        role_remove_list.append(role)
                except:
                    continue
        else:
            matching_roles = [role for role in current_roles if skill_name.capitalize() in role.name and role.name != skill_name.capitalize()]
            for role in matching_roles:
                role_remove_list.append(role)       
    await member.edit(roles=list(set(current_roles) - set(role_remove_list) | set(role_add_list)))
    print(f"Roles changed for {username}: {role_name_list}\n" if role_name_list and current_roles != set(member.roles) else f"No role changed for {username}\n")

# This goes where you register your commands (e.g., inside your Cog or directly if using bare client)
@client.slash_command(name="add_all_members", description="Add all server members to the database (admin only)")
async def add_all_members(interaction: Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You must be an administrator to use this command.", ephemeral=True)
        return

    await interaction.response.send_message("⏳ Adding members to the database...", ephemeral=True)

    added = 0
    skipped = 0

    for member in interaction.guild.members:
        if member.bot:
            continue

        IGN = await get_IGN(member)

        if IGN:
            upsert_player(member.id, IGN, 0)
            added += 1
        else:
            skipped += 1

    await interaction.followup.send(f"✅ Done! Added `{added}` members to the database. Skipped `{skipped}`.", ephemeral=True)
