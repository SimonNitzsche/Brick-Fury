class logger:
    def log(text):
        import time
        time_log = time.strftime("%X", time.localtime(time.time()))
        print(f'{tracers.colors.strong.green}[{time_log}] {text}{tracers.colors.reset}')

#class permissions:
   
class json:
    global file
    file = 'settings.json'
    def reader(data_type):
        import os.path
        import json
        import time
        global exists
        global data
        global token
        exists = os.path.isfile(file)

        if exists == False:
            time_log = time.strftime("%X", time.localtime(time.time()))
            token = input("[{}] What is the bot's login token? ".format(time_log))
            json_token = json.dumps({'token': token})
            with open(file, 'w') as json_file:  
                json.dump(json_token, json_file)
            exists = os.path.isfile(file)

        if exists:    
            with open(file) as json_file:
                data = json.load(json_file)
            arg = json.loads(data)
            args = [x for x in arg] # PARSE ARGUMENTS
            for x in args:
                if data_type == 'login':
                    if x == 'token':
                        token = arg[x]
                        return token;
                else:
                    if data_type == x:
                        response = arg[x]
                        return response;

            from functions import json
        raise ValueError(f'Could not find data type "{data_type}" in json file', data_type)

    def write(data_type, value):
        import json
        with open(file) as json_file:
            data = json.load(json_file)
        dump = {data_type: value}
        data = json.loads(data)
        data.update(dump)
        data = str(data).replace('\'', '"')
        with open(file, 'w') as json_file:
            json.dump(data, json_file)

    def update(data_type, value):
        import json
        with open(file) as json_file:
            data = json.load(json_file)
        dump = {data_type: value}
        data = json.loads(data)
        args = [x for x in data] # PARSE ARGUMENTS
        for x in args:
            if data_type == x:
                data[f'{data_type}'] = value
        data = str(data).replace('\'', '"')
        with open(file, 'w') as json_file:
            json.dump(data, json_file)
            
            
class tracers:
    class colors:
        reset = '\033[0m'
        generic = '\033[36m'
        name = '\033[93m'
        message = '\033[92m'
        type = '\033[95m'
        alert ='\033[91m'
        id = '\033[96m'
        time = '\033[92m'
    
        class styles:
            bold = '\033[1m'
            italics = '\033[3m'
            underline = '\033[4m'
            inverse = '\033[7m'
            strikethrough = '\033[9m'
        black = '\033[30m'
        red = '\033[31m'
        green = '\033[32m'
        yellow = '\033[33m'
        blue = '\033[34m'
        magenta = '\033[35m'
        cyan = '\033[36m'
        white = '\033[37m'
        class strong:
            gray = '\033[90m'
            red = '\033[91m'
            green = '\033[92m'
            yellow = '\033[93m'
            blue = '\033[94m'
            magenta = '\033[95m'
            cyan = '\033[96m'
            white = '\033[97m'
        class background:
            black = '\033[40m'
            red = '\033[41m'
            green = '\033[42m'
            yellow = '\033[43m'
            blue = '\033[44m'
            magenta = '\033[45m'
            cyan = '\033[46m'
            white = '\033[47m'
            class strong:
                black = '\033[100m'
                red = '\033[101m'
                green = '\033[102m'
                yellow = '\033[103m'
                blue = '\033[104m'
                magenta = '\033[105m'
                cyan = '\033[106m'
                white = '\033[107m'


