bookgame
========

Little py-driven engine for book-games AKA tutorial project

usage
--------
bookgame.py -i gamefile -d debuglevel -n

gamefile    path to a game data json

-d          enable extended debug output; necessary detalization should be set as debuglevel (integer from 0 (almost no debug output) to 10 (VERY detailed debug output). I recommend 2)

-n          ignore savegame data and start new game; save is not wiped, but could be overwrite by a new save data though.
