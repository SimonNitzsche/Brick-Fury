#   __________        .__        __     ___________                   
#   \______   \_______|__| ____ |  | __ \_   _____/_ _________ ___.__.
#    |    |  _/\_  __ \  |/ ___\|  |/ /  |    __)|  |  \_  __ <   |  |
#    |    |   \ |  | \/  \  \___|    <   |     \ |  |  /|  | \/\___  |
#    |______  / |__|  |__|\___  >__|_ \  \___  / |____/ |__|   / ____|
#           \/                \/     \/      \/                \/     

import discord
from discord.ext import commands
import sqlite3
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

fury.execute('''CREATE TABLE IF NOT EXISTS perms
             (serverid bigint, userid bigint, perm list)''') # PERMS

fury.execute('''CREATE TABLE IF NOT EXISTS commands
             (count int, command text, description text, number int, access text)''') # COMMANDS

con = sqlite3.connect(':memory:')
#con.isolation_level = None
mem = con.cursor()

mem.execute('''CREATE TABLE IF NOT EXISTS bypass
             (serverid bigint, userid bigint, bypass_state bit)''') # SWEAR BYPASS LIST
mem.execute('''CREATE TABLE IF NOT EXISTS progress
             (serverid bigint, ongoing bit)''') # RAFFLE IN PROGRESS
mem.execute('''CREATE TABLE IF NOT EXISTS raffle
             (serverid bigint, userid bigint)''') # RAFFLE


logging_con = sqlite3.connect('logger.sqlite')
logging = logging_con.cursor()

logging.execute('''CREATE TABLE IF NOT EXISTS replace
             (find text, replacement text)''')

client = discord.Client()
players={}
voices={}
#appinfo = discord.AppInfo()
#client.change_presence(status=dnd)
failsafe = False
ignore = False
file = 'settings.json'

def log(text):
    import time
    time_log = time.strftime("%X", time.localtime(time.time()))
    print(f'{tracers.colors.strong.green}[{time_log}] {text}{tracers.colors.reset}')

async def swear_filter(serverid, message, userid, message_data):
    global bypass
    bypass = None
    for bypass_state in mem.execute("SELECT bypass_state FROM bypass WHERE serverid = ? AND userid = ?", (serverid, userid, )):
        bypass = bypass_state[0]
    if bypass == 1:
        return 0;
    else:
        text = None
        if message_data != None:
            try:
                text = py_tesseract(message_data, 'message')
            except OSError:
                pass

        if text != None:
            message += '\n'
            message += '\n'
            message += text

            from functions import json
            try:
                log_server = client.get_server(json.reader('main_server'))
            except ValueError as err:
                json.write('main_server', '480876512120143882')
            log_channel = discord.utils.get(log_server.channels, name='bot-logs')
            await client.send_message(log_channel, '[IMAGE TEXT] {}'.format(message))

        swears = ''
        offenceTime = 0
        msg = message.lower()
        swearExceptionCounter = 0

        for exception in fury.execute("SELECT phrase FROM swearexception WHERE serverid = ?", (serverid, )):
            offenceTime -= msg.count('{}'.format(exception[0]))
            swearExceptionCounter += msg.count('{}'.format(exception[0]))
                
        for phrase in fury.execute("SELECT phrase FROM swear WHERE serverid = ?", (serverid, )):
            offenceTime += msg.count('{}'.format(phrase[0]))
            if msg.count('{}'.format(phrase[0])) > 0:
                swears += '{}, '.format(phrase[0])
        return offenceTime, swears

def py_tesseract(message, mode):
    if mode == 'message':
        if message != None:
            if message.server != None: # PY TESSERACT
                url = None
                import json
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
                        await client.send_message(channel, '[{}] [ROLE] [PERM_UPDATE] {} from {} to {}'.format(user.name, new[0], old[1], new[1]))
            if user.position != data.position:
                await client.send_message(channel, '[{}] [ROLE] [POS] {} to {}'.format(user.name, data.position, user.position))
            if user.hoist != data.hoist:
                await client.send_message(channel, '[{}] [ROLE] [HOIST] {} to {}'.format(user.name, data.hoist, user.hoist))
            if user.color != data.color:
                await client.send_message(channel, '[{}] [ROLE] [COLOR] {} to {}'.format(user.name, data.color.to_tuple(), user.color.to_tuple()))
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
                content = content.replace(members.mention, 'f@{members.name}#{members.discriminator}')
            content = content.replace('@everyone', '@​everyone')
            content = content.replace('@here', '@​here')
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
                content = content.replace(members.mention, 'f@{members.name}#{members.discriminator}')
            content = content.replace('@everyone', '@​everyone')
            content = content.replace('@here', '@​here')
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
    text_list = list(text)
    for x in range(len(text_list)):
        for get in logging.execute("SELECT replacement FROM replace WHERE find = ?", (text_list[x], )):
            text = text.replace(text_list[x], get[0])
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

async def status_update():
    from functions import json
    nurl = None
    ngame = None
    if json.reader('url') != 'None':
        nurl = json.reader('url')
    if json.reader('game') != 'None':
        ngame = json.reader('game')
    if is_number(json.reader('type')) == False:
        json.update('type', '0')
    await client.change_presence(game=discord.Game(name=ngame, type=int(json.reader('type')), url=nurl), status=json.reader('status'))

@client.event
async def on_ready():
    from functions import json
    log(f'{tracers.colors.cyan}> Logged in: {tracers.colors.strong.yellow}{client.user.name}, {tracers.colors.strong.cyan}{client.user.id}, {tracers.colors.strong.magenta}Initiated.')

    for x in range(100):
        try:
            await status_update()
            break
        except ValueError as err:
            if err.args[1] == 'game':
                json.write('game', 'LEGO Universe')
            elif err.args[1] == 'type':
                json.write('type', '0')
            elif err.args[1] == 'url':
                json.write('url', 'None')
            elif err.args[1] == 'status':
                json.write('status', 'online')


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
                    import json
                    for attach in message.attachments:
                        str_attach = str(attach)
                        attach_replace = str_attach.replace('\'', '"')
                        attachment_info = json.loads(attach_replace)
                        url = attachment_info['url']
                    content = message.content
                    for members in message.mentions:
                        content = content.replace(members.mention, 'f@{members.name}#{members.discriminator}')
                    content = content.replace('@everyone', '@​everyone')
                    content = content.replace('@here', '@​here')
                    if url == None:
                        await client.send_message(channel, '[{}] [{}] [edited] {}'.format(message.channel.name, message.author.name, content))
                    else:
                        await client.send_message(channel, '[{}] [{}] [edited] {} {}'.format(message.channel.name, message.author.name, content, url))

    
        swearEvent = False
        admin = message.author.server_permissions.administrator
        muteMember = message.author.server_permissions.mute_members
        if admin == False and message.author.bot == False and muteMember == False: # START OF SWEAR PROTECTION
        #if message.author.bot == False: # START OF SWEAR PROTECTION
            offenceTime, swears = await swear_filter(message.server.id, make_printable(message.content), message.author.id, message)
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

    if message.server == None: # PRIVATE MESSAGES
        #log('{}'.format(message.channel.user))
        from functions import json
        try:
            log_server = client.get_server(json.reader('main_server'))
        except ValueError as err:
            json.write('main_server', '480876512120143882')
        log_channel = discord.utils.get(log_server.channels, name='bot-pm-log')
        #log_member = log_server.get_member(message.channel)
        url = None
        import json
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

def perms(message):
    if message.server == None:
        return True
    else:
        if True != True:
            args = message.content.split(' ')
            com_arg = args[0]
            command = com_arg[len('.'):]
            perms = None
            for perm_list in fury.execute("SELECT perm FROM perms WHERE serverid =? AND userid =?", (message.server.id, message.author.id, )):
                perms = perm_list[0]
            if perms != None:
                perms = perms.split(',')
                com = False
                for x in range(len(perms)):
                    if command == perms[x]:
                        com = True
                        return True
                if com == False:
                    #state = None
                    for state_list in fury.execute("SELECT default_state FROM commands WHERE command =?", (command, )):
                        if state_list[0] == 'false':
                            return False
                        elif state_list[0] == 'true':
                            return True
            else:
                return False

                #state = state_list[0]
            #return
            #import re
            #com_name = list(args[0])
            #if re.match('[a-zA-Z]', com_name[1]) == False:
            #    await client.send_message(message.channel, 'Sorry {}, you do not have permission to run that command!'.format(message.author.mention))
            #    return False
            #else:
            #    return None

        if message.author.server_permissions.administrator != True:
            return False
        elif message.content.startswith('.ping'):
            if message.author.server_permissions.mute_members:
                return True
            else:
                return False
        else:
            return True

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
                    import json
                    for attach in message.attachments:
                        str_attach = str(attach)
                        attach_replace = str_attach.replace('\'', '"')
                        attachment_info = json.loads(attach_replace)
                        url = attachment_info['url']
                    content = message.content
                    for members in message.mentions:
                        content = content.replace(members.mention, 'f@{members.name}#{members.discriminator}')
                    content = content.replace('@everyone', '@​everyone')
                    content = content.replace('@here', '@​here')
                    if url == None:
                        await client.send_message(channel, '[{}] [{}] {}'.format(message.channel.name, message.author.name, content))
                    else:
                        await client.send_message(channel, '[{}] [{}] {} {}'.format(message.channel.name, message.author.name, content, url))
    
    if message.server == None: # PRIVATE MESSAGES
        #log('{}'.format(message.channel.user))
        from functions import json
        try:
            log_server = client.get_server(json.reader('main_server'))
        except ValueError as err:
            json.write('main_server', '480876512120143882')
        log_channel = discord.utils.get(log_server.channels, name='bot-pm-log')
        #log_member = log_server.get_member(message.channel)
        url = None
        import json
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
                import json
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

    # GENERAL COMMANDS
    args = message.content.split(' ')
    if args[0] == '.ping':
        if perms(message):
            if len(args) > 1:
                if args[1] == 'discord':
                    from datetime import datetime
                    datetime.utcnow()
                    time = message.timestamp
                    get_utc = str(datetime.utcnow()).split(':')
                    get_time = str(time).split(':')
                    new_utc = float(get_utc[2]) + (float(get_utc[1]) * 60)
                    new_time = float(get_time[2]) + (float(get_time[1]) * 60)
                    act_time = new_time - new_utc
                    await client.send_message(message.channel, 'Pong! Approximate Discord latency is {} seconds!'.format(abs(act_time)))
            else:
                import time
                before = time.monotonic()
                msg = await client.send_message(message.channel, 'Pong!')                
                ping = round((time.monotonic() - before) * 1000)
                await client.edit_message(msg, f'Pong! `{ping}ms`')


    if message.server != None and failsafe == False: # SERVER MESSAGES
        admin = message.author.server_permissions.administrator
        muteMember = message.author.server_permissions.mute_members
        #args = message.content.split(' ')
        if args[0] == '.run':
            await client.delete_message(message)
            appinfo = await client.application_info()
            if appinfo.owner.id == message.author.id:
                if args[1] == 'internal':
                    update = message.content[len(f'{args[0]} {args[1]} {args[2]} '):]
                    from functions import json
                    if args[2] == 'status':
                        json.update('status', args[3])
                        await status_update()
                    elif args[2] == 'game':
                        json.update('game', update)
                        await status_update()
                    elif args[2] == 'type':
                        json.update('type', args[3])
                        await status_update()
                    elif args[2] == 'url':
                        json.update('url', args[3])
                        await status_update()
            else:
                await permission_response(message)


        elif args[0] == '.embed':
            if muteMember:
                blank = True
            else:
                await permission_response(message)

        elif args[0] == '.perm':
            #if perms(message):
            appinfo = await client.application_info()
            if appinfo.owner.id == message.author.id:
                if args[1] == 'toggle':
                    found = False
                    perm = None
                    for perm_list in fury.execute("SELECT perm FROM perms WHERE serverid =? AND userid =?", (message.server.id, message.channel.id, )):
                        perm = perm_list[0]
                    if perm == None:
                        for comm in fury.execute("SELECT command FROM commands"):
                            if args[2] == comm[0]:
                                fury.execute("INSERT INTO perms VALUES (?, ?, ?)", (message.server.id, message.author.id, args[2], ))
                                conn.commit()
                    if perm != None:
                        for x in len(perm):
                            if args[2] == perm[x]: # REMOVE FROM LIST
                                comlist = ''
                                for x in range(len(perm)):
                                    if args[2] != perm[x]:
                                        comlist += '{}, '.format(member.mention)
                                fury.execute("UPDATE perms SET perm = ? WHERE serverid = ? AND userid = ?", (comlist, message.server.id, message.channel.id, ))
                            #for comm in fury.execute("SELECT command FROM commands"):
                                #if args[2] == comm[0]
                    perm = perm.split(',')
                    for x in range(len(perm)):
                        log(perm[x])
                        

        elif args[0] == '.clear':
            await client.delete_message(message)
            if muteMember:
                if len(args) > 1:
                    if is_number(args[1]):
                        if int(args[1]) < 500:
                            try:
                                await client.purge_from(message.channel, limit=int(args[1]))
                                await client.send_message(message.channel, f'Purged {args[1]} messages.')
                            except discord.errors.Forbidden:
                                await client.send_message(message.channel, f'Unable to purge {args[1]} messages. Inproper permissions.')
                            except discord.errors.HTTPException:
                                await client.send_message(message.channel, f'Unable to purge {args[1]} messages. HTTPException occured.')
                            except discord.errors.NotFound:
                                pass
                        else:
                            await client.send_message(message.channel, f'Unable to purge {args[1]} messages. Cannot purge more than 500 messages.')
                    else:
                        await client.send_message(message.channel, f'Unable to purge messages. Argument 1 is not a number.')
                else:
                    await client.send_message(message.channel, f'Unable to purge messages. Argument 1 not specified.')
            else:
                await permission_response(message)
           
                #fury.execute("DELETE FROM perms WHERE serverid = ? AND userid = ?;", (message.server.id, member_mentions.id, ))
                #conn.commit()
        elif args[0].lower() == '.rsvp':
            if len(args) > 1:
                if args[1] == 'c':
                    if muteMember:
                        if len(args) > 2:
                            import time
                            name = message.content[len('{} {} '.format(args[0], args[1])):]
                            fury.execute("INSERT INTO rsvp VALUES (?, ?, ?, ?, ?, ?)", (message.server.id, message.channel.id, name, int(time.time()), None, True))
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
                                    ulist += '{}, .'.format(member.mention)
                for user_list in fury.execute("SELECT users, name, enabled FROM rsvp WHERE serverid =? AND channelid =? ORDER BY timestamp DESC", (message.server.id, message.channel.id, )):
                    enabled = user_list[2]
                    users = user_list[0]
                    name = user_list[1]
                    break
                ulist = ''
                entered = None
                if enabled == True:
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
                else:
                    await client.send_message(message.channel, 'Sorry {}, but the {} RSVP is currently closed.'.format(message.author.mention, name))
                

            await client.delete_message(message)

        #if message.content.startswith('.comm'):
        #    
        #    args = message.content.split(' ')
        #    if perms(message):
        #        if len(args) > 1:
        #            if args[1] == 'c' or args[1] == 'create':
        #                await client.send_message(message.channel, 'Command create called.')
        #                if len(args) > 2:
        #                    await client.send_message(message.channel, 'Command name (arg2) specified as \'{}\'.'.format(args[2]))
        #                    if len(args) > 3 and is_number(args[3]):
        #                        await client.send_message(message.channel, 'Command argument count (arg3) specified as \'{}\'.'.format(args[3]))
        #                        if len(args) > 4:
        #                            log('end')
        #                else:
        #                    await client.send_message(message.channel, 'There is not enough arguments!')
        #            else:
        #                await client.send_message(message.channel, 'Invalid argument!')
        #    else:
        #        await permission_response(message)
                
                        

        #mem.execute('''CREATE TABLE IF NOT EXISTS progress
            #(serverid bigint, ongoing bit)''') # RAFFLE IN PROGRESS
        #mem.execute('''CREATE TABLE IF NOT EXISTS raffle
            #(serverid bigint, userid bigint)''') # RAFFLE'
        
        elif args[0] == '.sort':
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

            await client.delete_message(message)

        elif args[0] == '.raffle': # RAFFLE
            ongoing = None
            for is_ongoing in mem.execute("SELECT ongoing FROM progress WHERE serverid = ?", (message.server.id, )):
                ongoing = is_ongoing[0]
            entered = None
            for is_entered in mem.execute("SELECT userid FROM raffle WHERE serverid = ? AND userid = ?", (message.server.id, message.author.id, )):
                entered = is_entered[0]
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
                    
            await client.delete_message(message)
        elif args[0] == '.random ': # RANDOM
            if muteMember:
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
            await client.delete_message(message)
        
        #if message.content.startswith('.run'):
        #    
        #    appinfo = await client.application_info()
        #    if appinfo.owner.id == message.author.id:
        #        #msg = message.content[len('.run '):]
        #        args = message.content.split(' ')
        #        if args[1] == 'internal':
        #            if args[2] == 'echo':
        #                await client.send_message(message.channel, 'Comm not complete! Could not run internal command.')
                        

        elif message.content.startswith('.internal'):
            blank = True

        elif message.content.startswith('.log'):
            blank = True

        elif args[0] == '.ping':
            await client.delete_message(message)

        elif message.content.startswith('.test'):
            await client.delete_message(message)
            #log(f'{tracers.colors.strong.green}Testing')

        #if message.content.startswith('.oldtest'):
        #    
        #    if admin:
        #        msg = message.content[len('.oldtest'):]
        #        args = msg.split(' ')
        #        if len(args) > 0:
        #            if args[0] == 'add':
        #                if len(message.mentions) > 0:
        #                    for member_mentions in message.mentions:
        #                        if member_mentions.id != '399539809569472515' or member_mentions.id != '399777479423688705':
        #                            fury.execute("INSERT INTO watch VALUES (?, ?)", (message.server.id, member_mentions.id, ))
        #                            conn.commit()
        #                            await watch_logs(message.server, '**{} is now being watched!**'.format(member_mentions.mention))
            


        elif args[0] == 'updates':
            await client.send_message(message.channel, 'Tracer is currently writing a new permission based system for commands!')
            await client.delete_message(message)    
        elif args[0] == '.help':
            bot = message.server.get_member(client.user.id)
            top_role_color = bot.top_role.color
            await client.delete_message(message)  
            if len(args) > 1:
                embed = None
                response = ''
                command = None
                for command_list in fury.execute("SELECT number, command, description FROM commands WHERE command=? ORDER BY number ASC", (args[1], )):
                    command = command_list[1]
                    if command_list[0] > 0:
                        response += f'{command_list[2]}\n'
                            
                if command != None:
                    command = command.capitalize()
                    response = response.replace('message.id', str(message.id))
                    response = response.replace('message.author.id', str(message.author.id))
                    response = response.replace('message.server.name', str(message.server.name))
                    response = response.replace('message.author.mention', str(message.author.mention))
                    response = response.replace('message.author', str(message.author))
                                    
                    embed = discord.Embed(color=0x9B59B6)
                    embed.add_field(name=f'**{command} command:**', value=f'{response}', inline=False)
                else:
                    embed = discord.Embed(description=f'Sorry {message.author.mention}, but no instance of that command was found.', color=top_role_color)
                    #embed.add_field(name=f'**{command} command:**', value=f'{response}', inline=False)
                await client.send_message(message.channel, embed=embed)
                            
            else:
                embed = discord.Embed(description=f'Here are the commands available to you *{message.author.mention}*:', color=top_role_color)
                for command_list in fury.execute("SELECT command, description, access FROM commands WHERE number=0 ORDER BY count ASC"):
                    command = command_list[0]
                    description = command_list[1]
                    if command_list[2] == 'admin':
                        if admin:
                            embed.add_field(name=f'**.{command}**', value=f' - {description}', inline=False)
                    elif command_list[2] == 'muteMember':
                        if muteMember:
                            embed.add_field(name=f'**.{command}**', value=f' - {description}', inline=False)
                    else:
                        embed.add_field(name=f'**.{command}**', value=f' - {description}', inline=False)

                await client.send_message(message.channel, embed=embed)
        elif args[0] == '.watch': # WATCH
            if muteMember:
                if len(args) > 1:
                    msg = message.content[len(f'{args[0]} '):]
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
            await client.delete_message(message)           
        elif args[0] == '.allow': # ALLOW SWEARING
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
            await client.delete_message(message)
        elif args[0] == '.mention': # MENTION USERS !!! MOST LIKELY HAS BUGS
            if muteMember:
                if len(args) > 1:
                    msg = message.content[len(f'{args[0]} '):]
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
            await client.delete_message(message)        
        elif args[0] == '.quit': # QUIT
            if message.author.id == '85702178525704192' or message.author.id == '227161120069124096' or message.author.id == '173324987665612802' or message.author.id == '172846477683458049':
                await client.change_presence(status=discord.Status.do_not_disturb)
                log(f'{tracers.colors.strong.red}> Failsafe Mode: {tracers.colors.strong.yellow}{client.user.name}, {tracers.colors.strong.cyan}{client.user.id}, {tracers.colors.strong.red}Failsafe Active.')
                await client.delete_message(message)
                failsafe = True
        elif args[0] =='.addswear': # ADD SWEAR COMMAND
            if message.author.bot == False:
                if perms(message):
                    if len(args) > 1:
                        msg = message.content[len(f'{args[0]} '):]
                        fury.execute("INSERT INTO swear VALUES (?,?)", (message.server.id, msg.lower(), ))
                        conn.commit()
                else:
                    await permission_response(message)
            await client.delete_message(message)
        elif args[0] =='.removeswear': # REMOVE SWEAR COMMAND
            if message.author.bot == False:
                if perms(message):
                    if len(args) > 1:
                        msg = message.content[len(f'{args[0]} '):]
                        fury.execute("DELETE FROM swear WHERE serverid = ? AND phrase = ?;", (message.server.id, msg.lower(), ))
                        conn.commit()
                else:
                    await permission_response(message)
            await client.delete_message(message)
        elif args[0] == '.addswearexception': # ADD SWEAR EXCEPTION COMMAND
            if message.author.bot == False:
                if perms(message):
                    if len(args) > 1:
                        msg = message.content[len(f'{args[0]} '):]
                        fury.execute("INSERT INTO swearexception VALUES (?,?)", (message.server.id, msg.lower(), ))
                        conn.commit()
                else:
                    await permission_response(message)
            await client.delete_message(message)    
        elif args[0] == '.removeswearexception': # REMOVE SWEAR EXCEPTION COMMAND
            if message.author.bot == False:
                if perms(message):
                    if len(args) > 1:
                        msg = message.content[len(f'{args[0]} '):]
                        fury.execute("DELETE FROM swearexception WHERE serverid = ? AND phrase = ?;", (message.server.id, msg.lower(), ))
                        conn.commit()
                else:
                    await permission_response(message)
            await client.delete_message(message)
        elif args[0] == '.say': # SAY COMMAND
            if muteMember:
                if len(args) > 1:
                    msg = message.content[len(f'{args[0]} '):]
                    await client.send_message(message.channel, msg)
            else:
                await permission_response(message)
            await client.delete_message(message)
        elif message.content.startswith('Vote'): # VOTE FUNCTION
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
        elif message.content.startswith('Poll'): # POLL FUNCTION
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
        elif args[0] == '.addreaction': # POLL FUNCTION
            if muteMember:
                selected_emoji = None
                for x in client.servers:
                    for y in x.emojis:
                        if str(y) == args[2]:
                            selected_emoji = y
                selected_message = await client.get_message(message.channel, args[1])
                if selected_emoji != None:
                    await client.add_reaction(selected_message, selected_emoji)
            await client.delete_message(message)
        elif args[0] == '.vote': # vote void
            await client.delete_message(message)
        elif args[0] == '.poll': # poll void
            await client.delete_message(message)
        elif args[0] == '.restart': # RESTART COMMAND
            if message.author.id == '85702178525704192' or message.author.id == '227161120069124096' or message.author.id == '173324987665612802' or message.author.id == '172846477683458049':
                msg = message.content[len('.restart'):]
                await client.send_message(message.channel, '{} is restarting{}.'.format(client.user.name, msg))
                log(f'{tracers.colors.strong.red}> Manual Restart: {tracers.colors.strong.yellow}{client.user.name}, {tracers.colors.strong.cyan}{client.user.id}, {tracers.colors.strong.magenta}Restarting.')
                try:
                    await client.delete_message(message)
                except discord.errors.Forbidden:
                    pass
                
                await client.close()

        elif args[0] == '.members': # MEMBERS COMMAND
            await client.send_message(message.channel, 'I am currently defending the {} members that are in this guild.'.format(message.server.member_count))
            await client.delete_message(message)
            
        elif args[0] == '.servers': # SERVER COMMAND
            await client.send_message(message.channel, 'I am currently defending {} guilds.'.format(len(client.servers)))
            await client.delete_message(message)
            
        else: # UNKNOW COMMAND
            com_name = list(args[0])
            if len(com_name) > 0:
                if com_name[0] == '.' and len(com_name) > 1:
                    import re
                    if re.match(r'[a-zA-Z]', com_name[1]):
                        await client.send_message(message.channel, f'Sorry {message.author.mention}, but the given command does not currently exist!')
                        await client.delete_message(message)
            
        swearEvent = False
        if admin == False and message.author.bot == False and muteMember == False: # START OF SWEAR PROTECTION
        #if message.author.bot == False: # START OF SWEAR PROTECTION
            offenceTime, swears = await swear_filter(message.server.id, make_printable(message.content), message.author.id, message)
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
                    await client.send_message(censor_channel, '{} swore in {}, said {}totalling in {} offences.'.format(message.author.mention, message.channel.mention, swears, offenceTime))


        #if muteMember == False and message.author.bot == False: # START OF SPAM PROTECTION

# START
from functions import logger, json
try:
    logger.log(f'{tracers.colors.cyan}> Attempting Login.')
    client.run(json.reader('login')) # private
except discord.errors.LoginFailure as e:
    import os.path
    exists = os.path.isfile(json.file)
    if exists:
        try:
            os.remove(json.file)
        except OSError:
            pass
    logger.log('discord.errors.LoginFailure has occured. Please check your login token')
    logger.log('SESSION HAS BEEN TERMINATED')
    client.close()











