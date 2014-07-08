import json
import os
import sys
import getopt
import random

rooms = {}
player = {}
mobs = {}
difficulty = []
gameoverTexts = {}
currentRoomId = ""

debug = 0

def outputStr(string):
    print string

def debugOutputStr(string, debugLevel):
    global debug
    if (debug >= debugLevel):
        outputStr(string)

def getSaveFilename(bookDataFilename):
    saveGameFilename = bookDataFilename.split(".")[0] + ".sav"
    return saveGameFilename

def diceroll(dice):
    params = getDiceParams(dice)
    result = 0
    count = params["amount"]
    while count > 0:
        result += random.randint(1, params["sides"])
        count -= 1
    result += params["modifier"]
    return result

def getDiceParams(diceString):
    amount = 0
    sides = 0
    modifier = 0
    
    params = diceString.split("d")
    
    amount = int(params[0])
    if "+" in params[1]:
        params = params[1].split("+")
        sides = int(params[0])
        modifier = int(params[1])
    elif "-" in params[1]:
        params = params[1].split("-")
        sides = int(params[0])
        modifier = int(params[1])
    else:
        sides = int(params[1])
        
    result = {"amount": amount, "sides": sides, "modifier": modifier}
    return result

def loadData(bookDataFilename, needLoadSave):        
    global rooms
    global player
    global mobs
    global difficulty
    global currentRoomId
    
    debugOutputStr("%s opening..."%(bookDataFilename), 0)
    if os.path.isfile(bookDataFilename):
        with open(bookDataFilename, 'r') as fbook:
            try:
                s = fbook.read()
                bookJson = json.loads(s)
                entry = bookJson["entry"]
                rooms = bookJson["rooms"]
                player = bookJson["player"]
                mobs = bookJson["mobs"]
                gameoverTexts = bookJson["gameover"]
                difficulty = bookJson["skillcheckDifficulty"]
                fbook.close()
                
                currentRoomId = entry
            except:
                debugOutputStr("File '%s' could not be opened!"%(bookDataFilename), 0)
                sys.exit(2)

        saveFilename = getSaveFilename(bookDataFilename)
        if os.path.isfile(saveFilename) and needLoadSave:
            with open(saveFilename, 'r') as fsave:
                try:
                    s = fsave.read()
                    saveJson = json.loads(s)
                    if "cur_room" in saveJson:
                        currentRoomId = saveJson["cur_room"]
                    if "player" in saveJson:
                        player = json.loads(saveJson["player"])
                    if "mobs" in saveJson:
                        mobsSave = json.loads(saveJson["mobs"])
                        for mobid, mobdata in mobsSave:
                            mobs[mobid]["savedinfo"] = mobdata
                    fsave.close()
                except :
                    debugOutputStr("Save file '%s' could not be opened!\n Using default params."%(saveFilename), 0)
            
        return True
    else:
        debugOutputStr("Data file '%s' is not exist!"%(bookDataFilename), 0)
        return False

def saveGame(bookDataFilename):
    global currentRoomId
    global player
    global mobs
    
    savegame = {}       
    savegame["cur_room"] = currentRoomId
    savegame["player"] = player
    savegame["mobs"] = {}
    for mob in mobs:
        if "savedinfo" in mob:
            savegame["mobs"][mob["id"]] = mob["savedinfo"]
    
    ssave = json.dumps(savegame)
    
    saveFilename = getSaveFilename(bookDataFilename)
    fsave = open(saveFilename, "w")
    fsave.write(ssave)
    fsave.close()
    
def printRoomDialog(room):
    global currentRoomId
    outputStr("________________________")
    outputStr(room["desc"])
    
    encounter = getRoomEncounter(room)
    if encounter != "":
        outputStr(encounter)
        
    outputStr("___________")
    outputStr("Possible exits:")
    for idx, exit in enumerate(room["exits"]):
        outputStr("%d: %s"%(int(idx + 1), getExitDescription(exit)))
    exNum = input("Your choise:")
    if (exNum > 0) and (exNum <= len(room["exits"])):
        exit = room["exits"][exNum - 1]
        if tryLeaveRoom(exit):
            currentRoomId = exit["id"]

def tryLeaveRoom(exit):
    ev = exit["event"]
    if ev != {}:
        return runEvent(ev)
    return True
    
def runEvent(event):
    global player
    global currentRoomId
    
    result = True
    
    if "text" in event:
        outputStr(event["text"])
    else:
        debugOutputStr("Event '%s' text not found!"%(str(event)), 10)
        
    if "type" in event:
        if event["type"] == "damage":
            if tryKill(player, event["param"]):
                gameover("death")
        elif event["type"] == "skillcheck":
            result = checkSkill(player, event["param"], event["modifier"])
        elif event["type"] == "skillinc":
            incSkill(player, event["param"])
        elif event["type"] == "mobbattle":
            mob = getMob(event["param"])
            if "modifier" in mob and not checkMobSavedInfo(mob, "absent", currentRoomId):
                while True:
                    modifier = mob["modifier"] + event["modifier"]
                    hit = checkSkill(player, getCombatSkill(), modifier)
                    outputStr(getAttackDescription(player, hit))
                    if hit:                        
                        if tryKill(mob, 1):
                            result = True
                            break
                    hit = checkSkill(mob, getCombatSkill(), player["modifier"])
                    if hit:
                        if tryKill(player, 1):
                            result = False
                            break
        elif event["type"] == "mobremove":
            mobid, location = event["param"].split("@")
            addMobSavedInfo(getMob(mobid), "absent", location)
        elif event["type"] == "gameover":
            gameOver(event["param"])
            
        debugOutputStr("Event '%s' result: %s"%(event["type"], str(result)), 2)
    else:
        debugOutputStr("Event '%s' type not found!"%(str(event)), 10)
    
    if "events" in event:
        for subevent in event["events"]:
            runEvent(subevent)
    else:
        debugOutputStr("Event '%s' subevents not found!"%(str(event)), 10)
        
    if result:
        if "success" in event:
            runEvent(event["success"])
    elif "fail" in event:
        runEvent(event["fail"])
    
    return result

def tryKill(pretender, amount):
    pretender["hp"] -= amount
    if pretender["hp"] <= 0:
        #pretender is dead
        return True
    return False

def gameOver(gameoverId):
    global gameoverTexts
    
    # Default text for case is all texts are unavailable. Should be never used.
    text = "GAME OVER."
    if gameoverId not in gameoverTexts:
        gameoverId = "default"
        
    if gameoverId in gameoverTexts:
        text = random.choice(gameoverTexts[gameoverId])
    
    outputStr(text)
    sys.exit(1)
        

def checkSkill(pretender, skillid, mod):
    for skill in pretender["skills"]:
        if skill["id"] == skillid:
            skillbase = skill["value"]
            skillval = skillbase + mod
            valtosuccess = pretender["minValToSuccess"]
            debugOutputStr("%s's checkskill: %s, pretenders skill: %d + %d = %d"%(pretender["id"], skillid, skillbase, mod, skillval), 1)
            for i in range(0, skillval):
                dice = diceroll(pretender["diceToSkillcheck"])
                debugOutputStr("dice %s: %d/%d"%(pretender["diceToSkillcheck"], dice, valtosuccess), 1)
                if dice >= valtosuccess:
                    return True
            break
    return False

def incSkill(pretender, skillid):
    for skill in pretender["skills"]:
        if skill["id"] == skillid:
            skill["value"] += 1
            
def getExitDescription(exit):
    global currentRoomId
    
    desc = exit["desc"]
    if exit["event"] != {}:
        extended = ""
        skillid = ""
        mod = 0
        if exit["event"]["type"] == "mobbattle":
            mob = getMob(exit["event"]["param"])
            if not checkMobSavedInfo(mob, "absent", currentRoomId):
                skillid = getCombatSkill()
                mod = mob["modifier"]
        elif exit["event"]["type"] == "skillcheck":
            skillid = exit["event"]["param"]
            
        if skillid != "":
            mod += exit["event"]["modifier"]
            skill = getSkill(skillid)
            mod += skill["value"]
            extended = " (" + skill["name"] + ": " + getSkillcheckDifficulty(mod) + ")"
        desc += extended
    return desc

def getMob(mobid):
    global mobs
    for mob in mobs:
        if mob["id"] == mobid:
            return mob
    return {}

def addMobSavedInfo(mob, type, data):
    if "savedinfo" not in mob:
        mob["savedinfo"] = {}
    if type not in mob["savedinfo"]:
        mob["savedinfo"][type] = []
    mob["savedinfo"][type].append(data)
    
def checkMobSavedInfo(mob, type, data):
    if "savedinfo" not in mob or type not in mob["savedinfo"]:
        return False
    elif data in mob["savedinfo"][type]:
        return True
    else:
        return False

def getSkill(skillid):
    global player    
    for skill in player["skills"]:
        if skill["id"] == skillid:
            return skill
    return {}

def getCombatSkill():
    return "melee"

def getSkillcheckDifficulty(attemptsAmount):
    global player
    global difficulty
    global debug
    
    dice = player["diceToSkillcheck"]    
    minval = player["minValToSuccess"]
    params = getDiceParams(dice)
    dicemin = params["amount"] + params["modifier"]
    dicemax = params["amount"] * params["sides"] + params["modifier"]
           
    percentageToWin = 0
    if minval <= dicemin:
        percentageToWin = 100
    elif minval > dicemax:
        percentageToWin = 0
    else:
        percentageToWin = (dicemax - minval + 1) * 100 / (dicemax - dicemin + 1)
    
    percentageToWin *= attemptsAmount    
    index = int(len(difficulty) * percentageToWin / 100)
    
    if index >= len(difficulty):
        index = len(difficulty) - 1
    if index < 0:
        index = 0
    
    result = ""
    if debug:
        result = "%+d "%(attemptsAmount)
    if difficulty != []:
        result += difficulty[index]
        
    return result

def getRoomEncounter(room):
    for exit in room["exits"]:
        if "type" in exit["event"]:
            if exit["event"]["type"] == "mobbattle":
                mob = getMob(exit["event"]["param"])
                if "desc" in mob and not checkMobSavedInfo(mob, "absent", room["id"]):
                    desc = mob["desc"]
                    hasText = "onappear" in desc and room["id"] in desc["onappear"]
                    if hasText and not checkMobSavedInfo(mob, "appeared", room["id"]):
                        addMobSavedInfo(mob, "appeared", room["id"])
                        return desc["onappear"][room["id"]]
                    elif "default" in desc:
                        return desc["default"]
                    break
    return ""

def getAttackDescription(attacker, isSuccess):
    text = ""
    if "desc" in attacker:
        if "onattack" in attacker["desc"]:
            if isSuccess:
                id = "hit"
            else:
                id = "miss"
            onattack = attacker["desc"]["onattack"]
            if id in onattack:
                text = random.choice(onattack["id"])
    return text

def main(argv):
    global debug
    
    bookDataFilename = ''
    needLoadSave = True
    
    try:
        opts, args = getopt.getopt(argv, "hi:d:n", ["ifile=", "debug", "newgame"])
    except getopt.GetoptError:
        print 'bookgame.py -i <gamefile> -d'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'bookgame.py -i <gamefile> [-d <debuglevel> -n]'
            sys.exit()
        elif opt in ("-i", "--ifile"):
            bookDataFilename = arg
        elif opt in ("-d", "--debug"):
            debug = int(arg)
        elif opt in ("-n", "--newgame"):
            needLoadSave = False            
    
    if loadData(bookDataFilename, needLoadSave):
        while True:
            for room in rooms:
                if room["id"] == currentRoomId:
                    printRoomDialog(room)
                    saveGame(bookDataFilename)
        
if __name__ == "__main__":
    main(sys.argv[1:])
