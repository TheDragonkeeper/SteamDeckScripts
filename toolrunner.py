import os
import shutil
import urllib.request, json
import vdf
import getpass
username = getpass.getuser()
steamappfile = "steamapps.json"
datasheet = ''
reloaded = 0
datafolders = {}

######################## pulls app list and ids from valve  and keeps local uptodate \/
def regrab_list():
    global datasheet
    datasheet = "http://api.steampowered.com/ISteamApps/GetAppList/v0002/"
    with urllib.request.urlopen(datasheet) as url:
        datasheet = json.load(url)

def load_file():
    global datasheet
    try:
        with open(steamappfile) as json_file:
            datasheet = json.load(json_file)
    except:
        regrab_list()
        save_file()

def save_file():
    global datasheet
    data = {}
    for each in datasheet['applist']['apps']:
        data[each['appid']] = each['name']
    with open(steamappfile, 'w') as outfile:
        json.dump(data, outfile)
    load_file()

def reload_file():
    global reloaded
    reloaded = 1
    regrab_list()
    save_file()
#####################################################################################/\

############### finds all screenshots in steam default path and moves them to Pictures folder and renames them using appid \/
def screenshotmover():
    screenshotfolder = "/home/"+username+"/Pictures/Screenshots/"
    if not os.path.exists(screenshotfolder):
        os.makedirs(screenshotfolder)
    mypath = "/home/"+username+"/.local/share/Steam/userdata"
    for (dirpath, dirnames, filenames) in os.walk(mypath):
        if "screenshots" in dirpath:
            for file in filenames:
                if ".jpg" in file or ".png" in file:
                    app = str(str(dirpath).split("remote")[1]).split("/")[1]
                    if str(app) not in datasheet:
                        if reloaded == 0:
                            reload_file()
                    if str(app) not in datasheet:
                        shutil.move(dirpath+"/"+file, screenshotfolder+str(datasheet[str(app)]).replace(" ","-")+"-"+file)
                    else:
                        shutil.move(dirpath+"/"+file, screenshotfolder+str(app)+"-"+file)
            if "thumbnails" in dirpath:
                shutil.rmtree(dirpath, ignore_errors=True)
#######################################################################################/\

################################ Coverts ACF files used by steam to usable dictionaries  \/
def acfTodict(path):
    with open(path, 'r') as json_file:
        info = json_file.readlines()[1:]
        i = 0
        for x in info:
            info[i] = str(info[i]).replace('"\t\t"', '": "')
            if int(i + 1) < len(info) and i != 0:
                nextline = info[int(i + 1)]
                if '{' not in nextline and '}' not in nextline and '{' not in info[i] and '}' not in info[i]:
                    info[i] = info[i].replace('\n', ',\n')
                elif '{' in nextline:
                    info[i] = info[i].replace('\n', ':\n')
                elif '}' in info[i] and '"' in nextline:
                    info[i] = info[i].replace('\n', ',\n')
            i += 1
        info = json.loads(''.join(info))
        return info
########################################  /\

####### used to find data data on game files on system \/
def steam_data():
    global datasheet
    global reloaded
    global datafolders
    ## finds library paths from steam
    lib = '/home/'+username+'/.steam/steam/steamapps/libraryfolders.vdf'
    steamfolders = []
    if os.path.isfile(lib):
        info = acfTodict(lib)
        for libr in info:
            if os.path.isdir(info[libr]["path"]):
                if os.path.isdir(info[libr]["path"]+"/steamapps/"):
                    steamfolders.append(info[libr]["path"]+"/steamapps/")
    ## scan steam paths and construct a dict with data
    ## this is incase steam missed anything
    datafolders = {}
    for folder in steamfolders:
        dataloc = ['workshop/content/' , 'compatdata/', 'shadercache/']
        for loc in dataloc:
            if os.path.isdir(folder+loc):
                for dirnames in os.listdir(folder+loc):
                    if str(dirnames) in datafolders:
                        datafolders[str(dirnames)]["folders"].append(folder+loc+str(dirnames))
                    else:
                        if str(dirnames) not in datasheet:
                            if reloaded == 0:
                                 reload_file()
                        if str(dirnames) in datasheet:
                            if str(dirnames) in datafolders:
                                datafolders[str(dirnames)]["folders"].append(folder+loc+str(dirnames))
                            else:
                                datafolders[str(dirnames)] = {"name": str(datasheet[dirnames]), "appid": str(dirnames), "folders": [folder+loc+str(dirnames)], "installdir": '', "installed": False, 'shortcut': False}
                        else:
                            datafolders[str(dirnames)] = {"name": str(dirnames), "appid": str(dirnames), "folders": [folder+loc+str(dirnames)], "installdir": '', "installed": False, 'shortcut': False}
        ##  look through steams manifests to update dict of data, incase it has values not already added
        man = ["appmanifest_",".acf"]
        for file in os.listdir(folder):
           if man[0] in file and man[1] in file:
               info = acfTodict(folder+file)
               if str(info["appid"]) in datafolders:
                   datafolders[str(info["appid"])]['installdir'] = info["installdir"]
        ## check current known installed games
        for name in os.listdir(folder+'common/'):
            for each in datafolders:
                if str(name) == datafolders[each]['installdir']:
                    datafolders[each]['installed'] = True
                    datafolders[each]['installdir'] = folder+'common/'+datafolders[each]['installdir']
    ##check steams registry to update possible missing names in dict
    reg = '/home/'+username+'/.steam/registry.vdf'
    if os.path.isfile(reg):
        info =  acfTodict(reg)
        apps = info["HKCU"]["Software"]["Valve"]["Steam"]["apps"]
        for each in apps:
            if "name" in apps[each]:
                if each in datafolders:
                    if datafolders[each]["name"] != apps[each]["name"]:
                        if datafolders[each]["name"].isdigit():
                            datafolders[each]["name"] = apps[each]["name"]

    # check the shortcuts records to update names and install paths
    mypath = '/home/'+username+'/.local/share/Steam/userdata'
    for (dirpath, dirnames, filenames) in os.walk(mypath):
        if "shortcuts.vdf" in filenames:
            mypath = dirpath+"/shortcuts.vdf"
            break
    with open(mypath, 'rb') as file:
        content = vdf.binary_load(file)
        for each in content["shortcuts"]:
            item = content["shortcuts"][each]
            ## converts the binary appid to a useable format
            appid = item["appid"] & 0xffffffff
            appid = str(appid)
            if str(appid) in datafolders:
                if datafolders[str(appid)]["name"].isdigit():
                    datafolders[str(appid)]["name"] = item["AppName"]
                pathofbins = str(item["StartDir"]).replace('"','')
                if os.path.isdir(pathofbins):
                    datafolders[str(appid)]["installed"] = True
                    datafolders[str(appid)]['installdir'] = pathofbins
            else:
                if os.path.isdir(item["StartDir"]):
                    datafolders[str(appid)] = {"name": str(item["AppName"]), "appid": str(appid), "installdir": item["StartDir"], "installed": True}
                else:
                    datafolders[str(appid)] = {"name": str(item["AppName"]), "appid": str(appid), "installdir": item["StartDir"], "installed": False}
            datafolders[str(appid)]['shortcut'] = True

#####  just rename values for proton in dict so they have the correct names \/
    for pack in datafolders:
        if datafolders[pack]['name'] == datafolders[pack]['appid']:
            if "Proton" in datafolders[pack]['installdir']:
                values = datafolders[pack]['installdir'].split("/")
                datafolders[pack]['name'] = values[len(values)-1]
######################################################################### /\

def menu():
    global datafolders
    steam_games = []
    non_steam_games = []
    dead_shortcuts = []
    dead_inventory = []
    for game in datafolders:
        if datafolders[game]["installed"] == True and datafolders[game]["shortcut"] == False:
            steam_games.append([datafolders[game]['appid'],datafolders[game]['name']])
        elif datafolders[game]["installed"] == True and datafolders[game]["shortcut"] == True:
            non_steam_games.append([datafolders[game]['appid'],datafolders[game]['name']])
        elif datafolders[game]["installed"] == False and datafolders[game]["shortcut"] == True:
            dead_shortcuts.append([datafolders[game]['appid'],datafolders[game]['name']])
        elif datafolders[game]["installed"] == False and datafolders[game]["shortcut"] == False:
            dead_inventory.append([datafolders[game]['appid'],datafolders[game]['name']])

    print("Steam Games:")
    out = ''
    for each in steam_games:
        out = out + each[1] + "  |  "
    print(out)
    print('_______________________')
    print("Non Steam Games:")
    out = ''
    for each in non_steam_games:
        out = out + each[1] + "  |  "
    print(out)
    print('_______________________')
    print("Useless None Steam data:")
    out = ''
    for each in dead_shortcuts:
        out = out + each[1] + "  |  "
    print(out)
    print('_______________________')
    print("Useless Data:")
    out = ''
    for each in dead_inventory:
        out = out + each[1] + "  |  "
    print(out)
    print('_______________________')

load_file()
screenshotmover()
steam_data()
menu()
