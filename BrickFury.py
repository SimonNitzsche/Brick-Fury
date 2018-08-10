import discord
from discord.ext import commands
import sqlite3
import json
import time
import pytesseract
import io
import requests
import os
from PIL import Image, ImageEnhance, ImageFilter
import colorama
#from colorama import Fore, Style
colorama.init()

from functions import tracers

pytesseract.tesseract_cmd = 'C:\\Program Files (x86)\\Tesseract-OCR\\tesseract'

#description = '''A bot to protect against swearing and spam.'''
#bot = commands.Bot(command_prefix='.', description=description)

conn = sqlite3.connect('fury.sqlite')
fury = conn.cursor()

fury.execute('''CREATE TABLE IF NOT EXISTS rules
             (serverid bigint, rulenum tinyint, ruletext text)''') # RULES
fury.execute('''CREATE TABLE IF NOT EXISTS swear
             (serverid bigint, phrase text)''') # SWEAR
fury.execute('''CREATE TABLE IF NOT EXISTS swearexception
             (serverid bigint, phrase text)''') # SWEAR EXCEPTION
fury.execute('''CREATE TABLE IF NOT EXISTS watch
             (serverid bigint, userid bigint)''') # WATCH

fury.execute('''CREATE TABLE IF NOT EXISTS rsvp
             (serverid bigint, channelid bigint, name text, timestamp bigint, users text)''') # RSVP

#fury.execute('''CREATE TABLE IF NOT EXISTS poll
#             (messageid bigint, is_poll bit)''') # IS POLL
#fury.execute('''CREATE TABLE IF NOT EXISTS reactions
#             (messageid bigint, userid bigint, reacted bit)''') # REACTION CHECK



con = sqlite3.connect(':memory:')
#con.isolation_level = None
mem = con.cursor()

mem.execute('''CREATE TABLE IF NOT EXISTS bypass
             (serverid bigint, userid bigint, bypass_state bit)''') # SWEAR BYPASS LIST
mem.execute('''CREATE TABLE IF NOT EXISTS progress
             (serverid bigint, ongoing bit)''') # RAFFLE IN PROGRESS
mem.execute('''CREATE TABLE IF NOT EXISTS raffle
             (serverid bigint, userid bigint)''') # RAFFLE

client = discord.Client()
#appinfo = discord.AppInfo()
#client.change_presence(status=dnd)
failsafe = False
ignore = False
file = 'settings.json'

def log(text):
    import time
    time_log = time.strftime("%X", time.localtime(time.time()))
    #print('[{}] {}'.format(time_log, text))
    #print(tracers.colors.OKGREEN + f'[{time_log}] ' + tracers.colors.ENDC + f'{text}')
    print(f'{tracers.colors.strong.green}[{time_log}] {text}{tracers.colors.reset}')
    #try:
    #    log_server = client.get_server('227127903249367041')
    #    log_channel = discord.utils.get(log_server.channels, name='bot-logs')
    #    client.send_message(log_channel, text)
    #except discord.DiscordException:
    #    pass

async def swear_filter(serverid, message, userid, message_data):
    global bypass
    bypass = None
    for bypass_state in mem.execute("SELECT bypass_state FROM bypass WHERE serverid = ? AND userid = ?", (serverid, userid, )):
        bypass = bypass_state[0]
        #log(bypass_state)
    #log(bypass)
    if bypass == 1:
        return 0;
    else:
        text = None
        if message_data != None:
            try:
                text = py_tesseract(message_data, 'message')
            except OSError:
                #await client.change_presence(game=discord.Game(name='LEGO Universe'))
                pass

        #await client.change_presence(game=discord.Game(name='LEGO Universe'))
        if text != None:
            message += '\n'
            message += '\n'
            message += text

            log_server = client.get_server('227127903249367041')
            log_channel = discord.utils.get(log_server.channels, name='bot-logs')
            await client.send_message(log_channel, '[IMAGE TEXT] {}'.format(message))
            
            #log(message)
        #censor_server = client.get_server(serverid)
        #censor_member = censor_server.get_member(userid)

        swears = ''
        offenceTime = 0
        #swearCounter = 0
        msg = message.lower()
        swearExceptionCounter = 0
        #censor_channel = discord.utils.get(censor_server.channels, name='censor-log')
        #msg = ''.join(e for e in message.lower() if e.isalnum())
        for exception in fury.execute("SELECT phrase FROM swearexception WHERE serverid = ?", (serverid, )):
            offenceTime -= msg.count('{}'.format(exception[0]))
            swearExceptionCounter += msg.count('{}'.format(exception[0]))
            #if msg.count('{}'.format(exception[0])) > 0:
                
        for phrase in fury.execute("SELECT phrase FROM swear WHERE serverid = ?", (serverid, )):
            offenceTime += msg.count('{}'.format(phrase[0]))
            #swearCounter += msg.count('{}'.format(phrase[0]))
            if msg.count('{}'.format(phrase[0])) > 0:
                swears += '{}, '.format(phrase[0])

        #if offenceTime > 0:
        #    watch_server = client.get_server(serverid)
        #    watch_member = watch_server.get_member(userid)
        #    await watch(watch_server, watch_member, 'swear', message)
        return offenceTime, swears

def py_tesseract(message, mode):
    if mode == 'message':
        if message != None:
            if message.server != None: # PY TESSERACT
                url = None
                for attach in message.attachments:
                    #log (attach)
                    str_attach = str(attach)
                    attach_replace = str_attach.replace('\'', '"')
                    attachment_info = json.loads(attach_replace)
                    url = attachment_info['url']
                if url != None:
                    data = requests.get(url).content
                    image = Image.open(io.BytesIO(data))

                    first = False
                    second = False
                    try: 
                        image.filter(ImageFilter.MedianFilter())
                        enhancer = ImageEnhance.Contrast(image)
                        image = enhancer.enhance(2)
                        image.convert('1')
                    except ValueError:
                        first = True
                    
                    try:
                        image.filter(ImageFilter.SHARPEN)
                    except ValueError:
                        second = True
                
                    #image_id = attachment_info['id']
                    #filename = '{}.png'.format(image_id)
                    if first and second:
                        return None
                    else:
                        text = pytesseract.image_to_string(image)
                        return text
            return None
        return None
    elif mode == 'image': # SCANS A DIRECT IMAGE
        if message != None:
            data = requests.get(message).content
            image = Image.open(io.BytesIO(data))

            try:
                image.filter(ImageFilter.MedianFilter())
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(2)
                image.convert('1')
            except ValueError:
                pass
                    
            image.filter(ImageFilter.SHARPEN)
            
            text = pytesseract.image_to_string(image)
            return text
        return None
    return None


async def permission_response(message):
    await client.send_message(message.channel, 'Sorry {}, you do not have permission to run that command!'.format(message.author.mention))
    return;

def json_reader(data_type): # JSON READ / WRITE
    import os.path
    global exists
    global data
    global token
    #file = 'settings.json'
    exists = os.path.isfile(file)

    if exists == False:
        time_log = time.strftime("%X", time.localtime(time.time()))
        token = input("[{}] What is the bot's login token? ".format(time_log))
        json_token = json.dumps({"token": token})
        with open(file, 'w') as json_file:  
            json.dump(json_token, json_file)
        exists = os.path.isfile(file)

    if exists:    
        with open(file) as json_file:  
            data = json.load(json_file)
        arg = json.loads(data)
        args = [x for x in arg] # PARSE ARGUMENTS
        if args[0] == 'token':
            if data_type == 'login':
                token = arg[args[0]]
                #log('> Attempting Login: Token {}'.format(token))
                log(f'{tracers.colors.cyan}> Attempting Login.')
                return token;

async def checks(server, user, action, data):
    channel = discord.utils.get(server.channels, name='logs')
    if action == 'on_member_join':
        test = None
    elif action == 'on_member_update':
        if user.nick != data.nick:
            await client.send_message(channel, '[{}] [UPDATE] [NICK] {} to {}'.format(user.mention, data.nick, user.nick))
        if user.game != data.game:
            await client.send_message(channel, '[{}] [UPDATE] [GAME] {} to {}'.format(user.mention, data.game, user.game))

async def audit(server, user, action, data):
    await watch(server, user, action, data)
    channel = discord.utils.get(server.channels, name='audit-log')
    if channel != None:
        if action == 'on_member_update':
            #user = after, data = before
            if user.nick != data.nick:
                await client.send_message(channel, '[{}] [NICK] {} to {}'.format(user.mention, data.nick, user.nick))
            #if user.game != data.game:
            #    await client.send_message(channel, '[{}] [GAME] {} to {}'.format(user.mention, data.game, user.game))
            #if user.avatar != data.avatar:
            #    await client.send_message(channel, '[{}] [AVATAR] {} to {}'.format(user.mention, data.game, user.game))

        elif action == 'on_server_update':
            if user.name != data.name:
                await client.send_message(channel, '[{}] [SERVER] [NAME] {} to {}'.format(user.name, data.name, user.name))
            if user.owner != data.owner:
                await client.send_message(channel, '[{}] [SERVER] [OWNER] {} to {}'.format(user.name, data.owner, user.owner))
            if user.region != data.region:
                await client.send_message(channel, '[{}] [SERVER] [REGION] {} to {}'.format(user.name, data.region, user.region))
            if user.icon != data.icon:
                await client.send_message(channel, '[{}] [SERVER] [ICON] [UPDATE]'.format(user.name))
            if user.afk_channel != data.afk_channel:
                await client.send_message(channel, '[{}] [SERVER] [AFK_CHANNEL] {} to {}'.format(user.name, data.afk_channel, user.afk_channel))
            if user.afk_timeout != data.afk_timeout:
                await client.send_message(channel, '[{}] [SERVER] [AFK_TIMEOUT] {} to {}'.format(user.name, data.afk_timeout, user.afk_timeout))
            if user.mfa_level != data.mfa_level:
                await client.send_message(channel, '[{}] [SERVER] [MFA_LEVEL] {} to {}'.format(user.name, data.mfa_level, user.mfa_level))
            if user.verification_level != data.verification_level:
                await client.send_message(channel, '[{}] [SERVER] [VERIFICATION_LEVEL] {} to {}'.format(user.name, data.verification_level, user.verification_level))
            if user.features != data.features:
                await client.send_message(channel, '[{}] [SERVER] [FEATURES] [UPDATE]'.format(user.name))
            if user.default_channel != data.default_channel:
                await client.send_message(channel, '[{}] [SERVER] [DEFAULT_CHANNEL] {} to {}'.format(user.name, data.default_channel.name, user.default_channel.name))
            
        elif action == 'on_server_role_create':
            await client.send_message(channel, '[{}] [ROLE] [CREATE]'.format(user.name))

        elif action == 'on_server_role_delete':
            await client.send_message(channel, '[{}] [ROLE] [DELETE]'.format(user.name))
            
        elif action == 'on_server_role_update':
            if user.name != data.name:
                await client.send_message(channel, '[{}] [ROLE] [NAME] {} to {}'.format(user.name, data.name, user.name))
            if user.permissions != data.permissions:
                for new, old in zip(user.permissions, data.permissions):
                    if new[1] != old[1]:
                        await client.send_message(channel, '[{}] [ROLE] [PERM_UPDATE] {} from {} to {}'.format(user.name, new[0], new[1], old[1]))
                    #await client.send_message(channel, '[{}] [ROLE] [PERM] [UPDATE]'.format(user.name))
            if user.position != data.position:
                await client.send_message(channel, '[{}] [ROLE] [POS] {} to {}'.format(user.name, data.position, user.position))
            if user.hoist != data.hoist:
                await client.send_message(channel, '[{}] [ROLE] [HOIST] {} to {}'.format(user.name, data.hoist, user.hoist))
            if user.color != data.color:
                await client.send_message(channel, '[{}] [ROLE] [COLOR] {} to {}'.format(user.name, data.to_tuple(), user.to_tuple()))
            if user.mentionable != data.mentionable:
                await client.send_message(channel, '[{}] [ROLE] [MENTION] {} to {}'.format(user.name, data.mentionable, user.mentionable))
            
        elif action == 'on_member_ban':
            await client.send_message(channel, '[{}#{}] [BANNED]'.format(user.name, user.discriminator))
            
        elif action == 'on_member_unban':
            await client.send_message(channel, '[{}#{}] [UNBANNED]'.format(user.name, user.discriminator))
    
async def watch(server, user, action, data):
    channel = discord.utils.get(server.channels, name='watch')
    for userid in fury.execute("SELECT * FROM watch WHERE serverid = ? AND userid = ?", (server.id, user.id)):
        #log('Watch called: {} {} {} {}'.format(server, user, action, data.content))
        if action == 'message': # MESSAGE
            url = None
            for attach in data.attachments:
                str_attach = str(attach)
                attach_replace = str_attach.replace('\'', '"')
                attachment_info = json.loads(attach_replace)
                url = attachment_info['url']
            content = data.content
            for members in data.mentions:
                content = data.content.replace(members.mention , '@{}#{}'.format(members.name, members.discriminator))
            if url == None:
                await client.send_message(channel, '[{}] [{}] {}'.format(data.channel, user.mention, data.content))
            else:
                await client.send_message(channel, '[{}] [{}] {} {}'.format(data.channel, user.mention, data.content, url))
           
        elif action == 'message_edit': # MESSAGE EDIT
            url = None
            for attach in data.attachments:
                str_attach = str(attach)
                attach_replace = str_attach.replace('\'', '"')
                attachment_info = json.loads(attach_replace)
                url = attachment_info['url']
            content = data.content
            for members in data.mentions:
                content = data.content.replace(members.mention , '@{}#{}'.format(members.name, members.discriminator))
            if url == None:
                await client.send_message(channel, '[{}] [{}] [edited] {}'.format(data.channel, user.mention, data.content))
            else:
                await client.send_message(channel, '[{}] [{}] [edited] {} {}'.format(data.channel, user.mention, data.content, url))
                
        elif action == 'swear': # SWEAR
            await client.send_message(channel, '[{}] [{}] [SWEAR EVENT] {}'.format(data.channel, user.mention, data.content))
            
        elif action == 'on_reaction_add':
            await client.send_message(channel, '[{}] [REACTION ADD] [WIP]'.format(user.mention))
            
        #elif action == 'on_member_join':
        #    await client.send_message(channel, '[{}] [USER JOINED] [WIP]'.format(user.mention))
            
        #elif action == 'on_member_leave':
        #    await client.send_message(channel, '[{}] [USER LEFT] [WIP]'.format(user.mention))
            
        elif action == 'on_member_update':
            #user = after, data = before
            if user.nick != data.nick:
                await client.send_message(channel, '[{}] [UPDATE] [NICK] {} to {}'.format(user.mention, data.nick, user.nick))
            #if user.game != data.game:
            #    await client.send_message(channel, '[{}] [UPDATE] [GAME] {} to {}'.format(user.mention, data.game, user.game))
            
        #elif action == 'on_voice_state_update': # DO NOT ACKNOWLEDGE
            #await client.send_message(channel, '[{}] [VOICE STATE UPDATED]'.format(user.mention))
            
        elif action == 'on_member_ban':
            await client.send_message(channel, '[{}#{}] [USER BANNED]'.format(user.name, user.discriminator))
            
        elif action == 'on_member_unban':
            await client.send_message(channel, '[{}#{}] [USER UNBANNED]'.format(user.name, user.discriminator))

def make_printable(text):
    return ''.join(i for i in text if ord(i)<128)

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

async def watch_logs(server, message):
    if server != None:
        channel = discord.utils.get(server.channels, name='watch')
        await client.send_message(channel, message)
    

#@client.event
#async def on_error(event, args, kwargs):
#    log_server = client.get_server('227127903249367041')
#    log_channel = discord.utils.get(log_server.channels, name='bot-logs')
#    await client.send_message(log_channel, 'ERROR: Event {} with args {} and kwargs {}'.format(event, args, kwargs))

@client.event
async def on_ready():
    log(f'{tracers.colors.cyan}> Logged in: {tracers.colors.strong.yellow}{client.user.name}, {tracers.colors.strong.cyan}{client.user.id}, {tracers.colors.strong.magenta}Initiated.')
    await client.change_presence(game=discord.Game(name='LEGO Universe'))

#@client.event
#async def on_member_join(member):
    #text = py_tesseract(member.avatar_url, 'image')
    #offenceTime = await swear_filter(member.server.id, text, member.id, None)
    #if offenceTime > 0:
    #    defaultChannel = member.server.default_channel
    #    member = server.get_member(client.user.id)
    #    sendMessages = member.permissions_in(defaultChannel).send_messages
    #    if sendMessages:
    #        await client.send_message(defaultChannel, '!mute {} {}'.format('-1', member.mention))
    #        await client.send_message(member.id, 'You have been muted in {} for an inappropriate profile picture. Please change it, or ask staff to review this case.'.format(member.server.name))
    #offenceTime = await swear_filter(member.server.id, text, member.id, None)
    #if offenceTime > 0:
    #    defaultChannel = member.server.default_channel
    #    member = server.get_member(client.user.id)
    #    sendMessages = member.permissions_in(defaultChannel).send_messages
    #    if sendMessages:
    #        await client.send_message(defaultChannel, '!mute {} {}'.format('-1', member.mention))
    #        await client.send_message(member.id, 'You have been muted in {} for an inappropriate name. Please change it, or ask staff to review this case.'.format(member.server.name))

    
@client.event
async def on_server_join(server):
    log('> Joined {}'.format(server.name))
    defaultChannel = server.default_channel
    member = server.get_member(client.user.id)
    sendMessages = member.permissions_in(defaultChannel).send_messages
    if sendMessages:
        await client.send_message(defaultChannel, 'Hello! My name is {}. I am a moderation bot intended to prevent spam and swearing.'.format(client.user.name))

@client.event
async def on_server_remove(server):
    log(f'{tracers.colors.strong.red}> Removed from {server.name}')

@client.event
async def on_server_update(before, after):
    #log('ON SERVER UPDATE')
    await audit(after, after, 'on_server_update', before)

@client.event
async def on_server_role_update(before, after):
    await audit(after.server, after, 'on_server_role_update', before)

@client.event
async def on_server_role_create(role):
    await audit(role.server, role, 'on_server_role_create', role)

@client.event
async def on_server_role_delete(role):
    await audit(role.server, role, 'on_server_role_delete', role)

@client.event
async def on_reaction_add(reaction, user):
    #log('ON REACTION ADD')
    #muteMember = user.server_permissions.mute_members
    #admin = user.server_permissions.administrator
    # is poll  messageid bigint, is_poll bit
    # reacted  messageid bigint, userid bigint, reacted bit
    #log(reaction.message.id)
    #if user.id != client.user.id:
    if True == False:
        poll = None
        for is_poll in fury.execute("SELECT is_poll FROM poll WHERE messageid = ?", (reaction.message.id, )):
            poll = is_poll[0]
            log('IS POLL : {}'.format(poll))
            
        if poll == True:
            reacted = None
            for has_reacted in fury.execute("SELECT reacted FROM reactions WHERE messageid = ? AND userid = ?", (reaction.message.id, user.id, )):
                reacted = has_reacted[0]
                log('HAS REACTED : {}'.format(reacted))

            if reacted == True:
                await client.remove_reaction(reaction.message, reaction.emoji, user)
                log('REMOVE REACTION')
            
            else:
                fury.execute("INSERT INTO reactions VALUES (?, ?, ?)", (reaction.message.id, user.id, True, ))
                conn.commit()
                await watch(reaction.message.server, user, 'on_reaction_add', reaction)
        else:
            await watch(reaction.message.server, user, 'on_reaction_add', reaction)
        

# SGSDKJFDA:LFJK

    #fury.execute("INSERT INTO reactions VALUES (?, ?)", (reaction.message.id, user.id, True))

client.event
async def on_reaction_remove(reaction, user):
    #log('ON REACTION REMOVE')
    #muteMember = user.server_permissions.mute_members
    #admin = user.server_permissions.administrator
# is poll  messageid bigint, is_poll bit
# reacted  messageid bigint, userid bigint, reacted bit
    if True == False:
        poll = None
        for is_poll in fury.execute("SELECT is_poll FROM poll WHERE messsageid = ?", (reaction.message.id, )):
            poll = is_poll[0]

        if poll == True:
            fury.execute("DELETE FROM reactions WHERE messageid = ? AND userid = ? ", (reaction.message.id, user.id,))

@client.event
async def on_member_update(before, after):
    await audit(after.server, after, 'on_member_update', before)

@client.event
async def on_member_ban(member):
    await audit(member.server, member, 'on_member_ban', None)

@client.event
async def on_member_unban(server, user):
    await audit(server, user, 'on_member_unban', None)

@client.event
async def on_message_edit(message_before, message):
    if message.server != None: # SERVER LOGS
        await audit(message.server, message.author, 'message_edit', message)
        channel = discord.utils.get(message.server.channels, name='logs')
        if channel != None:
            if message.channel != channel:
                member = message.server.get_member('344569392572530690') # ECHO 
                if member == None or member.status == discord.Status.offline: # IF OFFLINE
                    url = None
                    for attach in message.attachments:
                        str_attach = str(attach)
                        attach_replace = str_attach.replace('\'', '"')
                        attachment_info = json.loads(attach_replace)
                        url = attachment_info['url']
                    content = message.content
                    for members in message.mentions:
                        content = message.content.replace(members.mention , '@{}#{}'.format(members.name, members.discriminator))
                    if url == None:
                        await client.send_message(channel, '[{}] [{}] [edited] {}'.format(message.channel.name, message.author.name, content))
                    else:
                        await client.send_message(channel, '[{}] [{}] [edited] {} {}'.format(message.channel.name, message.author.name, content, url))

        swearEvent = False
        admin = message.author.server_permissions.administrator
        muteMember = message.author.server_permissions.mute_members
        if admin == False and message.author.bot == False and muteMember == False: # START OF SWEAR PROTECTION
        #if message.author.bot == False: # START OF SWEAR PROTECTION
            offenceTime, swears = await swear_filter(message.server.id, message.content, message.author.id, message)
            if offenceTime > 0:
                try:
                    await client.delete_message(message)
                except discord.errors.Forbidden:
                    pass
                swearEvent = True
                if offenceTime >= 3:
                    member = message.server.get_member('344569392572530690') # ECHO
                    if member != None and member.status != discord.Status.offline: # IF OFFLINE
                        await client.send_message(message.channel, '!mute {} {}'.format(offenceTime, message.author.mention))
                censor_channel = discord.utils.get(message.server.channels, name='censor-log')
                if censor_channel != None:
                    await client.send_message(censor_channel, '{} swore while editing their message in {}, added {}totalling in {} offences.'.format(message.author.mention, message.channel.mention, swears, offenceTime))

        url = None
        for attach in message.attachments:
            #log (attach)
            str_attach = str(attach)
            attach_replace = str_attach.replace('\'', '"')
            attachment_info = json.loads(attach_replace)
            url = attachment_info['url']
        if url != None:
            mem.execute("DELETE FROM bypass WHERE serverid = ? AND userid = ?;", (message.server.id, members.id, ))
            con.commit()

#@bot.command(description='For when you wanna settle the score some other way')
#async def mention(self, ctx):
#    counter = 0
#    #x = message.server.members
#    x = ctx.server.members
#    for member in x:
#        counter += 1
#    await bot.say('I am currently defending the {} members that are in this guild.'.format(counter))
    #await client.send_message(message.channel, 'I am currently defending the {} members that are in this guild.'.format(counter))
    #unknown_command = False

@client.event
async def on_message(message):
    global failsafe
    global ignore        
    
    if message.server != None: # SERVER LOG
        await watch(message.server, message.author, 'message', message)
        channel = discord.utils.get(message.server.channels, name='logs') #
        if channel != None:
            if message.channel != channel:
                member = message.server.get_member('344569392572530690') # ECHO
                if member == None or member.status == discord.Status.offline: # IF OFFLINE
                    url = None
                    for attach in message.attachments:
                        str_attach = str(attach)
                        attach_replace = str_attach.replace('\'', '"')
                        attachment_info = json.loads(attach_replace)
                        url = attachment_info['url']
                    content = message.content
                    for members in message.mentions:
                        content = message.content.replace(members.mention , '@{}#{}'.format(members.name, members.discriminator))
                    if url == None:
                        await client.send_message(channel, '[{}] [{}] {}'.format(message.channel.name, message.author.name, content))
                    else:
                        await client.send_message(channel, '[{}] [{}] {} {}'.format(message.channel.name, message.author.name, content, url))
    
    if message.server == None: # PRIVATE MESSAGES
        #log('{}'.format(message.channel.user))
        log_server = client.get_server('227127903249367041')
        log_channel = discord.utils.get(log_server.channels, name='bot-pm-log')
        #log_member = log_server.get_member(message.channel)
        url = None
        for attach in message.attachments:
            str_attach = str(attach)
            attach_replace = str_attach.replace('\'', '"')
            attachment_info = json.loads(attach_replace)
            url = attachment_info['url']
        content = message.content
        for members in message.mentions:
            content = message.content.replace(members.mention , '@{}#{}'.format(members.name, members.discriminator))
        if message.author != client.user:
            if url == None:
                await client.send_message(log_channel, '[PM] [{}] -> [{}] {}'.format(message.channel.user, client.user, content))
            else:
                await client.send_message(log_channel, '[PM] [{}] -> [{}] {} {}'.format(message.channel.user, client.user, content, url))
        elif message.author == client.user:
            if url == None:
                await client.send_message(log_channel, '[PM] [{}] -> [{}] {}'.format(client.user, message.channel.user, content))
            else:
                await client.send_message(log_channel, '[PM] [{}] -> [{}] {} {}'.format(client.user, message.channel.user, content, url))

        if message.author.id != client.user.id:
            log(f'{tracers.colors.strong.magenta}[DM] {tracers.colors.strong.yellow}[{message.author.name}#{message.author.discriminator}] {tracers.colors.strong.green}{message.content}')
            if message.author.id == '85702178525704192' or message.author.id == '227161120069124096' or message.author.id == '173324987665612802' or message.author.id == '172846477683458049':
                if message.content.startswith('.restart'): # PM RESTART
                    await client.send_message(message.channel, '{} is restarting.'.format(client.user.name))
                    log(f'{tracers.colors.strong.red}> Manual PM Restart: {tracers.colors.strong.yellow}{client.user.name}, {tracers.colors.strong.cyan}{client.user.id}, {tracers.colors.strong.magenta}Restarting.')
                    await client.close()
            if message.content.startswith('.json '): # JSON CODES
                com = message.content[len('.json '):]
                arg = json.loads(com)
                args = [x for x in arg] # PARSE ARGUMENTS
                if args[0] == 'serverid':
                    if args[1] == 'messageid':
                        if args[2] == 'type':
                            if args[3] == 'text':
                                if arg[args[2]] == 'swearapprove':
                                    swearEvent = False
                                    offenceTime, swears = await swear_filter(arg[args[0]], arg[args[3]], None, None)
                                    if offenceTime > 0:
                                        swearEvent = True
                                    await client.send_message(message.channel, json.dumps({"serverid": arg[args[0]], "messageid": arg[args[1]], "type": 'swearevent', "text": swearEvent}))      
                                else:
                                    await client.send_message(message.channel, json.dumps({"serverid": arg[args[0]], "messageid": arg[args[1]], "type": 'invalid', "text": 0}))
                            else: # TEXT
                                await client.send_message(message.channel, json.dumps({"serverid": arg[args[0]], "messageid": arg[args[1]], "type": 'invalid', "text": 0}))
                        else: # TYPE
                            await client.send_message(message.channel, json.dumps({"serverid": arg[args[0]], "messageid": arg[args[1]], "type": 'invalid', "text": 0}))
                    else: # MESSAGE
                        await client.send_message(message.channel, json.dumps({"serverid": arg[args[0]], "messageid": arg[args[1]], "type": 'invalid', "text": 0}))
                else: # SERVER
                    await client.send_message(message.channel, json.dumps({"serverid": arg[args[0]], "messageid": arg[args[1]], "type": 'invalid', "text": 0}))

    elif message.server != None and failsafe == False: # SERVER MESSAGES
        muteMember = message.author.server_permissions.mute_members
        admin = message.author.server_permissions.administrator
        unknown_command = False
        if message.content.startswith('.'):
            unknown_command = True
        if message.author.id == client.user.id:
            unknown_command = False

        if message.content.lower().startswith('.ping'):
            unknown_command = False
            if muteMember:
                unknown_command = False
                from datetime import datetime
                datetime.utcnow()
                time = message.timestamp
                #log('{} and {}'.format(datetime.utcnow(), time))
                get_utc = str(datetime.utcnow()).split(':')
                get_time = str(time).split(':')
                new_utc = float(get_utc[2]) + (float(get_utc[1]) * 60)
                new_time = float(get_time[2]) + (float(get_time[1]) * 60)
                #log(get_utc)
                #log(get_time)
                act_time = new_utc - new_time
                #log(abs(act_time))
                await client.send_message(message.channel, 'Pong! Approximate Discord latency is {} seconds!'.format(abs(act_time)))
            else:
                await permission_response(message)
            

        if message.content.lower().startswith('.rsvp'):
            unknown_command = False
            args = message.content.split(' ')
            if len(args) > 1:
                if args[1] == 'c':
                    if muteMember:
                        if len(args) > 2:
                            import time
                            name = message.content[len('{} {} '.format(args[0], args[1])):]
                            fury.execute("INSERT INTO rsvp VALUES (?, ?, ?, ?, ?)", (message.server.id, message.channel.id, name, int(time.time()), None, ))
                            conn.commit()
                            await client.send_message(message.channel, '{} created {} RSVP.'.format(message.author.mention, name))
                    else:
                        await permission_response(message)
                elif args[1] == 'list':
                    if muteMember:
                        users = None
                        name = None
                        for user_list in fury.execute("SELECT users, name FROM rsvp WHERE serverid =? AND channelid =? ORDER BY timestamp DESC", (message.server.id, message.channel.id, )):
                            users = user_list[0]
                            name = user_list[1]
                            break
                        if users != None:
                            await client.send_message(message.channel, 'The following users have entered into the {} RSVP:'.format(name))
                            uargs = users.split(',')
                            ulist = ''
                            for x in range(len(uargs)):
                                member = message.server.get_member('{}'.format(uargs[x]))
                                if x == (len(uargs) - 1):
                                    ulist += 'and {}.'.format(member.mention)
                                else: 
                                    ulist += '{}, '.format(member.mention)
                            await client.send_message(message.channel, '{}'.format(ulist))
                          

            else:
                users = None
                name = None
                for user_list in fury.execute("SELECT users, name FROM rsvp WHERE serverid =? AND channelid =? ORDER BY timestamp DESC", (message.server.id, message.channel.id, )):
                    users = user_list[0]
                    name = user_list[1]
                    break

                ulist = ''
                entered = None
                if users != None:
                    uargs = users.split(',')
                    for x in range(len(uargs)):
                        if uargs[x] == message.author.id:
                            entered = True
                        ulist += '{},'.format(uargs[x])
                if entered == None:
                    if name != None:
                        ulist += '{}'.format(message.author.id)
                        fury.execute("UPDATE rsvp SET users = ? WHERE serverid = ? AND channelid = ? AND name = ?", (ulist, message.server.id, message.channel.id, name, ))
                        conn.commit()
                        await client.send_message(message.channel, '{} responded to the {} RSVP.'.format(message.author.mention, name))
                

                        

        if message.content.startswith('.comm'):
            unknown_command = False
            args = message.content.split(' ')
            if admin:
                if len(args) > 1:
                    if args[1] == 'c' or args[1] == 'create':
                        await client.send_message(message.channel, 'Command create called.')
                        if len(args) > 2:
                            await client.send_message(message.channel, 'Command name (arg2) specified as \'{}\'.'.format(args[2]))
                            if len(args) > 3 and is_number(args[3]):
                                await client.send_message(message.channel, 'Command argument count (arg3) specified as \'{}\'.'.format(args[3]))
                                if len(args) > 4:
                                    log('end')
                        else:
                            await client.send_message(message.channel, 'There is not enough arguments!')
                    else:
                        await client.send_message(message.channel, 'Invalid argument!')
            else:
                await permission_response(message)
                
                        

        #mem.execute('''CREATE TABLE IF NOT EXISTS progress
            #(serverid bigint, ongoing bit)''') # RAFFLE IN PROGRESS
        #mem.execute('''CREATE TABLE IF NOT EXISTS raffle
            #(serverid bigint, userid bigint)''') # RAFFLE'

        if message.content.startswith('.sort'):
            unknown_command = False
            appinfo = await client.application_info()
            if appinfo.owner.id == message.author.id:
                #inte = 0
                for count in fury.execute("SELECT count(*) FROM swear WHERE serverid = ?", (message.server.id, )):
                    for x in range(int(count[0])):
                        for phrase in fury.execute("SELECT phrase FROM swear WHERE serverid = ?", (message.server.id, )):
                            #inte += 1
                            #log(inte)
                            fury.execute("DELETE FROM swear WHERE serverid = ? AND phrase = ?", (message.server.id, phrase[0], ))
                            fury.execute("INSERT INTO swear VALUES (?, ?)", (message.server.id, phrase[0], ))
                            conn.commit()
                #inte = 0
                for count in fury.execute("SELECT count(*) FROM swearexception WHERE serverid = ?", (message.server.id, )):
                    for x in range(int(count[0])):
                        for phrase in fury.execute("SELECT phrase FROM swearexception WHERE serverid = ?", (message.server.id, )):
                            #inte += 1
                            #log(inte)
                            fury.execute("DELETE FROM swearexception WHERE serverid = ? AND phrase = ?", (message.server.id, phrase[0], ))
                            fury.execute("INSERT INTO swearexception VALUES (?, ?)", (message.server.id, phrase[0], ))
                            conn.commit()

                await client.send_message(message.channel, 'I sorted this server\'s swear list for you master. ')



        if message.content.startswith('.raffle'): # RAFFLE
            unknown_command = False
            ongoing = None
            for is_ongoing in mem.execute("SELECT ongoing FROM progress WHERE serverid = ?", (message.server.id, )):
                ongoing = is_ongoing[0]
            entered = None
            for is_entered in mem.execute("SELECT userid FROM raffle WHERE serverid = ? AND userid = ?", (message.server.id, message.author.id, )):
                entered = is_entered[0]
            args = message.content.split(' ')
            if len(args) >= 2:
                if muteMember:
                    if args[1] == 'create' or args[1] == 'c': # CREATE
                        if ongoing == None:
                            mem.execute("INSERT INTO progress VALUES (?, 1)", (message.server.id, ))
                            await client.send_message(message.channel, '{} has started a raffle! Type .raffle into chat and hit enter!'.format(message.author.mention))
                        else:
                            await client.send_message(message.channel, 'There is already an ongoing raffle {}.'.format(message.author.mention))
                    elif args[1] == 'select' or args[1] == 's': # SELECT
                        if ongoing == True:
                            if len(args) >= 2:
                                if len(args) == 3:
                                    if is_number(args[2]):
                                        import random
                                        for x in range(int(args[2])):
                                            prenumber = 0
                                            for has_number in mem.execute("SELECT * FROM raffle WHERE serverid = ?", (message.server.id, )):
                                                prenumber += 1
                                            number = random.randint(1, prenumber)
                                            count = 1
                                            for members in mem.execute("SELECT userid FROM raffle WHERE serverid = ?", (message.server.id, )):
                                                if count == number:
                                                    member = message.server.get_member('{}'.format(members[0]))
                                                    mem.execute("DELETE FROM raffle WHERE serverid = ? AND userid = ?", (message.server.id, member.id, ))
                                                    await client.send_message(message.channel, '{} has been selected for the raffle!'.format(member.mention))
                                                count += 1
                                        
                                else:
                                    import random
                                    for x in range(1):
                                        prenumber = 0
                                        for has_number in mem.execute("SELECT * FROM raffle WHERE serverid = ?", (message.server.id, )):
                                            prenumber += 1
                                        number = random.randint(1, prenumber)
                                        count = 1
                                        for members in mem.execute("SELECT userid FROM raffle WHERE serverid = ?", (message.server.id, )):
                                            if count == number:
                                                member = message.server.get_member('{}'.format(members[0]))
                                                mem.execute("DELETE FROM raffle WHERE serverid = ? AND userid = ?", (message.server.id, member.id, ))
                                                await client.send_message(message.channel, '{} has been selected for the raffle!'.format(member.mention))
                                            count += 1
                                    
                        else:
                            await client.send_message(message.channel, 'There\'s currently no ongoing raffle {}!'.format(message.author))
                                

                    elif args[1] == 'cancel':
                        if ongoing == True:
                            mem.execute("DELETE FROM raffle WHERE serverid = ?", (message.server.id, ))
                            mem.execute("DELETE FROM progress WHERE serverid = ?", (message.server.id, ))
                            await client.send_message(message.channel, 'Raffle has been cancelled by {}.'.format(message.author.mention))

                else:
                    await permission_response(message)
                
                
            else:
                if ongoing == True:
                    if entered == None:
                        mem.execute("INSERT INTO raffle VALUES (?, ?)", (message.server.id, message.author.id, ))
                        await client.send_message(message.channel, '{} has entered into the raffle!'.format(message.author.mention))
                    else:
                        await client.send_message(message.channel, 'You have already entered into the raffle {}!'.format(message.author.mention))
                #else:
                    #await client.send_message(message.channel, 'There\' currently no ongoing raffle {}!'.format(message.author.mention))
                    

        if message.content.startswith('.random '): # RANDOM
            unknown_command = False
            if muteMember:
                args = message.content.split(' ')
                if len(args) > 2:
                    if is_number(args[1]):
                        if (message.server.member_count/10) >= int(args[1]):
                            import random
                            for x in range(int(args[1])):
                                number = random.randint(1, message.server.member_count)
                                count = 1
                                for member in message.server.members:
                                    if number == count:
                                        await client.send_message(message.channel, '{} has been randomly selected!'.format(member.mention))
                                        break
                                    count += 1
                        else:
                            await client.send_message(message.channel, 'The value you ented is invalid {}. You cannot randomly pick more than 10% of the server!'.format(message.author.mention))

        
        if message.content.startswith('.run'):
            unknown_command = False
            appinfo = await client.application_info()
            if appinfo.owner.id == message.author.id:
                #msg = message.content[len('.run '):]
                args = message.content.split(' ')
                if args[1] == 'internal':
                    if args[2] == 'echo':
                        await client.send_message(message.channel, 'Comm not complete! Could not run internal command.')
                        

        if message.content.startswith('.internal'):
            unknown_command = False

        if message.content.startswith('.log'):
            unknown_command = False        

        if message.content.startswith('.test'):
            unknown_command = False
            #log(f'{tracers.colors.strong.green}Testing')

        if message.content.startswith('.oldtest'):
            unknown_command = False
            if admin:
                msg = message.content[len('.oldtest'):]
                args = msg.split(' ')
                if len(args) > 0:
                    if args[0] == 'add':
                        if len(message.mentions) > 0:
                            for member_mentions in message.mentions:
                                if member_mentions.id != '399539809569472515' or member_mentions.id != '399777479423688705':
                                    fury.execute("INSERT INTO watch VALUES (?, ?)", (message.server.id, member_mentions.id, ))
                                    conn.commit()
                                    await watch_logs(message.server, '**{} is now being watched!**'.format(member_mentions.mention))
            


        if message.content.startswith('.update'):
            unknown_command = False
            await client.send_message(message.channel, 'Tracer is currently writing a new permission based system for commands!')
            
        if message.content.startswith('.help'): # HELP COMMAND - TEMPORARY! DO. NOT. JUDGE.
            unknown_command = False
            msg = message.content[len('.help'):]
            args = msg.split(' ')
            if len(args) == 1: # COMMAND LIST
                response =      ': ----------------------------------------------------------------------------------------------------'
                response +=     '\n: Here are the commands available to you *{}*:'.format(message.author.mention)
                response +=     '\n: **.members** - Displays the number of users in this Discord server.'
                response +=     '\n: **.servers** - Displays the number of Discord servers/guilds that this bot is in.'
                response +=     '\n: **.json** - Only usuable in Private Messages. Returns requested information.'
                response +=     '\n: **.updates** - Displays bot rewrite updates!'
                if muteMember or admin:
                    response += '\n\n: **.allow** - Allows a user to send a message, ignoring the language filter. Timeout is 60 seconds.'
                    response += '\n: **.mention** - Mention a given user.'
                    response += '\n: **.say** - Make the bot say a message.'
                    response += '\n: **.vote** - Finalizes a vote. Please see syntax.'
                    response += '\n: **.poll** - Finalizes a poll. Please see syntax.'
                    response += '\n: **.addreaction** - Add custom emoji reaction to a message.'
                    response += '\n: **.random** - Picks a random member of this Discord.'
                if admin:
                    response += '\n\n: **.watch** - Watch somebody and report their every move to a channel.'
                    response += '\n: **.addswear** - Add a word to the language filter.'
                    response += '\n: **.removeswear** - Remove a word from the language filter.'
                    response += '\n: **.addswearexception** - Add a word to the exception filter.'
                    response += '\n: **.removeswearexception** - Remove a word from the exception filter.'
                if message.author.id == '85702178525704192' or message.author.id == '227161120069124096' or message.author.id == '173324987665612802' or message.author.id == '172846477683458049':
                    response += '\n\n: **.quit** - Put the bot into a lockdown state.'
                    response += '\n: **.restart** - Restart the bot if it is in lockdown. PM Only.'
                    response += '\n: **.restart** - Restart the bot.'
                await client.send_message(message.channel, response)
            elif len(args) > 1: # SYNTAX STUFF
                response = None
                if args[1] == 'update':
                    response = ': **.updates** - Displays bot rewrite updates!'
                elif args[1] == 'members':
                    response = ': **.members** - Displays the number of users in this Discord server.'
                elif args[1] == 'servers':
                    response = '\n: **.servers** - Displays the number of Discord servers/guilds that this bot is in. '
                elif args[1] == 'json':
                    response = '\n: **.json** {"serverid": "*serverid*", "messageid": "*messageid*", "type": "*type*", "text": "*text*"}'
                elif args[1] == 'allow':
                    response = ': .allow {}'.format(message.author.mention)
                elif args[1] == 'mention':
                    response = ': **.mention** *{}*/*{}*'.format(message.author.mention, message.author.id)
                elif args[1] == 'say':
                    response = '\n: **.say** *Hello World*'
                elif args[1] == 'vote':
                    response = ': **Declare a vote:** *Vote to add Brick Fury to **{}**.*'.format(message.server.name)
                    response += '\n: **Create the vote:** *.vote*'
                elif args[1] == 'poll':
                    response = ': **Declare a poll:** *Poll to add Brick Fury to **{}**.*'.format(message.server.name)
                    response += '\n: :regional_indicator_a: `Yes`'
                    response += '\n: :regional_indicator_b: `No`'
                    response += '\n: :regional_indicator_c: `Of course! {} is awesome!`'.format(message.author)
                    response += '\n: **Create the poll:** *.poll **3***'
                elif args[1] == 'addreaction':
                    emoji_server = client.get_server('323959784019591169') # JALUS Discord
                    for y in emoji_server.emojis:
                        if str(y) == '<:maude_will_find_you:343515988106674176>':
                            response = '\n: **.addreaction** *{}* {}'.format(message.id, y)
                elif args[1] == 'raffle':
                    response = ': **.random** {} (number of users to pick)'.format(message.server.member_count/10)
                elif args[1] == 'watch':
                    response = ': **.watch** add/remove {}'.format(message.author.mention)
                elif args[1] == 'addswear':
                    response = ': **.addswear** {}'.format(message.author.name)
                elif args[1] == 'removeswear':
                    response = ': **.removeswear** {}'.format(message.author.name)
                elif args[1] == 'addswearexception':
                    response = ': **.addswear** {}'.format(message.author.name)
                elif args[1] == 'removeswearexception':
                    response = ': **.removeswearexception** {}'.format(message.author.name)
                        
                if message.author.id == '85702178525704192' or message.author.id == '227161120069124096' or message.author.id == '173324987665612802' or message.author.id == '172846477683458049':
                    if args[1] == 'quit':
                        response = ': **.quit** - Puts the bot into lockdown.'
                    elif args[1] == 'restart':
                        response = ': **.restart** - Restarts the bot. Can be done anywhere. If the bot is in lockdown, restart has to be done via private message.'  

                if response != None:
                    await client.send_message(message.channel, response)
                elif response == None:
                    await client.send_message(message.channel, 'Sorry {}, but no instance of that command was found.'.format(message.author.mention))
                
                    
            
        if message.content.startswith('.watch '): # WATCH
            unknown_command = False
            if admin:
                msg = message.content[len('.watch '):]
                args = msg.split(' ')
                if len(args) > 0:
                    if args[0] == 'add':
                        if len(message.mentions) > 0:
                            for member_mentions in message.mentions:
                                if member_mentions.id != '399539809569472515' or member_mentions.id != '399777479423688705':
                                    fury.execute("INSERT INTO watch VALUES (?, ?)", (message.server.id, member_mentions.id, ))
                                    conn.commit()
                                    await watch_logs(message.server, '**{} is now being watched!**'.format(member_mentions.mention))
                    elif args[0] == 'remove':
                        if len(message.mentions) > 0:
                            for member_mentions in message.mentions:
                                fury.execute("DELETE FROM watch WHERE serverid = ? AND userid = ?;", (message.server.id, member_mentions.id, ))
                                conn.commit()
                                await watch_logs(message.server, '**{} is no longer being watched!**'.format(member_mentions.mention))
                    else:
                        await client.send_message(message.channel, 'Sorry {}, but the given argument does not currently exist!'.format(message.author.mention))
                        
        if message.content.startswith('.allow'): # ALLOW SWEARING
            unknown_command = False
            if muteMember:
                msg = message
                ignore = False
                if len(message.mentions) > 0:
                    ignore = True
                    for members in message.mentions:
                        #log(members)
                        mem.execute("INSERT INTO bypass VALUES (?, ?, '1')", (msg.server.id, members.id, ))
                        con.commit()
                        #log('Before')
                        try:
                            await client.delete_message(message)
                        except discord.errors.Forbidden:
                            pass
                        #await client.delete_message(message)
                        await client.wait_for_message(timeout=60, author=members)
                        #log('After')
                        url = None
                        for attach in message.attachments:
                            #log (attach)
                            str_attach = str(attach)
                            attach_replace = str_attach.replace('\'', '"')
                            attachment_info = json.loads(attach_replace)
                            url = attachment_info['url']
                        if url == None:
                            mem.execute("DELETE FROM bypass WHERE serverid = ? AND userid = ?;", (msg.server.id, members.id, ))
                            con.commit()
                            
        if message.content.startswith('.mention '): # MENTION USERS !!! MOST LIKELY HAS BUGS
            unknown_command = False
            if muteMember:
                msg = message.content[len('.mention '):]
                args = msg.split(' ')
                member_list = []
                if len(args) > 0:
                    if len(message.mentions) > 0:
                            for member_mentions in message.mentions:
                                member_list.append(member_mentions.mention)
                                
                    for members in args:
                        member = message.server.get_member(members)
                        if member != None:
                            member_list.append(member.mention)

                await client.send_message(message.channel, ' '.join(map(str, member_list)))
                
        
        if message.content.startswith('.quit'): # QUIT
            unknown_command = False
            if message.author.id == '85702178525704192' or message.author.id == '227161120069124096' or message.author.id == '173324987665612802' or message.author.id == '172846477683458049':
                await client.change_presence(status=discord.Status.do_not_disturb)
                log(f'{tracers.colors.strong.red}> Failsafe Mode: {tracers.colors.strong.yellow}{client.user.name}, {tracers.colors.strong.cyan}{client.user.id}, {tracers.colors.strong.red}Failsafe Active.')
                failsafe = True
        if message.content.startswith('.addswear '): # ADD SWEAR COMMAND
            if message.author.bot == False:
                if admin:
                    msg = message.content[len('.addswear '):]
                    fury.execute("INSERT INTO swear VALUES (?,?)", (message.server.id, msg.lower(), ))
                    conn.commit()
                else:
                    await permission_response(message)
                unknown_command = False
        if message.content.startswith('.removeswear '): # REMOVE SWEAR COMMAND
            if message.author.bot == False:
                if admin:
                    msg = message.content[len('.removeswear '):]
                    fury.execute("DELETE FROM swear WHERE serverid = ? AND phrase = ?;", (message.server.id, msg.lower(), ))
                    conn.commit()
                else:
                    await permission_response(message)
                unknown_command = False
        if message.content.startswith('.addswearexception '): # ADD SWEAR EXCEPTION COMMAND
            if message.author.bot == False:
                if admin:
                    msg = message.content[len('.addswearexception '):]
                    fury.execute("INSERT INTO swearexception VALUES (?,?)", (message.server.id, msg.lower(), ))
                    conn.commit()
                else:
                    await permission_response(message)
                unknown_command = False
        if message.content.startswith('.removeswearexception '): # REMOVE SWEAR EXCEPTION COMMAND
            if message.author.bot == False:
                if admin:
                    msg = message.content[len('.removeswearexception '):]
                    fury.execute("DELETE FROM swearexception WHERE serverid = ? AND phrase = ?;", (message.server.id, msg.lower(), ))
                    conn.commit()
                else:
                    await permission_response(message)
                unknown_command = False
        
        if message.content.startswith('.say '): # SAY COMMAND
            if muteMember:
                msg = message.content[len('.say '):]
                await client.send_message(message.channel, msg)
            else:
                await permission_response(message)
            unknown_command = False
        if message.content.startswith('Vote'): # VOTE FUNCTION
            if muteMember:
                def check(msg):
                    return msg.content.startswith('.vote') # VOTE FUNCTION SUBCOMMAND
                msg = await client.wait_for_message(timeout=60, author=message.author, check=check)
                #fury.execute("INSERT INTO poll VALUES (?,?)", (message.id, True, ))
                #conn.commit()
                if msg != None:
                    await client.add_reaction(message, u"\U0001F53C") # UP ARROW
                    await client.add_reaction(message, u"\U0001F53D") # DOWN ARROW
            else:
                await permission_response(message)
            unknown_command = False
        if message.content.startswith('Poll'): # POLL FUNCTION
            if muteMember:
                def check(msg):
                    return msg.content.startswith('.poll ') # POLL FUNCTION SUBCOMMAND
                msg = await client.wait_for_message(timeout=60, author=message.author, check=check)
                #fury.execute("INSERT INTO poll VALUES (?,?)", (message.id, True, ))
                #conn.commit()
                val = msg.content[len('.poll '):]
                valint = int(val)
                base = ord(u"\U0001F1E6")
                if valint <= 20 and valint >= 2:
                    for x in range(0, valint):
                        options = base + x
                        indicator = chr(options)
                        await client.add_reaction(message, indicator) # REGIONAL INDICATORS
                    
            else:
                await permission_response(message)
            unknown_command = False
        if message.content.startswith('.addreaction '): # POLL FUNCTION
            if muteMember:
                msg = message.content[len('.addreaction '):]
                args = msg.split(' ')
                selected_emoji = None
                log(args[1])
                for x in client.servers:
                    for y in x.emojis:
                        if str(y) == args[1]:
                            selected_emoji = y
                selected_message = await client.get_message(message.channel, args[0])
                if selected_emoji != None:
                    await client.add_reaction(selected_message, selected_emoji)
            unknown_command = False
        if message.content.startswith('.vote'): # vote void
            unknown_command = False
        if message.content.startswith('.poll'): # poll void
            unknown_command = False
        if message.content.startswith('.restart'): # RESTART COMMAND
            if muteMember:
                msg = message.content[len('.restart'):]
                await client.send_message(message.channel, '{} is restarting{}.'.format(client.user.name, msg))
                log(f'{tracers.colors.strong.red}> Manual Restart: {tracers.colors.strong.yellow}{client.user.name}, {tracers.colors.strong.cyan}{client.user.id}, {tracers.colors.strong.magenta}Restarting.')
                try:
                    await client.delete_message(message)
                except discord.errors.Forbidden:
                    pass
                unknown_command = False
                await client.close()
            else:
                await permission_response(message)
                unknown_command = False
        if message.content.startswith('.members'): # MEMBERS COMMAND
            await client.send_message(message.channel, 'I am currently defending the {} members that are in this guild.'.format(message.server.member_count))
            unknown_command = False
        if message.content.startswith('.servers'): # SERVER COMMAND
            await client.send_message(message.channel, 'I am currently defending {} guilds.'.format(len(client.servers)))
            unknown_command = False
            
        swearEvent = False
        if admin == False and message.author.bot == False and muteMember == False: # START OF SWEAR PROTECTION
        #if message.author.bot == False: # START OF SWEAR PROTECTION
            offenceTime, swears = await swear_filter(message.server.id, message.content, message.author.id, message)
            if offenceTime > 0:
                swearEvent = True
                if offenceTime >= 3:
                    member = message.server.get_member('344569392572530690') # ECHO
                    if member != None and member.status != discord.Status.offline: # IF OFFLINE
                        await client.send_message(message.channel, '!mute {} {}'.format(offenceTime, message.author.mention))
                censor_channel = discord.utils.get(message.server.channels, name='censor-log')
                if censor_channel != None:
                    await client.send_message(censor_channel, '{} swore in {}, said {}totalling in {} offences.'.format(message.author.mention, message.channel.mention, swears, offenceTime))


        #if muteMember == False and message.author.bot == False: # START OF SPAM PROTECTION

        if unknown_command == True and message.content.startswith('..') == False:
            await client.send_message(message.channel, 'Sorry {}, but the given command does not currently exist!'.format(message.author.mention))

        if message.content.startswith('.'):
            if ignore:
                blakn = True
            elif message.content.startswith('.restart'):
                if muteMember == False:
                    try:
                        await client.delete_message(message)
                    except discord.errors.Forbidden:
                        pass
            elif message.content.startswith('.internal'):
                blakn = True
            elif message.content.startswith('.log'):
                blakn = True
            elif message.content.startswith('..'):
               blakn = True
            else:
                try:
                    await client.delete_message(message)
                except discord.errors.Forbidden:
                    pass
        elif swearEvent:
            try:
                await client.delete_message(message)
            except discord.errors.Forbidden:
                pass

# START
try:
    client.run(json_reader('login')) # private
except discord.errors.LoginFailure as e:
    import os.path
    exists = os.path.isfile(file)
    if exists:
        try:
            os.remove(file)
        except OSError:
            pass
    log('discord.errors.LoginFailure has occured. Please check your login token')
    log('SESSION HAS BEEN TERMINATED')
    client.close()











