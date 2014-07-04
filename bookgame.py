import json
import os
import sys
import getopt
import logging
import random

rooms = {}
player = {}
mobs = {}
difficulty = []
gameoverTexts = {}
currentRoomId = ""

debug = False

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
    
    logging.info("%s opening...", bookDataFilename)
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
                logging.error("File '%s' could not be opened!", bookDataFilename)
                sys.exit(2)

        saveFilename = getSaveFilename(bookDataFilename)
        if os.path.isfile(saveFilename) and needLoadSave:
            with open(saveFilename, 'r') as fsave:
                try:
                    s = fsave.read()
                    logging.info("savedata:\n%s\n loading:", s)
                    saveJson = json.loads(s)
                    if "cur_room" in saveJson:
                        currentRoomId = saveJson["cur_room"]
                        logging.info("current room id: %s", currentRoomId)
                    if "player" in saveJson:
                        player = json.loads(saveJson["player"])
                        logging.info("player data: %s", str(player))
                    if "mobs" in saveJson:
                        mobs["savedinfo"] = json.loads(saveJson["mobs"])
                    fsave.close()
                except :
                     logging.error("Save file '%s' could not be opened!\n Using default params.", saveFilename)
            
        return True
    else:
        logging.error("Data file '%s' is not exist!", bookDataFilename)
        return False

def saveGame(bookDataFilename):
    global currentRoomId
    global player
    global mobs
    
    savegame = {}       
    savegame["cur_room"] = currentRoomId
    savegame["player"] = player
    savegame["mobs"] = mobs["savedinfo"]
    
    ssave = json.dumps(savegame)
    logging.debug("SAVED:\n%s\n------------", ssave)
    
    saveFilename = getSaveFilename(bookDataFilename)
    fsave = open(saveFilename, "w")
    fsave.write(ssave)
    fsave.close()
    
def printRoomDialog(room):
    global currentRoomId
    print "________________________"
    print room["desc"]
    
    encounter = getRoomEncounter(room)
    if encounter != "":
        print encounter
        
    print "___________"
    print "Possible exits:"
    for idx, exit in enumerate(room["exits"]):
        print int(idx + 1), ": ", getExitDescription(exit)
    exNum = input("Your choise:")
    if (exNum > 0) and (exNum <= len(room["exits"])):
        exit = room["exits"][exNum - 1]
        if tryLeaveRoom(exit):
            currentRoomId = exit["id"]

def tryLeaveRoom(exit):
    if exit["event"] != {}:
        if runEvent(exit["event"]):
            runEvent(exit["event"]["success"])
            return True
        else:
            runEvent(exit["event"]["fail"])
            return False
    return True
    
def runEvent(event):
    global player
    
    result = True
    
    if "text" in event:
        print event["text"]
    else:
        logging.debug("Event '%s' text not found!", str(event))
        
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
            if "modifier" in mob:
                while True:
                    modifier = mob["modifier"] + event["modifier"]
                    hit = checkSkill(player, getCombatSkill(), event["modifier"])
                    if hit:
                        if tryKill(mob, 1):
                            result = True
                            break
                    if tryKill(player, 1):
                        result = False
                        break
        elif event["type"] == "gameover":
            gameOver(event["param"])
                
            
        logging.debug("Event '%s' result: %s", event["type"], str(result))
    else:
        logging.debug("Event '%s' type not found!", str(event))
    
    if "events" in event:
        for subevent in event["events"]:
            runEvent(subevent)
    else:
        logging.debug("Event '%s' subevents not found!", str(event))
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
    
    print text
    sys.exit(1)
        

def checkSkill(pretender, skillid, mod):
    for skill in pretender["skills"]:
        if skill["id"] == skillid:
            skillbase = skill["value"]
            skillval = skillbase + mod
            valtosuccess = pretender["minValToSuccess"]
            logging.debug("checkskill: %s, pretenders skill: %d + %d = %d", skillid, skillbase, mod, skillval)
            for i in range(0, skillval):
                dice = diceroll(pretender["diceToSkillcheck"])
                logging.debug("dice: %d/%d", dice, valtosuccess)
                if dice >= valtosuccess:
                    return True
            break
    return False

def incSkill(pretender, skillid):
    for skill in pretender["skills"]:
        if skill["id"] == skillid:
            skill["value"] += 1
            
def getExitDescription(exit):
    desc = exit["desc"]
    if exit["event"] != {}:
        extended = ""
        skillid = ""
        mod = 0
        if exit["event"]["type"] == "mobbattle":
            skillid = "melee"
            mod = getMob(exit["event"]["param"])["modifier"]
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
                if "desc" in mob:
                    desc = mob["desc"]
                    if "onappear" in desc and room["id"] in desc["onappear"]:
                        return desc["onappear"][room["id"]]
                    elif "default" in desc:
                        return desc["default"]
                    break
    return ""

def main(argv):
    global debug
    
    bookDataFilename = ''
    needLoadSave = True
    
    try:
        opts, args = getopt.getopt(argv, "hi:dn", ["ifile=", "debug", "newgame"])
    except getopt.GetoptError:
        print 'bookgame.py -i <gamefile> -d'
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print 'bookgame.py -i <gamefile> -d'
            sys.exit()
        elif opt in ("-i", "--ifile"):
            bookDataFilename = arg
        elif opt in ("-d", "--debug"):
            logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
            debug = True
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
