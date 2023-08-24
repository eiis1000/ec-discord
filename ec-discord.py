# bot.py
import os

import discord
from discord.ext import commands
import time
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA1
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Protocol.SecretSharing import Shamir
from Crypto.Util import Padding
import binascii
import asyncio
import base64
import sys
import re
import traceback
# from dotenv import load_dotenv

# load_dotenv()
# TOKEN = os.getenv('DISCORD_TOKEN')

TOKEN = None
tokenfile = '.token'
if len(sys.argv) > 1:
    tokenfile = sys.argv[1] + '.token'
with open(tokenfile, 'r') as f:
    TOKEN = f.read().strip()

ch_n2id = {
    'bot-commands': 1141934815566905424,
    'resident-commands': 1142305167719530547,
    'admin-commands': 1141934946404012143,
}
ch_id2ch = {id: None for id in ch_n2id.values()}

allowed_selfroles = ["'27", "'26", "'25", "'24", "'23", "cruft",
                    'baker', 'burton-conner', 'macgregor', 'maseeh', 'mccormick',
                    'new-house', 'next', 'new-vassar', 'random', 'simmons', 'fsilg', 'grad-housing']

flags = {}
maintainer = 452902745066831903 # erez
start_time = time.ctime() 

intents = discord.Intents._from_value(3276541)

# client = discord.Client(intents=intents)
bot = commands.Bot(command_prefix='!', intents=intents)


def shorthash(s):
    h = SHA1.new()
    h.update(s.encode('utf-8'))
    return h.hexdigest()[:5]

def to_bytes(x: int) -> bytes:
    return x.to_bytes((x.bit_length() + 7) // 8, 'big')
    
def from_bytes(xbytes: bytes) -> int:
    return int.from_bytes(xbytes, 'big')

def hexit(x: int) -> str:
    return binascii.hexlify(to_bytes(x)).decode('utf-8')

def unhexit(x: str) -> int:
    return from_bytes(binascii.unhexlify(x.encode('utf-8')))

def hall_roles():
    guild = bot.guilds[0]
    return set(r for r in guild.roles if re.match(r'.*\(\d[EW]\)$', r.name))

def all_roles():
    guild = bot.guilds[0]
    return set(r for r in guild.roles)

def get_role(name):
    guild = bot.guilds[0]
    return discord.utils.get(guild.roles, name=name)

def nicelist(l):
    return ', '.join(l)


@bot.event
async def on_ready():
    print(f'Connected on {start_time} with intents {bot.intents}.')
    for guild in bot.guilds:
        await on_guild_join(guild)
    assert len(bot.guilds) == 1
    global ch_n2id
    global ch_id2ch
    for ch_id in ch_n2id.values():
        ch_id2ch[ch_id] = bot.get_channel(ch_id)
        
@bot.event
async def on_guild_join(guild):
    print(f'joined {guild.name}')


@bot.event
async def on_message(message):
    global prev_msg
    prev_msg = message
    if message.author.bot:
        return
    if message.author.id == maintainer:
        if 'my son' in message.content.lower():
            await message.channel.send('yes father')
        if message.content.lower() in ['!version', 'version', 'pbv']:
            await message.channel.send('0.1.4')
        if message.content.lower() in ['!reboot', 'reboot', 'kys']:
            await message.channel.send('okay :(')
            try:
                await bot.close()
                print("committed suicide")
            except:
                exit(0)
    await bot.process_commands(message)


@bot.command(help="Gives a user the verified role.")
async def manualverify(ctx):
    if ctx.message.channel.id not in ch_id2ch:
        await ctx.send(f"This is not a valid bot commands channel. Please issue commands in one of {nicelist(ch_n2id.keys())}.")
        return
    if not (set([get_role('hall-chair'), get_role('moderator')]) & set(ctx.message.author.roles)):
        await ctx.send(f"Only hall chairs and moderators can manually verify users.")
        return
    
    mentions = ctx.message.mentions
    if len(mentions) != 1:
        await ctx.send(f"You must mention (tag with the @ symbol) exactly one user to assign the roles to.")
        return
    
    user = mentions[0]
    await user.add_roles(get_role('verified'))
    await ctx.send(f"Granted verified role to {user.mention}. \nIf you'd like to undo this or add different/multiple hall roles, contact a moderator.")


@bot.command(help="Gives you the specified role.")
async def selfrole(ctx, role_str=None):
    global allowed_selfroles
    if ctx.message.channel.id not in ch_id2ch:
        await ctx.send(f"This is not a valid bot commands channel. Please issue commands in one of {nicelist(ch_n2id.keys())}.")
        return
    if get_role('verified') not in ctx.message.author.roles:
        await ctx.send(f"You haven't yet verified your MIT email. First acquire the `verified` role, then try again.")
        return
    if not role_str:
        await ctx.send(f"Please name a role to add. Allowed selfroles are {nicelist(allowed_selfroles)}.")
        return
    
    if len(ctx.message.role_mentions) > 0:
        await ctx.send("Please do not mention your desired role - just enter its name :)")
        return
    
    role_str = role_str.replace("‘", "'")
    if "'" + role_str in allowed_selfroles:
        role_str = "'" + role_str
    if len(role_str) > 2 and "'" + role_str[2:] in allowed_selfroles:
        role_str = "'" + role_str[2:] # for when people do 2027 instead of '27
    if role_str.lower() in allowed_selfroles:
        role_str = role_str.lower()
    rq_role = get_role(role_str)
    if rq_role is None:
        await ctx.send(f"{role_str.replace('@','')} is not a valid role. Allowed selfroles are {nicelist(allowed_selfroles)}.")
        return
    elif role_str not in allowed_selfroles:
        await ctx.send(f"{role_str.replace('@','')} is not an allowed selfrole. Allowed selfroles are {nicelist(allowed_selfroles)}.")
        return 
    
    if rq_role in ctx.message.author.roles:
        await ctx.message.author.remove_roles(rq_role)
        await ctx.send(f"Removed {rq_role} from {ctx.message.author.mention}.")
    else:
        await ctx.message.author.add_roles(rq_role)
        await ctx.send(f"Added {rq_role} to {ctx.message.author.mention}.")


@bot.command(hidden=True)
async def addaffiliated(ctx):
    await addaffiliate(ctx)

@bot.command(help="Grants ec-affiliated and your hall role.")
async def addaffiliate(ctx):
    if ctx.message.channel.id not in ch_id2ch:
        await ctx.send(f"This is not a valid bot commands channel. Please issue commands in one of {nicelist(ch_n2id.keys())}.")
        return
    if get_role('ec-resident') not in ctx.message.author.roles:
        await ctx.send(f"Only EC residents can add new EC affiliates.")
        return

    caller_hall_role_set = set(ctx.message.author.roles) & hall_roles()
    if len(caller_hall_role_set) != 1:
        await ctx.send(f"You have {len(caller_hall_role_set)} hall roles, which is very confusing to joeg. Please contact a {get_role('moderator').mention} for manual resolution.")
        return
    caller_hall_role = caller_hall_role_set.pop()
    
    mentions = ctx.message.mentions
    if len(mentions) != 1:
        await ctx.send(f"You must mention (tag with the @ symbol) exactly one user to assign the roles to.")
        return
    
    user = mentions[0]
    if get_role('verified') not in user.roles:
        await ctx.send(f"{user.mention} hasn't yet verified their MIT email. Ask them to first acquire the `verified` role via `!verify`, then try again.")
        return

    await user.add_roles(get_role('ec-affiliated'))
    await user.add_roles(caller_hall_role)
    await ctx.send(f"Granted ec-affiliated and {caller_hall_role.name[-3:-1]} roles to {user.mention}. \nIf you'd like to undo this or add different/multiple hall roles, contact a moderator.")


@bot.command(help="Grants ec-resident and your hall role.")
async def addresident(ctx):
    if ctx.message.channel.id not in ch_id2ch:
        await ctx.send(f"This is not a valid bot commands channel. Please issue commands in one of {nicelist(ch_n2id.keys())}.")
        return
    if not (set([get_role('hall-chair'), get_role('moderator'), get_role('hall-moderator')]) & set(ctx.message.author.roles)):
        await ctx.send(f"Only hall chairs, hall moderators, and server moderators can add new EC residents.")
        return

    caller_hall_role_set = set(ctx.message.author.roles) & hall_roles()
    if len(caller_hall_role_set) != 1:
        await ctx.send(f"You have {len(caller_hall_role_set)} hall roles, which is very confusing to joeg. Please contact a {get_role('moderator').mention} for manual resolution.")
        return
    caller_hall_role = caller_hall_role_set.pop()
    
    mentions = ctx.message.mentions
    if len(mentions) != 1:
        await ctx.send(f"You must mention exactly one user to assign the roles to.")
        return
    
    user = mentions[0]
    if get_role('verified') not in user.roles:
        await ctx.send(f"{user.mention} hasn't yet verified their MIT email. Ask them to first acquire the `verified` role via `!verify`, then try again.")
        return

    await user.add_roles(get_role('ec-affiliated'))
    await user.add_roles(get_role('ec-resident'))
    await user.add_roles(caller_hall_role)
    await ctx.send(f"Granted ec-affiliated, ec-resident, and {caller_hall_role.name[-3:-1]} roles to {user.mention}. \nIf you'd like to undo this or add different/multiple hall roles, contact a moderator.")    


@bot.command(help="Grants hall-moderator")
async def addhallmod(ctx):
    if ctx.message.channel.id not in ch_id2ch:
        await ctx.send(f"This is not a valid bot commands channel. Please issue commands in one of {nicelist(ch_n2id.keys())}.")
        return
    if not (set([get_role('hall-chair'), get_role('moderator')]) & set(ctx.message.author.roles)):
        await ctx.send(f"Only hall chairs and server moderators can add new hall moderators.")
        return

    caller_hall_role_set = set(ctx.message.author.roles) & hall_roles()
    if len(caller_hall_role_set) != 1:
        await ctx.send(f"You have {len(caller_hall_role_set)} hall roles, which is very confusing to joeg. Please contact a {get_role('moderator').mention} for manual resolution.")
        return
    caller_hall_role = caller_hall_role_set.pop()
    
    mentions = ctx.message.mentions
    if len(mentions) != 1:
        await ctx.send(f"You must mention exactly one user to assign the roles to.")
        return

    user = mentions[0]
    if get_role('verified') not in user.roles:
        await ctx.send(f"{user.mention} hasn't yet verified their MIT email. Ask them to first acquire the `verified` role via `!verify`, then try again.")
        return
    if get_role('ec-resident') not in user.roles:
        await ctx.send(f"Please use !addresident first.")
        return
    await user.add_roles(get_role('hall-moderator'))
    await ctx.send(f"Granted hall-moderator role to {user.mention}. \nIf you'd like to undo this, contact a moderator.")    

@bot.command(hidden=True)
async def bp(ctx):
    if ctx.message.author.id != maintainer:
        return
    await ctx.send("breakpoint executed")
    breakpoint()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    errstr = str(error)[:100] + "  ...  " + str(error)[-100:]
    await ctx.send(f"You've encountered an error: {errstr}")#\nPlease contact the administrator <@{maintainer}> with this information.")
    raise error


@bot.command(hidden=True)
async def tmp_hallmod(ctx):
    await manualverify(ctx)
    await asyncio.sleep(1)
    await addresident(ctx)
    await asyncio.sleep(1)
    await addhallmod(ctx)

bot.run(TOKEN)
