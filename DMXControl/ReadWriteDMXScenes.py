#!/usr/bin/env python
import os.path

#e.g.
## Comment: List of scene names and timing, then channel settings H,S,V
#Scene,"Scene 1",10
#Set,"Chan,1",100,200,50
#Set,"Chan 2",200,150,30
#Scene,"Scene 2 All Red",20
#Set,"Chan,1",255,0,0
#Set,"Chan 2",255,0,0

#Data structure:
#{1: 
#	{'name': 'Scene 1', 'time': '10', 
#	 'sets': {'Chan,1': {'h': '100', 's': '200', 'v': '50'}, 
#	          'Chan 2': {'h': '200', 's': '150', 'v': '30'}
#		 }
#	}, 

def ReadDMXScenes(filename):
    data = {} # ordered dictionary
    if not os.path.isfile(filename):
        print('File does not exist. ' + filename)
    else:
        with open(filename) as f:
            content = f.read().splitlines()
        linenum = 1
        scenenum = 0
        for line in content:
            if (line[0] == '#'):
                continue
            params = []
            # Could use a lib, but to avoid that we separate " first
            linesplitquote = line.split('"')
            # odd elements (1,3,5...) are within quotes
            # even elements (0,2,4,6...) are not in quotes
            index = 0
            for item in linesplitquote:
                if (index % 2) == 1: #odd, in quotes
                    params.append( item)
                else:
                    # ignore all empty fields
                    if item != '':
                        paramsplitcomma = item.split(",")
                        for field in paramsplitcomma:
                            if field != '':
                                params.append( field)
                index += 1
            print( params)
            if params[0] == "Scene":
                # Scene,"Scene 1",10
                scenenum += 1
                # Create scene and add empty list of channel settings
                # sets is a List of Dictionaries
                data[scenenum] =  {"name": params[1], "time": params[2], "sets": []}
                setting = {}
                first = True
            else:
                if params[0] == "Set": # len(params) >= 4:
                    # Channels: Set,"Chan,1",100,200,50
                    setting[ params[1] ] = {"h": params[2],
                                      "s": params[3],
                                      "v": params[4]
                                      }
                    if first:
                        data[scenenum]["sets"] = ( setting)
                        first = False
            linenum += 1
    return data

def WriteDMXScenes(filename, scenes):
    f = open(filename, "w")
    f.write("# Comment: List of scene names and timing, then channel settings H,S,V\n")
    for scene in scenes.values():
        f.write("Scene,\"" + str(scene["name"]) + "\"," + str(scene["time"]) + "\n")
        for settingkey in scene["sets"].keys():
            f.write("Set,\"" + str(settingkey) + "\"," +
                    str(scene["sets"][settingkey]["h"]) + "," +
                    str(scene["sets"][settingkey]["s"]) + "," +
                    str(scene["sets"][settingkey]["v"]) + "\n")
    f.close()

if __name__ == "__main__":
    filename = 'C:\\Users\\sesa170272\\Documents\\Dev\\Python\\Utils\\DMXScenes.csv'
    scenes = ReadDMXScenes(filename)
    print( scenes)

    filename = 'C:\\Users\\sesa170272\\Documents\\Dev\\Python\\Utils\\DMXScenes2.csv'
    WriteDMXScenes(filename, scenes)
    with open(filename) as f:
            content = f.read()
            print( content)
