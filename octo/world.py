"""The world: one big continuous map, with the camera following Octo.

Tile legend
  reef:   '.' sand  ',' seagrass  'd' abyss sand  '#' rock  'C' coral
          'K' kelp (slap to cut)  'v' trench (ink flies over it)
          'R' cracked rock (a bubble bomb blasts it open)
          'I' ice wall (Zappy's shock shatters it)  'G' ghost wall (only Spooky Octo passes)
          'l' lava (Chilly's ice shard cools it into rock)
          'Y' geyser: blasts Octo up to the Sky Islands (and back down)
  shrine/temple: '=' floor  'W' wall  'S' statue  'v' pit  'L' locked door
  Octo Temple pyramid: 'P' lower tier  'Q' upper tier  'H' stairs
          'X' shutter: open until you step into its arena, then it closes
              until every enemy in the arena is beaten

Tiles inside SHRINE_RECT use shrine art and music; everything else is the reef.
validate() runs at startup and checks that the map is rectangular, spawns sit
on floor, and everything can be reached.
"""
from collections import deque

import pygame

import gfx

from settings import TILE

LEVEL = [
    "######################################WWWWWWWWWWWWWWWWWWWW######################################################################################################",
    "#...........................##########W==================W##########...........................#...............................................................#",
    "#.,.K.K.KK.,K..K.,..K.,..KK.##########W==S============S==W##########.......CC.....#..,.........#.....................,,,............,....................,,,...#",
    "#.KKKKK..KKK#KK.KKKK..K..#K.##########W==================W##########.......CC..CC..,...,,......#......................,............,,,.....,..............,....#",
    "#...K.KK,.KKK..,K..KK.K.KK..##########W==================W##########...,CC....CC...CCC......#..#.,.........C...C............,.......,....,.......,..#####......#",
    "#.KK.K,K.#.KKKK.KKKKK,KK....##########W==================W##########...CCC....CC...CC..........#.,,,..........,,,..........,,,###,C....CC,,....#....#...#......#",
    "#......KKK...K,K..KKK.......##########W==================W##########....CC..,...........,......#.,.............,............,#####C......,....###,..#...#,C....#",
    "#..KKKK...#######..K.#K..KK.##########W==================W##########.........CC................#..,....C.....................#####...#.......#####,##...#......#",
    "#..K.K...K#K.K.K#K..K.K...K.##########W==S============S==W##########...#..#.C.............CC...#..............C#...,..C......##########......#########I###.....#",
    "#..K.K.,K,#.K.K.#K.K#K..KK..##########W==================W##########.........C............C.C..I........C.........,,,,........###..#.#.......#######....###..,.#",
    "#.K.KK..#K#K...K#.....KK.K..##########WWWWWWWWWXXWWWWWWWWW##########...,......CC........#.CCC..I...................,C###..,.........,.........######....###.,,.#",
    "#.K.K.K#,K#.K.K.#K,.K...,,K.WWWWWWWWWWWWWWWWWWWLLWWWWWWWWWWWWWWWWWWW..........CCC..............I...###..............######,,.......,,,#...,....#####C.#####..,.#",
    "#.K,....,K#K.K.K#K...K......W=========W==================W=========W.........CCCC..............#...####.,..,.#..###.#######.........,.,.,,,,....###....###.....#",
    "#..K..KK.K###K###...KKKK.K..W=vv===vv=W==================W==vv==vv=W.........CCC.....,.........#..#####...,,##.####.######...........,,,..,.............###....#",
    "#.K.K.K.K....K..KK.K##,KKK,.W=v=====v=W===S==========S===W=========W.,.......C.C.,.............#..#####....,.#.vvvv.,###....#.........,.........###....#####,..#",
    "#..#.K.K.,K,.K..KK,.KKK...K.W=========X==================X====S====W..C.............,.......#..#...###.......vvvvvvvvv..,..###.........,...C...#####.,.#####,,.#",
    "#.,........,.K...K.KK..KKKK.W=========X==================X=========W.CC...................C.C..#.............vvvvvvvvv....,##.........,,,,...C######...#####,..#",
    "#.KKKK#KK..KKKKKKKKK.K...K..W=========X==================X====S====W.CC..........#........C.C..#.............vvvvvvvvv.....,...........,.......#####....###....#",
    "#.#KK..K.,..........K..K.,..W=v=====v=W===S==========S===W=========W...,.,,..,.,...........CC..#............C..vvvvv###..,.....C.,..........Y...###..........C.#",
    "#.......K..K....KKKKKK.K,.K.W=vv===vv=W==================W==vv==vv=W.,.......,......#.,........#..................######,,,.,................,.................#",
    "#..K..K..KKK.,.#...K.KK.K#K.W=========W==================W=========W...........................#..............,#########.,,,.,,....,...........................#",
    "#...........................WWWWWWWWWWWWWWWWWW====WWWWWWWWWWWWWWWWWW...........................#..............###########.,#.,,,..#............................#",
    "#####....######....######..............#######....#######..............#########.....###########....,..,......#####.#####.....,........#..............#....CC..#",
    "#.......................#..............##....,.........##,...........,.#ddddddddddddddddddddddd#...,,,........#####,#####.....,....,.CC........................#",
    "#...#,...........,......#.KK.....,.....##,.............##..............#ddddddddddddddddddddddd#...............###...###.........,,,,.......#..................#",
    "#.......C...........,...#.K..K...KK.KKKKKKK............##.....CC.CC,...#ddddddddddddddddd#ddddd#...............................................................#",
    "#..,.,..#...............#..K.K..,K.K.KKKKKK.......,....##.....C...C....#ddddddddddddddddddddddd#####II##########################################################",
    "#.....................,...K.........KKKKKKK............##......C.......#dddvvvdddddddd#######dd#.................ll.....................ll.....................#",
    "#....C....Y.,.....,...C..........,...KKKKKK............##.....C...C....#ddvvdddddddddd#ddddd#dd#.,,...............ll,,,,,,..v...........ll..................,..#",
    "#......,..............C...........KK...##..............##.....CC.CC....#ddvvdddddddddv#ddddd#dd#.,................ll.,,.,..#####........ll....v............,,,.#",
    "#.....,..,..,C,.........#.K.......K....##..............##.,............#dddddddddvvvvv#ddddd#dd#...........,......ll.......#...#.......ll...#vvv....###..###,..#",
    "#.....,........,........#........K....#vvvvvvvvvvvvvvvvvv#......,......#dddddddddddddd#ddddd#dd#.......#..,,,....ll,.......#...#.......ll..###v....##########..#",
    "#..........C.......C....#..KKK...K.KK.#vvvvvvvvvvvvvvvvvv#.,...,.......#dddddddddddddd###R###dd#......###..,.v...ll........#...##.......ll..#......##########..#",
    "#......,.vvvvv.....,....#......,......#vvvvvvvvvvvvvvvvvv#####.,..######ddddddddddddddddddddddd#.......#....vvv..ll.....v..##.##........ll..,......##########..#",
    "#..,...vvvvvvvvv........#......,.....,.................,##.............#dddddddddddddddddddvvvd#.............v...ll..#.............#....ll.,,#,.....###..###...#",
    "#.....vvvvvvvvvvv...#...#.........................C.....##.,...........#dddddvvvvvvdddddddd#ddd#..........###.....ll...................ll,..###,.....#.........#",
    "#....vvvvvvvvvvvvv..,...#.............CC....C,..........##........,.....dddvvvddddddddddddddddd#.........#####....ll...#..###.........#ll,,.###......#.........#",
    "#..#.vvvvvvvvvvvvv...,................CC......................,.........ddvvvdddddddd#vvddddddd#.....,..,#####....ll..########..,......#ll,######..............#",
    "#....vvvvv...vvvvv........C.............................................dvvdddddddddddvvdddddddd....,,,,,#####...ll....#.#####v........,ll,#######.........###.#",
    "#....vvvvvvvvvvvvv,C.,......................,,...................vvvv...dddddddd#ddddddvvddddddd....,,###..##....ll....,.#####..,.......llv########.......####.#",
    "#....vvvvvvvvvvvvv.,........................,..........................#dddddddddddddddvvddddddd.....#####.......ll.......###..,,,.....llv,########.......####.#",
    "#....,vvvvvvvvvvv.,C....#.............CC.....,......C,..##.............#dddddd#ddddddd#vvvdddddd....,#####.......ll.....,.......,.#....ll,,########.......####.#",
    "#......vvvvvvvvv........#.......,.....CC....,.....,.....##.............#dddddddddddddvvvddddddd#.....#####........ll....................ll,#######........####.#",
    "#........vvvvv....C.....#....,........CC..C..........,..##.............#ddddddd#ddddddddddddddd#......###..#....,.ll....................ll,.###..........###...#",
    "#..,....#.C..........C..#####.....##########........##########,....#####ddddddddddddd#dvvvddddd#..........###..,,,ll....................ll,#..............#....#",
    "#.,.,C............#####.#..........,...#..........,.....#.......,...vvv#dddddddddddddd#vvdddddd#.###.....#....#.,ll..........v.........ll,,......#.............#",
    "#....,............#...#.#.WWWWWWWWW....#...PPPPPPPP.....#...........vvv#dddddddddddddddvvdddddd#.####...###....#.ll...................,ll,......###............#",
    "#...,....C,C.....,#...#.#.W=======W....#...PQQQQQQP.....................dddddddddddddddvvdddddd#.####....#.......ll......v.......,.....,ll.,..,..#......###....#",
    "#.....C..,.......,##R##.#.W=======W.....,..PQ====QP...,.....vv.....,....ddddddddddddddddddddddd#.####............ll.....vvv.....,,,.....ll,,,,,,......######...#",
    "#.....,C....,...........#.W=======W........PQ====QP..Y......vv..........ddddddddddddddddddddddd#.####........#....ll.....v......,,,.....ll.,..,..v....,#####...#",
    "#..#............,....,..#.W=======W.....,..PQ====QP.....C...vv..........ddddddddddddddddddddddd#.###........###...ll.....#.......v.....ll..............#####...#",
    "#..C......,.C...........#.WWWW=WWWW........PQ====QP.,...#...vv.........#dd#dddd#ddddddddddddddd#..........v..#....ll.........,..vvv....ll........#.....,###....#",
    "#....,..................#...C..........#...PQQHHQQP.....#.,..........vv#ddddddddddddddddddddddd#.................ll.....................ll.....................#",
    "#......C...C...C..,.....#..............#...PPPHHPPP.....#vv,.,...,...vv#ddddddddddddddddddddddd#################################################################",
    "#.......................#..............#.....S..S.......#vv..........vv#ddddddddddddddddddddddd#...............................................................#",
    "#########.....################....############....############....##################.....#######........C..,......C.......C...WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW.#",
    "#..............................................................................................#.....C....................C...W==============================W.#",
    "#..,.....................#C#...............,.,.........,..#..............,........,........,...#.#.........C.#.C...#.....#,...W===S==================S=======W.#",
    "#............C...................,........,.....................,.........,....................#..C.................,..#......W==============================W.#",
    "#...##########.....C.C.,....,...............,......,.......#........###########...C............#..C................,,,###.....W==============================W.#",
    "#.#.#........#....................,...##########.......,.........C..#..,..,..#.........,.C.....#....................,..#...C..W==============================W.#",
    "#...#....#...#.............#..,.......#.,......#....,.,...C...,.....#..,.....#.....C.........,.#..............................W==============================W.#",
    "#.,.#........#......,..,..........#...#......,C#.....,............C.#........#,,...............#......C,,,,.............,.....W===S==================S=======W.#",
    "#...#..C.....#....C...#.C.....,..,....#........#.................,..#....C...#C.C........,.....#.#.....#,,,,.#...C.#.,.,,#....W==============================W.#",
    "#...######..##........................#..#######..........C.#.......###..#####.................#..,.......,.........,,,.,.....W==============================W.#",
    "#........C..,..........,...........................................C........C......C.........C.#...,.................,........WWWWWWWWWWWWWWWLLWWWWWWWWWWWWWWW.#",
    "#..........#......#C############.#....,..C,....#.,...,...................,...C.C......,........G...,C...C....,...C.......C.C..W=============W================W.#",
    "#....,..,.C.........#..........#............,....C....,.......#......C.........C..##########...G...,........,,,.......#.......W=============W================W.#",
    "#..,,.........C.....#..........#....................############.#...........#...##...,....#...G.............,...,..,###,.....W==S======S===W===S======S=====W.#",
    "#.,C...,............#..........#...................,#.C........#..C.#C..........,.##......##...#.....,.##....#..,,,#,,#,,#,...W=============W================W.#",
    "#.....,.........,..,#.........C#C.........C.........#C....C....#.,.........#.....C#........#C..#....,#,###....#####..,..,#....W=============W================W.#",
    "#.......########..#.#########..#..,.....,...........#..,.......#........,.........#...C.,..#C..#.....,..#.....#...#.....###...W=============X================W.#",
    "#..,....#......#C..............,......#.,...........#....C...,.#........#######...#.C#######...#...........,..#...R....,.#....W=============W================W.#",
    "#.....#.#......#.......#......,.,....,.......C......#..#########C.#,..,.#.....#...,..,.....C#..#....,.....,,,.#...#...,,,.....W==S======S===W===S======S=====W.#",
    "#.......#...,C.#C.......,......#............,..#...........C.....#.C....#.....##....#..,.......#....,......,..#####,,,.,.#.,..W=============W================W.#",
    "#.......#,..#..#......................,.C.........#,............,......,#.....#................#.#.,,,.#.....#.,...#,...###...W=============W================W.#",
    "#......,####..##.....C............,......C.#..,..,C.......,.,...........###..##................#....,.........#,,........#.#..W=============W================W.#",
    "#.....,.,......C....,...............,.,...........C.#..,....,......C.....,........,......C..,,.#.......#.......,.,............WWWWWWWWWWWWWWWWWWWWWW==WWWWWWWW.#",
    "#..............................................................................................#...............................................................#",
    "################################################################################################################################################################",
    "WWWWWWWWWWWWWWWW####WWWWWWWWWWWWWWWW####WWWWWWWWWWWWWWWW####WWWWWWWWWWWWWWWW####WWWWWWWWWWWWWWWW####WWWWWWWWWWWWWWWW####WWWWWWWWWWWWWWWW########################",
    "W==============W####W==============W####W==============W####W==============W####W==============W####W==============W####W==============W########################",
    "W==============W####W=vvv==vv==vvv=W####W==============W####W==============W####W=vv========vv=W####W=WWW=WWWW=WWW=W####W==v========v==W########################",
    "W===S======S===W####W=v====vv====v=W####W===v======v===W####W===S======S===W####W=v==========v=W####W=W==========W=W####W==============W########################",
    "W==============W####W===vv====vv===W####W==============W####W==============W####W======SS======W####W=W=WWW==WWW=W=W####W======vv======W########################",
    "W==============W####W==============W####W==============W####W==============W####W==============W####W==============W####W==============W########################",
    "W==============W####W===vv====vv===W####W==============W####W==============W####W======SS======W####W=W=WWW==WWW=W=W####W======vv======W########################",
    "W===S======S===W####W=v====vv====v=W####W===v======v===W####W===S======S===W####W=v==========v=W####W=W==========W=W####W==============W########################",
    "W==============W####W=vvv==vv==vvv=W####W==============W####W==============W####W=vv========vv=W####W=WWW=WWWW=WWW=W####W==v========v==W########################",
    "W==============W####W==============W####W==============W####W==============W####W==============W####W==============W####W==============W########################",
    "WWWWWWWWWWWWWWWW####WWWWWWWWWWWWWWWW####WWWWWWWWWWWWWWWW####WWWWWWWWWWWWWWWW####WWWWWWWWWWWWWWWW####WWWWWWWWWWWWWWWW####WWWWWWWWWWWWWWWW########################",
    "################################################################################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv..vvvvvvvvvvvvvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvv..vvvvvvvvvv.....vvvvvvvvvvvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvv........vvvvvvv.......vvvvvvvvvvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvv..........vvvvvv.....vvvvvvvvvvvvvv.vvvvvv####################################################################################################",
    "vvvvvvv.,vvvvvvvvv.........==========.vvvvvvvvvvv....,.Cvvvv####################################################################################################",
    "vvvvv.......vvvvv.,........vvv=vvvvvvvvvvvv..vvvv.......vvvv####################################################################################################",
    "vvvv..........vvvvv.......vvvv=vvvvvvvvvv......vv...Y....vvv####################################################################################################",
    "vvv............vvvvvvv.vvvvvvv=vvvvvvvvv................vvvv####################################################################################################",
    "vv......Y......========vvvvvvv=vvvvvvvv................vvvvv####################################################################################################",
    "vvv........C..vvvvvvvvvvvvvvvv=vvvvvvv............vv..vvvvvv####################################################################################################",
    "vvv..........vvvvvvvvvvvvvvvvv=vvvvvvvv...........===vvvvvvv####################################################################################################",
    "vvvvv.,.....vvvvvvvvvvvvvvvvvv=vvvvvvv.............vvvvvvvvv####################################################################################################",
    "vvvvvvvv.vvvvvvvvvvvvvvvvvvvvv=vvvvvvvvv..........vvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvv=vvvvvvvvv.........vvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvv=vvvvvvvvvv.......vvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvvvvvvvvv..vv.vvvvvvvvvv..vvvvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvvvvv.v.......v.vvvvvvvv=vvvvvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvvv.............vvvvvvvv=vvvvvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvv................vvvvvv=vvvvvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvvv...............vvvvvv=vvvvvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvv.................=========vvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvv.vvvvvvv................vvvvvvvvv=vvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvv........vvvvv..............vvvvvvvvv.=vvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvv..........vvv.v........C..v.vvvvvv......Cvvvvvvvvv####################################################################################################",
    "vvvvvvvvv...........vvvvv.........vvvvvvvvv.........vvvvvvvv####################################################################################################",
    "vvvvvvvv......Y......vvvvvv.vv..vvvvvvvvvv............vvvvvv####################################################################################################",
    "vvvvvvvv............vvvvvvvvvvvvvvvvvvvvv........C...vvvvvvv####################################################################################################",
    "vvvvvvvvv..........vvvvvvvvvvvvvvvvvvvvvvv...........vvvvvvv####################################################################################################",
    "vvvvvvvvvvv.......vvvvvvvvvvvvvvvvvvvvvvvv.C.........vvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvv..vvvvvvvvvvvvvvvvvvvvvvvvvvvv........vvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv..vvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv####################################################################################################",
    "vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv####################################################################################################",
]
LEVEL_W, LEVEL_H = len(LEVEL[0]), len(LEVEL)
# each region has its own look (tiles, tint, particles) and some their own music
THEMES = {
    'KELP WOODS': 'kelp', 'CORAL GARDENS': 'garden', 'THE LAGOON': 'lagoon', 'THE ABYSS': 'abyss',
    'SHIP GRAVEYARD': 'wreck', 'FROZEN SHELF': 'frost', 'EMBER VENTS': 'vents', 'SUNKEN CITY': 'city',
    'MURK PALACE': 'city', 'SKY ISLANDS': 'sky',
}
REGION_MUSIC = {'SKY ISLANDS': 'sky', 'FROZEN SHELF': 'frost', 'EMBER VENTS': 'vents', 'SUNKEN CITY': 'city', 'MURK PALACE': 'city'}
DARK_REGIONS = {'SUNKEN CITY', 'MURK PALACE'}
SKY_Y = 92               # rows from here down are the Sky Islands
SKY_RECT = (0, 92, 59, 127)
GEYSERS = [((53, 49), (8, 102)), ((10, 28), (14, 119)), ((140, 18), (52, 100))]   # (sea tile, sky tile) pairs
# one mini-boss guards each region: (style id, tile x, tile y) -- see entities.MINIBOSS_STYLES
MINIBOSSES = [('pinch', 48, 28), ('wraith', 13, 20), ('thorn', 83, 14), ('blowhard', 16, 31),
              ('gloom', 82, 44), ('captain', 50, 64), ('frostmaw', 115, 7), ('magma', 118, 41),
              ('warden', 107, 66), ('storm', 33, 113)]
WORLD_H = 80             # rows below this are the trial rooms, reached only by portal

# Trial portals: step in, get warped to a one-screen trial room, win a new form.
#   room: tile rect of the room (walls included), exactly one screen big
#   portal: where the portal sits in the world; Octo lands just below it afterwards
TRIALS = {
    'storms': {
        'title': 'TRIAL OF STORMS', 'form': 'zap', 'kind': 'waves',
        'room': (0, 80, 15, 90), 'entry': (7.5, 5), 'portal': (83, 6),
        'goal': "DEFEAT THREE WAVES OF ENEMIES!",
        'waves': [
            ['crab', 'crab', 'crab', 'crab', 'crab', 'puffer', 'puffer'],
            ['jelly', 'jelly', 'jelly', 'urchin', 'urchin', 'crab', 'crab', 'puffer'],
            ['puffer', 'puffer', 'puffer', 'jelly', 'jelly', 'jelly', 'urchin', 'crab', 'crab', 'crab', 'crab'],
        ],
        'spots': [(2, 2), (13, 2), (2, 8), (13, 8), (7, 1), (8, 9), (1, 5), (14, 5), (5, 5), (10, 5), (7, 8)],
    },
    'currents': {
        'title': 'TRIAL OF CURRENTS', 'form': 'ice', 'kind': 'collect',
        'room': (20, 80, 35, 90), 'entry': (7.5, 5), 'portal': (48, 58), 'time': 30,
        'goal': "GRAB ALL 10 ORBS IN 30 SECONDS!",
        'orbs': [(3, 3), (12, 3), (1, 5), (14, 5), (7, 4), (8, 6), (3, 7), (12, 7), (5, 1), (10, 9)],
        'guards': [('puffer', 1, 1), ('puffer', 14, 1), ('puffer', 1, 9), ('puffer', 14, 9),
                   ('jelly', 3, 5), ('jelly', 12, 5)],
    },
    'frost': {
        'title': 'TRIAL OF FROST', 'form': 'bubble', 'kind': 'survive',
        'room': (60, 80, 75, 90), 'entry': (7.5, 5), 'portal': (128, 13), 'time': 25,
        'goal': "DODGE THE URCHIN STORM FOR 25 SECONDS!", 'eyes': [], 'fast': 2.2,
        'guards': [('urchin', 2, 2), ('urchin', 13, 2), ('urchin', 2, 8), ('urchin', 13, 8),
                   ('urchin', 7, 2), ('urchin', 8, 8)],
    },
    'embers': {
        'title': 'TRIAL OF EMBERS', 'form': 'spiky', 'kind': 'waves',
        'room': (80, 80, 95, 90), 'entry': (7.5, 5), 'portal': (150, 40),
        'goal': "DEFEAT THREE WAVES OF FIERY FOES!",
        'waves': [
            ['lavacrab', 'lavacrab', 'lavacrab', 'lavacrab', 'puffer', 'puffer'],
            ['lavacrab', 'lavacrab', 'lavacrab', 'urchin', 'urchin', 'jelly', 'jelly'],
            ['lavacrab', 'lavacrab', 'lavacrab', 'lavacrab', 'puffer', 'puffer', 'jelly', 'jelly', 'urchin'],
        ],
        'spots': [(2, 1), (13, 1), (1, 5), (14, 5), (4, 9), (11, 9), (4, 1), (11, 1), (1, 9), (14, 9),
                  (5, 5), (10, 5)],
    },
    'echoes': {
        'title': 'TRIAL OF ECHOES', 'form': 'glow', 'kind': 'collect',
        'room': (100, 80, 115, 90), 'entry': (7.5, 5), 'portal': (104, 59), 'time': 35,
        'goal': "GRAB ALL 12 ORBS IN THE MAZE IN 35 SECONDS!",
        'orbs': [(1, 1), (14, 1), (1, 9), (14, 9), (5, 2), (10, 8), (3, 3), (12, 7), (7, 4), (8, 6),
                 (7, 1), (8, 9)],
        'guards': [('jelly', 3, 5), ('jelly', 12, 5), ('puffer', 1, 5), ('puffer', 14, 5)],
    },
    'winds': {
        'title': 'TRIAL OF WINDS', 'form': 'air', 'kind': 'waves',
        'room': (120, 80, 135, 90), 'entry': (7.5, 5), 'portal': (42, 106),
        'goal': "FEND OFF THREE WAVES OF SKY RAIDERS!",
        'waves': [
            ['gull', 'gull', 'gull', 'gull', 'gull'],
            ['gull', 'gull', 'gull', 'gull', 'puffer', 'puffer'],
            ['gull', 'gull', 'gull', 'gull', 'gull', 'gull', 'jelly', 'jelly'],
        ],
        'spots': [(2, 1), (13, 1), (1, 5), (14, 5), (2, 9), (13, 9), (5, 1), (10, 9), (4, 5), (11, 5)],
    },
    'shadows': {
        'title': 'TRIAL OF SHADOWS', 'form': 'ghost', 'kind': 'survive',
        'room': (40, 80, 55, 90), 'entry': (7.5, 8), 'portal': (80, 40), 'time': 25,
        'goal': "SURVIVE THE BARRAGE FOR 25 SECONDS!",
        'eyes': [(7.5, 5), (1.5, 1.5), (13.5, 1.5), (1.5, 8.5), (13.5, 8.5)],
    },
}
SHRINE_RECT = (28, 0, 67, 21)     # tiles (x0, y0, x1, y1) of the Sunken Shrine

REGIONS = [   # (banner name, tile rect x0, y0, x1, y1); anywhere else is the Coral Reef
    ('OCTO TEMPLE', (43, 46, 50, 53)),
    ('PEARL SHOP', (27, 47, 33, 50)),
    ('MURK PALACE', (126, 55, 157, 77)),
    ('FROZEN SHELF', (96, 1, 158, 25)), ('EMBER VENTS', (96, 27, 158, 52)), ('SUNKEN CITY', (96, 54, 158, 78)),
    ('TRIAL OF FROST', (60, 80, 75, 90)), ('TRIAL OF EMBERS', (80, 80, 95, 90)),
    ('TRIAL OF ECHOES', (100, 80, 115, 90)), ('TRIAL OF WINDS', (120, 80, 135, 90)),
    ('SKY ISLANDS', (0, 92, 59, 127)),
    ('TRIAL OF STORMS', (0, 80, 15, 90)), ('TRIAL OF CURRENTS', (20, 80, 35, 90)),
    ('TRIAL OF SHADOWS', (40, 80, 55, 90)),
    ('SUNKEN SHRINE', (28, 0, 67, 21)),
    ('KELP WOODS', (1, 1, 27, 21)),
    ('CORAL GARDENS', (68, 1, 94, 21)),
    ('THE LAGOON', (1, 23, 23, 54)),
    ('THE ABYSS', (72, 23, 94, 54)),
    ('SHIP GRAVEYARD', (1, 56, 94, 78)),
]

START = (46.5, 49.5)     # tile coords of Octo's spawn: the sanctuary on top of the Octo Temple pyramid
SHRINE_CHECKPOINT = (47.5, 19)
NPC = ('shelly', 43, 54)
SHOPKEEPER = (30, 47)     # Hermie the hermit crab, behind the counter
SHOP_ROW = 49            # tile row the wares sit on

# (kind, tile x, tile y)
ENEMIES = [
    # central plaza
    ('crab', 42, 37), ('crab', 52, 36), ('crab', 48, 41),
    # west reef
    ('crab', 29, 36), ('crab', 34, 41), ('jelly', 32, 38),
    # kelp forest
    ('jelly', 29, 27), ('jelly', 32, 24), ('crab', 30, 30),
    # shrine approach
    ('puffer', 43, 25), ('puffer', 52, 25), ('crab', 45, 28), ('crab', 51, 29),
    # coral cliffs
    ('urchin', 60, 24), ('urchin', 68, 30), ('puffer', 64, 31),
    # urchin field
    ('urchin', 60, 36), ('urchin', 68, 37), ('urchin', 64, 42), ('crab', 59, 41),
    # the trench
    ('puffer', 59, 46), ('puffer', 66, 51), ('jelly', 64, 48),
    # shipwreck
    ('crab', 35, 46), ('crab', 29, 53), ('puffer', 36, 52),
    # shrine: great hall
    ('crab', 41, 13), ('crab', 54, 19), ('urchin', 44, 16), ('urchin', 51, 16), ('puffer', 48, 13),
    # shrine: jelly pool (arena)
    ('jelly', 31, 16), ('jelly', 35, 14), ('jelly', 35, 18), ('urchin', 33, 12),
    # shrine: key vault (arena)
    ('crab', 59, 12), ('crab', 65, 20), ('urchin', 64, 16), ('puffer', 65, 12), ('jelly', 59, 20),
    # shrine: throne (arena)
    ('shark', 46, 3),
    # kelp woods
    ('jelly', 17, 10),
    ('jelly', 23, 9),
    ('jelly', 15, 5),
    ('jelly', 12, 8),
    ('crab', 6, 19),
    ('crab', 8, 12),
    ('crab', 22, 11),
    # the lagoon
    ('crab', 4, 43),
    ('crab', 16, 43),
    ('crab', 12, 26),
    ('crab', 5, 25),
    ('jelly', 3, 27),
    ('jelly', 17, 51),
    ('puffer', 18, 35),
    # coral gardens
    ('urchin', 75, 17),
    ('urchin', 78, 9),
    ('urchin', 91, 13),
    ('urchin', 88, 5),
    ('puffer', 77, 5),
    ('puffer', 71, 9),
    ('puffer', 85, 8),
    ('crab', 89, 10),
    # the abyss
    ('jelly', 76, 31),
    ('jelly', 82, 52),
    ('jelly', 77, 29),
    ('jelly', 90, 30),
    ('puffer', 82, 33),
    ('puffer', 82, 26),
    ('puffer', 77, 38),
    ('urchin', 81, 45),
    ('urchin', 86, 25),
    # ship graveyard
    ('crab', 40, 64),
    ('crab', 92, 59),
    ('crab', 35, 69),
    ('crab', 48, 71),
    ('crab', 32, 73),
    ('puffer', 72, 60),
    ('puffer', 13, 70),
    ('puffer', 79, 64),
    ('urchin', 65, 66),
    ('urchin', 8, 58),
    ('jelly', 67, 72),
    ('jelly', 54, 73),
    # --- east expansion ---
    ('icecrab', 105, 12),
    ('icecrab', 103, 24),
    ('icecrab', 120, 16),
    ('icecrab', 128, 21),
    ('icecrab', 100, 21),
    ('icecrab', 112, 19),
    ('icecrab', 157, 17),
    ('icecrab', 155, 11),
    ('icecrab', 125, 24),
    ('icecrab', 141, 22),
    ('icecrab', 129, 24),
    ('jelly', 148, 2),
    ('jelly', 105, 7),
    ('jelly', 122, 21),
    ('jelly', 117, 9),
    ('puffer', 143, 20),
    ('puffer', 106, 10),
    ('puffer', 137, 21),
    ('puffer', 108, 21),
    ('urchin', 132, 3),
    ('urchin', 107, 18),
    ('urchin', 135, 9),
    ('urchin', 99, 23),
    ('lavacrab', 111, 51),
    ('lavacrab', 112, 38),
    ('lavacrab', 98, 34),
    ('lavacrab', 151, 44),
    ('lavacrab', 104, 38),
    ('lavacrab', 99, 29),
    ('lavacrab', 147, 46),
    ('lavacrab', 102, 44),
    ('lavacrab', 103, 50),
    ('lavacrab', 139, 30),
    ('lavacrab', 120, 32),
    ('lavacrab', 122, 43),
    ('puffer', 129, 38),
    ('puffer', 105, 35),
    ('puffer', 127, 42),
    ('puffer', 134, 44),
    ('puffer', 144, 43),
    ('urchin', 118, 41),
    ('urchin', 134, 45),
    ('urchin', 123, 46),
    ('urchin', 155, 37),
    ('urchin', 141, 49),
    ('jelly', 110, 55),
    ('jelly', 122, 78),
    ('jelly', 117, 67),
    ('jelly', 117, 58),
    ('jelly', 117, 73),
    ('jelly', 119, 64),
    ('puffer', 116, 62),
    ('puffer', 100, 76),
    ('puffer', 111, 65),
    ('puffer', 116, 74),
    ('urchin', 116, 67),
    ('urchin', 115, 64),
    ('urchin', 99, 59),
    ('lavacrab', 98, 63),
    ('lavacrab', 119, 57),
    ('lavacrab', 119, 64),
    ('lavacrab', 118, 77),
    ('lavacrab', 130, 67),
    ('lavacrab', 137, 74),
    ('jelly', 133, 70),
    ('jelly', 129, 75),
    ('puffer', 137, 67),
    ('puffer', 131, 72),
    ('murk', 141, 59),
    # --- sky islands ---
    ('gull', 22, 98),
    ('gull', 30, 112),
    ('gull', 33, 116),
    ('gull', 44, 105),
    ('gull', 47, 121),
    ('gull', 16, 118),
    ('gull', 10, 101),
    ('gull', 26, 114),
]

# placed treasure and food: (kind, tile x, tile y)
ITEMS = [
    ('container', 64, 27),
    ('bluepearl', 19, 46), ('bluepearl', 21, 46), ('bluepearl', 20, 47),
    ('bluepearl', 68, 47),
    # snacks: each shrimp restores half a heart
    ('shrimp', 34, 34), ('shrimp', 54, 52), ('shrimp', 68, 41), ('shrimp', 43, 23),
    ('shrimp', 40, 20),
    # kelp woods
    ('shrimp', 7, 7),
    ('shrimp', 20, 10),
    ('bluepearl', 3, 12),
    ('container', 13, 10),
    # the lagoon
    ('shrimp', 19, 50),
    ('shrimp', 7, 46),
    ('bluepearl', 15, 45),
    # coral gardens
    ('shrimp', 76, 16),
    ('shrimp', 84, 12),
    ('bluepearl', 87, 12),
    ('bluepearl', 83, 19),
    # the abyss
    ('shrimp', 91, 31),
    ('shrimp', 75, 48),
    ('bluepearl', 83, 47),
    ('container', 89, 29),
    # ship graveyard (one pearl hidden in every wrecked hull)
    ('shrimp', 83, 75),
    ('shrimp', 92, 69),
    ('shrimp', 24, 64),
    ('bluepearl', 8, 61),
    ('bluepearl', 25, 68),
    ('bluepearl', 42, 62),
    ('bluepearl', 57, 70),
    ('bluepearl', 72, 61),
    ('bluepearl', 86, 69),
    ('bluepearl', 11, 73),
    ('bluepearl', 75, 74),
    # --- east expansion ---
    ('container', 150, 6),
    ('container', 125, 31),
    ('container', 112, 72),
    ('bluepearl', 141, 18),
    ('bluepearl', 123, 4),
    ('bluepearl', 145, 4),
    ('bluepearl', 149, 22),
    ('shrimp', 151, 17),
    ('shrimp', 103, 16),
    ('shrimp', 134, 16),
    ('bluepearl', 99, 41),
    ('bluepearl', 116, 35),
    ('bluepearl', 104, 28),
    ('bluepearl', 147, 37),
    ('shrimp', 140, 45),
    ('shrimp', 134, 38),
    ('shrimp', 132, 34),
    ('bluepearl', 103, 68),
    ('bluepearl', 110, 77),
    ('bluepearl', 124, 60),
    ('bluepearl', 104, 76),
    ('shrimp', 124, 67),
    ('shrimp', 108, 69),
    ('shrimp', 122, 63),
    # --- sky islands ---
    ('container', 36, 96),
    ('container', 13, 120),
    ('bluepearl', 52, 101),
    ('bluepearl', 45, 103),
    ('bluepearl', 29, 115),
    ('bluepearl', 48, 119),
    ('shrimp', 9, 103),
    ('shrimp', 31, 113),
]

# arenas: interior rect in tiles (x0, y0, x1, y1 inclusive) + reward when cleared
ARENAS = {
    'pool': {'rect': (29, 12, 37, 20), 'reward': ('container', 33, 16)},
    'vault': {'rect': (58, 12, 66, 20), 'reward': ('key', 64, 16)},
    'throne': {'rect': (39, 1, 56, 9), 'reward': ('halfpearl', 47.5, 5), 'boss': True},
    'keyroom': {'rect': (127, 66, 139, 76), 'reward': ('key', 133, 71)},
    'murk': {'rect': (127, 56, 156, 64), 'reward': ('halfpearl', 141.5, 60), 'boss': True},
}

SOLID_ALL = set('#CKWSLRIPQ')
OPENABLE = set('KLRIl')       # tiles that can be opened for good (saved in savegames)
FLOOR_CHARS = set('.,=dH')


def in_rect(tx, ty, r):
    return r[0] <= tx <= r[2] and r[1] <= ty <= r[3]


def area_at(tx, ty):
    if ty >= SKY_Y:
        return 'sky'
    if ty >= WORLD_H:
        return 'trial'
    return 'dungeon' if in_rect(tx, ty, SHRINE_RECT) else 'overworld'


def trial_at(tx, ty):
    for name, t in TRIALS.items():
        if in_rect(tx, ty, t['room']):
            return name
    return None


def region_at(tx, ty):
    for name, r in REGIONS:
        if in_rect(tx, ty, r):
            return name
    return 'CORAL REEF'


def theme_at(tx, ty):
    return THEMES.get(region_at(tx, ty), 'reef')


def floor_for(tx, ty):
    return '=' if area_at(tx, ty) in ('dungeon', 'trial') else '.'


def arena_tile_rect(a):
    x0, y0, x1, y1 = a['rect']
    return pygame.Rect(x0 * TILE, y0 * TILE, (x1 - x0 + 1) * TILE, (y1 - y0 + 1) * TILE)


def arena_of(tx, ty):
    for name, a in ARENAS.items():
        x0, y0, x1, y1 = a['rect']
        if x0 <= tx <= x1 and y0 <= ty <= y1:
            return name
    return None


class Level:
    def __init__(self, opened=()):
        self.w, self.h = LEVEL_W, LEVEL_H
        self.px_w, self.px_h = self.w * TILE, self.h * TILE
        self.bounds = pygame.Rect(0, 0, self.px_w, self.px_h)
        self.tiles = [list(r) for r in LEVEL]
        # shutters start open: remember where they are, per arena
        self.doors = {name: [] for name in ARENAS}
        for y in range(self.h):
            for x in range(self.w):
                if self.tiles[y][x] == 'X':
                    self.tiles[y][x] = '='
                    for name, a in ARENAS.items():
                        x0, y0, x1, y1 = a['rect']
                        if x0 - 1 <= x <= x1 + 1 and y0 - 1 <= y <= y1 + 1:
                            self.doors[name].append((x, y))
        for (tx, ty) in opened:
            self.tiles[ty][tx] = floor_for(tx, ty)
        self.blockers = []
        self.ghost_ok = False          # True while Octo is in Spooky form
        self.themes = [[theme_at(x, y) for x in range(self.w)] for y in range(self.h)]
        self.surface = None
        self.dirty_tiles = set()

    # -- tiles -------------------------------------------------------------
    def tile(self, tx, ty):
        if 0 <= tx < self.w and 0 <= ty < self.h:
            return self.tiles[ty][tx]
        return None

    def set_tile(self, tx, ty, ch):
        self.tiles[ty][tx] = ch
        self.dirty_tiles.add((tx, ty))

    def set_doors(self, arena, closed):
        for (tx, ty) in self.doors[arena]:
            self.set_tile(tx, ty, 'X' if closed else '=')

    def solid(self, ch, who):
        if ch is None or ch in SOLID_ALL or ch == 'X':
            return True
        if ch in 'vl':
            return who in ('player', 'walker')
        if ch == 'G':
            return not (who == 'player' and self.ghost_ok)
        return False

    def tiles_in(self, rect):
        x0, x1 = rect.left // TILE, (rect.right - 1) // TILE
        y0, y1 = rect.top // TILE, (rect.bottom - 1) // TILE
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                yield tx, ty, self.tile(tx, ty)

    def blocked(self, rect, who):
        if not self.bounds.contains(rect):
            return True
        for tx, ty, ch in self.tiles_in(rect):
            if self.solid(ch, who):
                return True
        if who != 'shot':
            for b in self.blockers:
                if rect.colliderect(b):
                    return True
        return False

    def flood(self, tx, ty, ch):
        """All tiles of type ch connected to (tx, ty)."""
        out, todo = set(), [(tx, ty)]
        while todo:
            x, y = todo.pop()
            if (x, y) in out or self.tile(x, y) != ch:
                continue
            out.add((x, y))
            todo += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        return out

    # -- drawing -----------------------------------------------------------
    PYRAMID_HEIGHT = {'P': 1, 'Q': 2, 'H': 1}

    def _height(self, tx, ty):
        ch = self.tile(tx, ty)
        if ch == '=' and region_at(tx, ty) == 'OCTO TEMPLE':
            return 3                     # the sanctuary on top
        return self.PYRAMID_HEIGHT.get(ch, 0)

    def _blit_tile(self, tiles, tx, ty):
        ch = self.tiles[ty][tx]
        top = ch == '=' and region_at(tx, ty) == 'OCTO TEMPLE'
        if ch in 'PQH' or top:
            h = self._height(tx, ty)
            lower = tuple(self._height(tx + dx, ty + dy) < h for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)))
            rail = (self.tile(tx - 1, ty) != 'H', self.tile(tx + 1, ty) != 'H')
            self.surface.blit(gfx.pyramid_tile('T' if top else ch, lower, rail), (tx * TILE, ty * TILE))
            return
        area = 'dungeon' if area_at(tx, ty) in ('dungeon', 'trial') else 'overworld'
        other = 'overworld' if area == 'dungeon' else 'dungeon'
        themed = tiles['themes'].get(self.themes[ty][tx], {}) if area == 'overworld' else {}
        variants = themed.get(ch) or tiles[area].get(ch) or tiles[other].get(ch) or tiles[area][floor_for(tx, ty)]
        img = variants[(tx * 7 + ty * 13 + tx * ty) % len(variants)]
        self.surface.blit(img, (tx * TILE, ty * TILE))

    def render(self, tiles):
        if self.surface is None:
            self.surface = pygame.Surface((self.px_w, self.px_h))
            for ty in range(self.h):
                for tx in range(self.w):
                    self._blit_tile(tiles, tx, ty)
            self.dirty_tiles.clear()
        for (tx, ty) in self.dirty_tiles:
            self._blit_tile(tiles, tx, ty)
        self.dirty_tiles.clear()
        return self.surface


def validate():
    problems = []
    for i, row in enumerate(LEVEL):
        if len(row) != LEVEL_W:
            problems.append(f"row {i} has {len(row)} tiles, expected {LEVEL_W}")
    if problems:
        return problems
    for kind, tx, ty in ENEMIES + ITEMS:
        if LEVEL[int(ty)][int(tx)] not in FLOOR_CHARS:
            problems.append(f"{kind} at {(tx, ty)} sits on {LEVEL[int(ty)][int(tx)]!r}")
    for name, a in ARENAS.items():
        kind, tx, ty = a['reward']
        if LEVEL[int(ty)][int(tx)] not in FLOOR_CHARS:
            problems.append(f"{name} reward sits on {LEVEL[int(ty)][int(tx)]!r}")
    # can Octo reach everything? (kelp can be cut, doors unlocked, shutters open)
    walk = FLOOR_CHARS | set('KLXRIGlY')
    links = {}
    for a, b in GEYSERS:
        links[a] = b
        links[b] = a     # R: cracked rock, bombs open it
    seen = {(int(START[0]), int(START[1]))}
    q = deque(seen)
    while q:
        x, y = q.popleft()
        hops = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)] + ([links[(x, y)]] if (x, y) in links else [])
        for nx, ny in hops:
            if 0 <= nx < LEVEL_W and 0 <= ny < LEVEL_H and (nx, ny) not in seen \
                    and LEVEL[ny][nx] in walk:
                seen.add((nx, ny))
                q.append((nx, ny))
    targets = [(k, x, y) for k, x, y in ENEMIES + ITEMS] + \
              [(n, a['reward'][1], a['reward'][2]) for n, a in ARENAS.items()]
    for name, t in TRIALS.items():
        px, py = t['portal']
        targets += [(name + ' portal', px, py), (name + ' portal exit', px, py + 1)]
    for k, x, y in targets:
        if (int(x), int(y)) not in seen:
            problems.append(f"{k} at {(x, y)} is unreachable")
    # each trial room: everything inside must be on floor and reachable from where Octo lands
    for name, t in TRIALS.items():
        x0, y0 = t['room'][:2]
        ex, ey = int(t['entry'][0]) + x0, int(t['entry'][1]) + y0
        inside = {(ex, ey)}
        q = deque(inside)
        while q:
            x, y = q.popleft()
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in inside and LEVEL[ny][nx] in FLOOR_CHARS:
                    inside.add((nx, ny))
                    q.append((nx, ny))
        pts = [('entry', *t['entry'])] + [('orb', x, y) for x, y in t.get('orbs', [])] + \
              [(k, x, y) for k, x, y in t.get('guards', [])] + [('spot', x, y) for x, y in t.get('spots', [])]
        for k, x, y in pts:
            if (int(x) + x0, int(y) + y0) not in inside:
                problems.append(f"{name}: {k} at {(x, y)} is not reachable floor")
    return problems
