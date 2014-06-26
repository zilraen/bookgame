import json
import os
import sys
import getopt
import logging
import random

rooms = {}
player = {}
mobs = {}
currentRoomId = ""

def getSaveFilename(bookDataFilename):
    saveGameFilename = bookDataFilename.split(".")[0] + ".sav"
    return saveGameFilename

def diceroll(dice):
    params = dice.split("d", 2)
    count = int(params[0])
    sides = int(params[1])
    result = 0
    while count > 0:
        result += random.randint(1, sides)
        count -= 1
    return result

def loadData(bookDataFilename, needLoadSave):        
    global rooms
    global player
    global mobs
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
                    fsave.close()
                except :
                     logging.error("Save file '%s' could not be opened!\n Using default params.", saveFilename)
            
        return True
    else:
        logging.error("Data file '%s' is not exist!", bookDataFilename)
        return False

def saveGame(bookDataFilename):
    global currentRoomId
    
    savegame = {}       
    savegame["cur_room"] = currentRoomId
    savegame["player"] = player
    
    ssave = json.dumps(savegame)
    logging.debug("SAVED:\n%s\n------------", ssave)
    
    saveFilename = getSaveFilename(bookDataFilename)
    fsave = open(saveFilename, "w")
    fsave.write(ssave)
    fsave.close()
    
def printRoomDialog(room):
    global currentRoomId
    
    print room["desc"]
    print "___________"
    print "Possible exits:"
    for idx, exit in enumerate(room["exits"]):
        print int(idx), ":", exit["id"]
    exNum = input("Your choise:")
    if exNum < len(room["exits"]):
        exit = room["exits"][exNum]
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
            tryKill(player, event["param"])
        elif event["type"] == "skillcheck":
            result = checkSkill(player, event["param"], event["modifier"])
        elif event["type"] == "skillinc":
            incSkill(player, event["param"])
            
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

def checkSkill(pretender, skillid, mod):
    for skill in pretender["skills"]:
        if skill["id"] == skillid:
            skillbase = skill["value"]
            skillval = skillbase + mod
            valtosuccess = pretender["minValToSuccess"]
            logging.debug("checkskill: %s, pretenders skill: %d + %d = %d", skillid, skillbase, mod, skillval)
            for i in range(0, skillval):
                dice = diceroll("1d6")
                logging.debug("dice: %d/%d", dice, valtosuccess)
                if dice >= valtosuccess:
                    return True
            break
    return False

def incSkill(pretender, skillid):
    for skill in pretender["skills"]:
        if skill["id"] == skillid:
            skill["value"] += 1

def main(argv):
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
