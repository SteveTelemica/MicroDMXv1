#!/usr/bin/env python
import os.path

#e.g.
## first line is com port name, baud rate
#"COM7",19200
## other lines are channel name, then DMX numbers for r,g,b,w (w optional)
#"Chan,1",1,2,3,4
#"Chan 2",5,6,7

def ReadDMXSettings(filename):
    data = {}
    if not os.path.isfile(filename):
        print('File does not exist. ' + filename)
    else:
        with open(filename) as f:
            content = f.read().splitlines()
        linenum = 1
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
            #print( params)
            if linenum == 1:
                # Serial settings
                data["port"] =  {"name": params[0], "speed": params[1]}
            else:
                if (len(params) >= 4):
                    # DMX channels, order by line num
                    data[linenum-1] =  {"name": params[0],
                                      "r": params[1],
                                      "g": params[2],
                                      "b": params[3],
                                      "w": params[4] if len(params) >= 5 else -1
                                      }
            linenum += 1
    #print( data)
    return data

if __name__ == "__main__":
    filename = 'C:\\Users\\sesa170272\\Documents\\Dev\\Python\\Utils\\DMXSettings.csv'
    settings = ReadDMXSettings(filename)
    print( settings)
