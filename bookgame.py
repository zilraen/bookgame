import json
import os
import sys
import logging

rooms = {}
currentRoomId = ""

def getSaveFilename(bookDataFilename):
    saveGameFilename = bookDataFilename.split(".")[0] + ".sav"
    return saveGameFilename

def loadData(bookDataFilename):        
    global rooms
    global currentRoomId
    
    logging.info("%s opening...", bookDataFilename)
    if os.path.isfile(bookDataFilename):
        fbook = open(bookDataFilename, 'r')
        s = fbook.read()

        bookJson = json.loads(s)
        entry = bookJson["entry"]
        rooms = bookJson["rooms"]
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
        logging.error("DATA NOT FOUND!")
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
        currentRoomId = room["exits"][exNum]["id"]
        saveGame(bookDataFilename)

def main(argv):
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    
    bookDataFilename = argv[0]
    if loadData(bookDataFilename):
        while True:
            for room in rooms:
                if room["id"] == currentRoomId:
                    printRoomDialog(room)
        
if __name__ == "__main__":
    main(sys.argv[1:])
