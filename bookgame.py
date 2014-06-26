import json
import os
import sys
import getopt
import logging

rooms = {}
player = {}
mobs = {}
currentRoomId = ""

def getSaveFilename(bookDataFilename):
    saveGameFilename = bookDataFilename.split(".")[0] + ".sav"
    return saveGameFilename

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
                    logging.info("savedata:\n%s\n loaded!", s)
                    saveJson = json.loads(s)
                    currentRoomId = saveJson["cur_room"]
                    logging.info("current room id: %s", currentRoomId)
     
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
    
    ssave = json.dumps(savegame)
    logging.debug("SAVED:\n%s\n------------", ssave)
    
    saveFilename = getSaveFilename(bookDataFilename)
    fsave = open(saveFilename, "w")
    fsave.write(ssave)
    fsave.close()
    
def printRoomDialog(room):
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
    
    if event["type"] == "damage":
        tryKill(player, event["param"])
    elif event["type"] == "skillcheck":
        return checkSkill(player, event["param"], event["modifier"])
    return True

def tryKill(pretender, amount):
    pretender["hp"] -= amount
    if pretender["hp"] <= 0:
        #pretender is dead
        return True
    return False

def checkSkill(pretender, skillid, mod):
    return True

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
