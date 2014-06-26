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

def loadData(bookDataFilename):        
    global rooms
    global player
    global mobs
    global currentRoomId
    
    logging.info("%s opening...", bookDataFilename)
    if os.path.isfile(bookDataFilename):
        fbook = open(bookDataFilename, 'r')
        s = fbook.read()

        bookJson = json.loads(s)
        entry = bookJson["entry"]
        rooms = bookJson["rooms"]
        player = bookJson["player"]
        mobs = bookJson["mobs"]
        fbook.close()
        
        currentRoomId = entry

        saveFilename = getSaveFilename(bookDataFilename)
        if os.path.isfile(saveFilename):
            fsave = open(saveFilename, 'r')
            s = fsave.read()
        
            if len(s) != 0:
                logging.info("savedata:\n%s\n loaded!", s)
                saveJson = json.loads(s)
                currentRoomId = saveJson["cur_room"]
                logging.info("current room id: %s", currentRoomId)

            fsave.close()
            
        return True
    else:
        logging.error("'%s'DATA NOT FOUND!", bookDataFilename)
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
        if tryLeaveRoom(room, exit):
            currentRoomId = exit["id"]

def tryLeaveRoom(room, exit)
    if exit["event"] != {}:
        if runEvent(exit["event"]):
            runEvent(exit["event"]["success"])
            return True
        else:
            runEvent(exit["event"]["fail"])
            return False
    return True
    
def runEvent(event)
    return True

def main(argv):
    bookDataFilename = ''
    
    try:
        opts, args = getopt.getopt(argv, "hi:d", ["ifile=", "debug"])
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
    
    if loadData(bookDataFilename):
        while True:
            for room in rooms:
                if room["id"] == currentRoomId:
                    printRoomDialog(room)
                    saveGame(bookDataFilename)
        
if __name__ == "__main__":
    main(sys.argv[1:])
