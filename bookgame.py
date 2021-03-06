# -*- coding: utf-8 -*-
import json
import os
import sys
import getopt
import random

rooms = []
player = {}
mobs = []
skills = []
items = []
difficulty = []
inputRequest = []
availableExits = []
gameoverTexts = {}
currentRoomId = ""

debug = 0

def outputStr(string):
    print string

def debugOutputStr(string, debugLevel):
    global debug
    if (debug >= debugLevel):
        outputStr("debug %d/%d: %s"%(debugLevel, debug, string))

def outputLine():
    outputStr("________________________")

def outputShortLine():
    outputStr("___________")

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
    global skills
    global items
    global difficulty
    global inputRequest
    global availableExits
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
                skills = bookJson["skills"]
                items = bookJson["items"]
                gameoverTexts = bookJson["gameover"]
                difficulty = bookJson["skillcheckDifficulty"]
                inputRequest = bookJson["inputRequest"]
                availableExits = bookJson["availableExits"]
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
    global player
    
    outputLine()
    outputStr(room["desc"])
    
    encounter = getRoomEncounter(room)
    if encounter != "":
        outputStr(encounter)
        
    outputShortLine()
    outputStr(getAvailableExits())
    for idx, exit in enumerate(room["exits"]):
        outputStr("%d: %s"%(int(idx + 1), getExitDescription(exit)))
    userInput = raw_input(getInputRequest())
    if userInput in ("skills", "skill", "s"):
        printSkills(player)
    elif userInput in ("items", "item", "i"):
        printItems(player)
    else:
        try:
            exNum = int(userInput)
            if(exNum > 0) and (exNum <= len(room["exits"])):
                exit = room["exits"][exNum - 1]
                if tryLeaveRoom(exit):
                    currentRoomId = exit["id"]
        except ValueError:
            return

def printSkills(mob):
    if "skills" in mob:
        for skillid in mob["skills"].keys():
            skillval = mob["skills"][skillid]
            skillDef = getSkill(skillid)
            outputShortLine()
            outputStr("%s [%+d]:\n%s"%(skillDef["name"], skillval, skillDef["desc"]["default"]))

def printItem(itemid):
    if isValidItem(itemid):
        item = getItem(itemid)
        outputStr("%s:\n%s"%(item["name"], item["desc"]))
        for skillid in item["type"].keys():
            skill = getSkill(skillid)
            modifier = item["type"][skillid]["modifier"]
            outputStr("%s: [%+d]"%(skill["name"], modifier))

def printItems(mob):
    if "slots" in mob:
        outputStr("Equiped:")
        for slotid in mob["slots"].keys():
            itemid = mob["slots"][slotid]
            outputShortLine()
            printItem(itemid)
    if "items" in mob:
        outputStr("\nInventory:")
        for itemid in mob["items"].keys():
            outputShortLine()
            printItem(itemid)

def printMobShortInfo(mob, damage=0):
    name = getName(mob)
    hp = mob["hp"]
    if damage == 0:
        outputStr("%s: %dhp"%(name, hp))
    else:
        outputStr("%s: %dhp -%dhp!"%(name, hp, damage))

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
            result = (checkSkill(player, event["param"], event["modifier"]) > 0)
        elif event["type"] == "skillinc":
            incSkill(player, event["param"])
        elif event["type"] == "additem":
            addItem(player, event["param"])
        elif event["type"] == "removeitem":
            removeItem(player, event["param"])
        elif event["type"] == "mobbattle":
            mob = getMob(event["param"])
            if "modifier" in mob and not checkMobSavedInfo(mob, "absent", currentRoomId):
                while True:
                    modifier = mob["modifier"] + event["modifier"]
                    hit = checkSkill(player, getCombatSkillId(), modifier)
                    if not checkSkill(mob, getDefenceSkillId(), 0, (hit <= 0)):                
                        if tryKill(mob, hit):
                            result = True
                            break
                    hit = checkSkill(mob, getCombatSkillId(), player["modifier"])
                    if not checkSkill(player, getDefenceSkillId(), 0, (hit <= 0)):
                        if tryKill(player, hit):
                            result = False
                            break
                outputShortLine()
        elif event["type"] == "mobremove":
            mobid, location = event["param"].split("@")
            addMobSavedInfo(getMob(mobid), "absent", location)
        elif event["type"] == "gameover":
            gameOver(event["param"])
        elif event["type"] == "echo":
            # donothing, the message is already displayed.
            # it is needed only to avoid a "type not found" error 
            pass
            
        debugOutputStr("Event '%s' result: %s"%(event["type"], str(result)), 2)
    else:
        debugOutputStr("Event '%s' type not found!"%(str(event)), 10)
        
    if result:
        if "success" in event:
            for subevent in event["success"]:
                runEvent(subevent)
    elif "fail" in event:
        for subevent in event["fail"]:
                runEvent(subevent)
    
    return result

def tryKill(pretender, damage):
    printMobShortInfo(pretender, damage)
    pretender["hp"] -= damage
    if pretender["hp"] <= 0:
        #pretender is dead
        return True
    return False

def gameOver(gameoverId):
    global gameoverTexts
    
    # Default text for case if all gameover texts are unavailable. Should be never used.
    text = "GAME OVER."
    if gameoverId not in gameoverTexts:
        gameoverId = "default"
        
    if gameoverId in gameoverTexts:
        text = random.choice(gameoverTexts[gameoverId])
    
    outputStr(text)
    sys.exit(1)
        

def checkSkill(pretender, skillid, mod=0, autosuccess=False):
    succeedCount = 0
    skillval = getSkillWithMods(pretender, skillid, mod)
    valtosuccess = pretender["minValToSuccess"]    
    
    debugOutputStr("%s's checkskill: %s, effective skill: %d, autosuccess: %s"%(pretender["id"], skillid, skillval, str(autosuccess)), 1)
    
    printSkillUseDescription(pretender, skillid)
    
    if autosuccess:
        if skillval > 0:
            succeedCount = skillval
        else:
            succeedCount = 1
    else:
        for i in range(0, skillval):
            dice = diceroll(pretender["diceToSkillcheck"])
            debugOutputStr("dice %s: %d/%d"%(pretender["diceToSkillcheck"], dice, valtosuccess), 1)
            if dice >= valtosuccess:
                succeedCount += 1
        
    if succeedCount > 0:
        printSkillSuccessDescription(pretender, skillid)
    else:
        printSkillFailDescription(pretender, skillid)     
    
    return succeedCount

def incSkill(pretender, skillid):
    if skillid in pretender["skills"]:
        pretender["skills"][skillid] += 1
    else:
        pretender["skills"][skillid] = 1

def isValidItem(itemid):
    return getItem(itemid) != {}

def addItem(pretender, itemid):
    if itemid in pretender["items"]:
        pretender["items"][itemid] += 1
    elif isValidItem(itemid):
        pretender["items"][itemid] = 1

def removeItem(pretender, itemid):
    if itemid in pretender["items"]:
        pretender["items"][itemid] -= 1
        
        if pretender["items"][itemid] <= 0:
            del pretender["items"][itemid]

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
                skillid = getCombatSkillId()
                mod = mob["modifier"]
        elif exit["event"]["type"] == "skillcheck":
            skillid = exit["event"]["param"]
            
        if skillid != "":
            mod += exit["event"]["modifier"]
            
            skillval = getSkillWithMods(player, skillid, mod)
                
            skill = getSkill(skillid)
            if "name" in skill:
                extended = " (" + skill["name"] + ": " + getSkillcheckDifficulty(skillval) + ")"
                
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
    global skills
    for skill in skills:
        if skill["id"] == skillid:
            return skill
    return {}

def getItem(itemid):
    global items
    for item in items:
        if item["id"] == itemid:
            return item
    return {}

def hasSlot(mob, slotid):
    if "slots" in mob:
        if slotid in mob["slots"]:
            return mob["slots"][slotid]
    return None

def equipItem(mob, itemid):
    item = getItem(itemid)
    if "slot" in item:
        slotid = item["slot"]
        slot = hasSlot(mob, slotid)
        if slot is not None:
            unequipItem(mob, slotid)
            mob["slots"][slotid] = itemid

def unequipItem(mob, slotid):
    slotitem = hasSlot(mob, slotid)
    if slotitem is not None:
        addItem(mob, slotitem)
        mob["slots"][slotid] = ""

def getAffectingItems(mob, skillid):
    global items
    affectingItems = []
    if "slot" in mob:
        for slotid in mob["slots"].keys():
            for item in items:
                if item["id"] == mob["slots"][slotid]:
                    if skillid in item["type"]:
                        affectingItems.append(item)
    return affectingItems

def getSkillWithMods(pretender, skillid, mod):
    skillbase = 0
    if skillid in pretender["skills"]:
        skillbase = pretender["skills"][skillid]
        
    affectingItems = getAffectingItems(pretender, skillid)
    itemsBonus = 0
    if len(affectingItems):
        for item in affectingItems:
            itemsBonus += item["type"][skillid]["modifier"]
        
    skillval = skillbase + mod + itemsBonus
    return skillval
    
def getCombatSkillId():
    return "melee"

def getDefenceSkillId():
    return "evasion"

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

def getItemUseDescription(pretender, skillid):
    texts = []
    items = getAffectingItems(pretender, skillid)
    for item in items:
        texts += item["type"][skillid]["use"]
    return texts

def getItemSuccessDescription(pretender, skillid):
    texts = []
    items = getAffectingItems(pretender, skillid)
    for item in items:
        texts += item["type"][skillid]["success"]
    return texts

def getItemFailDescription(pretender, skillid):
    texts = []
    items = getAffectingItems(pretender, skillid)
    for item in items:
        texts += item["type"][skillid]["fail"]
    return texts

def printSkillUseDescription(pretender, skillid):
    text = ""
    texts = []
    skill = getSkill(skillid)
    texts += skill["desc"]["use"]
    texts += getItemUseDescription(pretender, skillid)
    if len(texts) > 0:
        text = random.choice(texts)
        text = text.format(getName(pretender))
        
    if len(text) > 0:
        outputStr(text)

def printSkillSuccessDescription(pretender, skillid):
    text = ""
    texts = []
    skill = getSkill(skillid)
    texts += skill["desc"]["success"]
    texts += getItemSuccessDescription(pretender, skillid)
    if len(texts) > 0:
        text = random.choice(texts)
        text = text.format(getName(pretender))
        
    if len(text) > 0:
        outputStr(text)
    
def printSkillFailDescription(pretender, skillid):
    text = ""
    texts = []
    skill = getSkill(skillid)
    texts += skill["desc"]["fail"]
    texts += getItemFailDescription(pretender, skillid)    
    if len(texts) > 0:
        text = random.choice(texts)
        text = text.format(getName(pretender))
    
    if len(text) > 0:
        outputStr(text)
    
def getInputRequest():
    global inputRequest
    result = random.choice(inputRequest)
    return result

def getAvailableExits():
    global availableExits
    result = random.choice(availableExits)
    return result
    
def getName(mob):
    result = random.choice(mob["name"])
    return result

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
    #main(sys.argv[1:])
    main(["-i", "bookgame.json", "-d", "2", "-n"])
