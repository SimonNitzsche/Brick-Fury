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



con = sqlite3.connect(':memory:')
#con.isolation_level = None
mem = con.cursor()

mem.execute('''CREATE TABLE IF NOT EXISTS bypass
             (serverid bigint, userid bigint, bypass_state bit)''') # SWEAR BYPASS LIST

client = discord.Client()
#client.change_presence(status=dnd)
failsafe = False
ignore = False
file = 'settings.json'

def log(text):
    import time
    time_log = time.strftime("%X", time.localtime(time.time()))
    print('[{}] {}'.format(time_log, text))

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
        
        text = py_tesseract(message_data)
        if text != None:
            message += '\n'
            message += '\n'
            message += text

            log_server = client.get_server('227127903249367041')
            log_channel = discord.utils.get(log_server.channels, name='bot-logs')
            await client.send_message(log_channel, '[IMAGE TEXT] {}'.format(message))
            
            #log(message)

        offenceTime = 0
        msg = message.lower()
        #msg = ''.join(e for e in message.lower() if e.isalnum())
        for exception in fury.execute("SELECT phrase FROM swearexception WHERE serverid = ?", (serverid, )):
            offenceTime -= msg.count('{}'.format(exception[0]))
        for phrase in fury.execute("SELECT phrase FROM swear WHERE serverid = ?", (serverid, )):
            offenceTime += msg.count('{}'.format(phrase[0]))

        #if offenceTime > 0:
        #    watch_server = client.get_server(serverid)
        #    watch_member = watch_server.get_member(userid)
        #    await watch(watch_server, watch_member, 'swear', message)
        
        return offenceTime;

def py_tesseract(message):
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
                image.filter(ImageFilter.MedianFilter())
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(2)
                image.convert('1')
                
                image.filter(ImageFilter.SHARPEN)
            
                #image_id = attachment_info['id']
                #filename = '{}.png'.format(image_id)

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
                log('> Attempting Login.')
                return token;

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
            
        #elif action == 'on_member_update':
            #await client.send_message(channel, '[{}] [PROFILE UPDATED]'.format(user.mention)) 
            
        #elif action == 'on_voice_state_update': # DO NOT ACKNOWLEDGE
            #await client.send_message(channel, '[{}] [VOICE STATE UPDATED]'.format(user.mention))
            
        elif action == 'on_member_ban':
            await client.send_message(channel, '[{}] [USER BANNED]'.format(user.mention))
            
        elif action == 'on_member_unban':
            await client.send_message(channel, '[{}] [USER UNBANNED]'.format(user.mention))


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
    log('> Logged in: {}, {}, Initiated.'.format(client.user.name, client.user.id))
    await client.change_presence(game=discord.Game(name='LEGO Universe'))
    
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
    log('> Removed from {}'.format(server.name))

@client.event
async def on_reaction_add(reaction, user):
    await watch(reaction.message.server, user, 'on_reaction_add', reaction)

#@client.event
#async def on_member_update(before, after):
#    await watch(after.server, after, 'on_member_update', before)

@client.event
async def on_member_ban(member):
    await watch(member.server, member, 'on_member_ban')

@client.event
async def on_member_unban(server, user):
    await watch(server, user, 'on_member_unban')

@client.event
async def on_message_edit(message_before, message):
    if message.server != None: # SERVER LOGS
        await watch(message.server, message.author, 'message_edit', message)
        channel = discord.utils.get(message.server.channels, name='logs')
        if channel != None:
            if message.channel != channel:
                member = message.server.get_member('344569392572530690') # ECHO 
                if member.status == discord.Status.offline: # IF OFFLINE
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
        if admin == False and message.author.bot == False: # START OF SWEAR PROTECTION
        #if message.author.bot == False: # START OF SWEAR PROTECTION
            offenceTime = await swear_filter(message.server.id, message.content, message.author.id, message)
            if offenceTime > 0:
                await client.delete_message(message)
                swearEvent = True
                if offenceTime >= 3:
                    await client.send_message(message.channel, '!mute {} {}'.format(offenceTime, message.author.mention))


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
                if member.status == discord.Status.offline: # IF OFFLINE
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
            log('[DM] [{}#{}] {}'.format(message.author.name, message.author.discriminator, message.content))
            if message.author.id == '85702178525704192' or message.author.id == '227161120069124096' or message.author.id == '173324987665612802' or message.author.id == '172846477683458049':
                if message.content.startswith('.restart'): # PM RESTART
                    await client.send_message(message.channel, '{} is restarting.'.format(client.user.name))
                    log('> Manual PM Restart: {}, {}, Restarting.'.format(client.user.name, client.user.id))
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
                                    offenceTime = swear_filter(arg[args[0]], arg[args[3]], None, None)
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

        if message.content.startswith('.watch '): # WATCH
            unknown_command = False
            if admin:
                msg = message.content[len('.watch '):]
                args = msg.split(' ')
                if len(args) > 0:
                    if args[0] == 'add':
                        if len(message.mentions) > 0:
                            for member_mentions in message.mentions:
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
                        await client.delete_message(message)
                        await client.wait_for_message(timeout=60, author=members)
                        #log('After')
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
                log('> Failsafe Mode: {}, {}, Failsafe Active.'.format(client.user.name, client.user.id))
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
                await client.wait_for_message(timeout=60, author=message.author, check=check)
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
                log('> Manual Restart: {}, {}, Restarting.'.format(client.user.name, client.user.id))
                await client.delete_message(message)
                unknown_command = False
                await client.close()
            else:
                await permission_response(message)
                unknown_command = False
        if message.content.startswith('.members'): # MEMBERS COMMAND
            counter = 0
            x = message.server.members
            for member in x:
                counter += 1
            await client.send_message(message.channel, 'I am currently defending the {} members that are in this guild.'.format(counter))
            unknown_command = False
        elif message.content.startswith('.servers'): # SERVER COMMAND
            counter = 0
            x = client.servers
            for server in x:
                counter += 1
            await client.send_message(message.channel, 'I am currently defending {} guilds.'.format(counter))
            unknown_command = False
            
        swearEvent = False
        if admin == False and message.author.bot == False: # START OF SWEAR PROTECTION
        #if message.author.bot == False: # START OF SWEAR PROTECTION
            offenceTime = await swear_filter(message.server.id, message.content, message.author.id, message)
            if offenceTime > 0:
                swearEvent = True
                if offenceTime >= 3:
                    await client.send_message(message.channel, '!mute {} {}'.format(offenceTime, message.author.mention))


        #if muteMember == False and message.author.bot == False: # START OF SPAM PROTECTION

        if unknown_command == True and message.content.startswith('..') == False:
            await client.send_message(message.channel, 'Sorry {}, but the given command does not currently exist!'.format(message.author.mention))

        if message.content.startswith('.'):
            if ignore:
                blakn = True
            elif message.content.startswith('.restart'):
                if muteMember == False:
                    await client.delete_message(message)
            elif message.content.startswith('..'):
               blakn = True
            else:
                await client.delete_message(message)
        elif swearEvent:
            await client.delete_message(message)

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





















