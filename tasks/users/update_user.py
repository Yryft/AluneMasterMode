import nextcord
import json
from core import client
from .db import upsert_player, delete_player, get_player_by_discord_id, update_uuid, update_ign
from tasks.catacombs_handler.catacombs_handler import get_IGN, get_uuid, update_roles_and_nicknames

ID_index = 0
IGN_index = 1
UUID_index = 2
PROFILE_index = 3

with open("utils/IDs.json", "r") as file:
    IDs = json.load(file)
    ADMIN_CHANNEL = IDs["ADMIN_CHANNEL"]
                        
@client.event
async def on_member_join(member: nextcord.Member):
    IGN = await get_IGN(member)

    if IGN:  # simple sanity check
        upsert_player(member.id, IGN, 0)
        print(f"Added {IGN} (ID: {member.id}) to database with null UUID.")
    else:
        print(f"Failed to extract IGN for user {member.id}")
    
@client.event
async def on_member_remove(member: nextcord.Member):
    delete_player(member.id)
    IGN = await get_IGN(member)
    print(f"Deleted {IGN} (ID: {member.id}) from database.")
    channel = client.get_channel(ADMIN_CHANNEL)
    user = await client.fetch_user(member.id)
    
    if channel:
        # Fetch the audit logs
        audit_logs = await member.guild.audit_logs(limit=1).flatten()
        
        # Check for kick entry
        if audit_logs:
            leave_entry = audit_logs[0]
            if leave_entry.action == nextcord.AuditLogAction.kick and leave_entry.target.id == member.id:
                reason = leave_entry.reason if leave_entry.reason else "No reason provided."
                await channel.send(f"<@&1346530010948702289><@&1350409195878486059>\nUser  {user.mention} was kicked by {leave_entry.user.mention}. Reason :{reason}")
                return
            elif leave_entry.action == nextcord.AuditLogAction.ban and leave_entry.target.id == member.id:
                reason = leave_entry.reason if leave_entry.reason else "No reason provided."
                await channel.send(f"<@&1346530010948702289><@&1350409195878486059>\nUser  {user.mention} was banned by {leave_entry.user.mention}. Reason :{reason}")
                return
        await channel.send(f"<@&1346530010948702289><@&1350409195878486059>\nUser  {user.mention} has left the server.")
        
@client.event
async def on_member_update(before: nextcord.Member, after: nextcord.Member):
    async for entry in after.guild.audit_logs(limit=2, action=nextcord.AuditLogAction.member_update):
        if entry.target.id == after.id:
                if entry.user is None or entry.user.id != client.user.id:
                    IGN = await get_IGN(after)
                    update_ign(after.id, IGN)
                    print(f"Updated IGN for {await get_IGN(before)} (ID: {after.id}) to {get_player_by_discord_id(after.id)[IGN_index]}.")
                    uuid = get_player_by_discord_id(after.id)[UUID_index]
                    if uuid == "0":
                        uuid = await get_uuid(IGN)
                        if uuid:
                            update_uuid(after.id, uuid)
                            print(f"Updated UUID for {IGN} (ID: {after.id}) to {uuid}.")
                            await update_roles_and_nicknames(after)
                        else:
                            print(f"Failed to update UUID for {IGN} (ID: {after.id})")
                    else:
                        await update_roles_and_nicknames(after)