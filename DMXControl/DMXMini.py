#!/usr/bin/env python
#DMXMini.py

#Libraries
from tkinter import *
from tkinter import ttk
from functools import partial
from tkinter.colorchooser import *
from colorsys import *
import time
import os
import serial # Needs pip install pyserial

#Subroutines
from ReadDMXSettings import *
from ReadWriteDMXScenes import *

class DMXMini:

    def __init__(self, root, settings, scenesfilename):
        self.settings = settings

        title = "DMX Mini Controller"
        root.title(title)

        mainframe = ttk.Frame(root, padding="3 3 12 12")
        mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        ttk.Label(mainframe, text="DMX Mini Controller").grid(column=1, row=1, columnspan=2, sticky=W)

        self.livestate = IntVar(0)
        self.check = ttk.Checkbutton(mainframe, text="Live", onvalue=1, offvalue=0, variable=self.livestate, command=self.changestate)
        self.check.grid(column=3, row=1, sticky=W)
        self.livestate.set(0)

        ttk.Label(mainframe, text="Scene").grid(column=1, row=2, sticky=W)

        self.scenes = ReadDMXScenes(scenesfilename)
        self.sceneslist = [] # used to copy list to the box
        # scenes are a dictionary by scene number, now transform to dictionary by name
        self.scenesdata = {}
        i = 1
        for scene in self.scenes.values():
            self.sceneslist.append( scene["name"] )
            self.scenesdata[ scene["name"] ] = self.scenes[i]
            i += 1
        print (self.scenesdata)
        self.scenesvar = StringVar(value=self.sceneslist)
        self.scenelistbox = Listbox(mainframe, height=10, listvariable=self.scenesvar)
        self.scenelistbox.grid(column=1, row=3, rowspan=4, sticky=W)
        self.scenelistbox.bind("<<ListboxSelect>>",
                               lambda e: self.sceneselection(self.scenelistbox.curselection()))

        self.scene = StringVar()
        self.scene_entry = ttk.Entry(mainframe, width=20, textvariable=self.scene)
        self.scene_entry.grid(column=1, row=7, sticky=(W, E))

        self.messagetext = StringVar()
        self.messagevalue = ttk.Label(mainframe, textvariable = self.messagetext)
        self.messagevalue.grid(column=1, row=8, columnspan=3, sticky=W)
        self.messagetext.set("Started " + title)

        ttk.Button(mainframe, text="Save", command=self.save).grid(column=2, row=2, sticky=W)

        ttk.Button(mainframe, text="Up", command=self.up).grid(column=2, row=3, sticky=W)
        ttk.Button(mainframe, text="Down", command=self.down).grid(column=2, row=4, sticky=W)
        ttk.Button(mainframe, text="Update", command=self.update).grid(column=2, row=5, sticky=W)
        ttk.Button(mainframe, text="Delete", command=self.delete).grid(column=2, row=6, sticky=W)

        self.addbutton = ttk.Button(mainframe, text="Add", command=self.add)
        self.addbutton.grid(column=2, row=7, sticky=W)

        self.speedtext = StringVar()
        self.speedvalue = ttk.Label(mainframe, textvariable = self.speedtext)
        self.speedvalue.grid(column=3, row=2, sticky=W)
        self.speedtext.set("2.0 sec")

        self.speedvar = IntVar() #or DoubleVar
        self.speedscale = ttk.Scale(mainframe, orient=VERTICAL, from_=250, to=0, length=110,
                                    variable=self.speedvar, command=self.updatespeed)
        self.speedscale.grid(column=3, row=3, rowspan=3)
        self.speedvar.set(20)

        ttk.Label(mainframe, text="Fade Time").grid(column=3, row=7, sticky=W)

        # widgets per channel
        self.chantext = {}
        self.chanvalue = {}
        self.chanvar = {}
        self.chanscale = {}
        self.colourpicker = {}

        # channel data
        for i in self.settings.keys():
            if (isinstance(i,int)):
                self.chantext[i] = StringVar()
                self.chanvalue[i] = ttk.Label(mainframe, text="100%", textvariable = self.chantext[i]).grid(column=3+i, row=2, sticky=W)
                self.chantext[i].set("0 %")

                self.chanvar[i] = IntVar()
                
                self.chanscale[i] = ttk.Scale(mainframe, orient=VERTICAL, from_=255, to=0, length=110,
                                              variable=self.chanvar[i], command = partial( self.updatechan, i) )
                self.chanscale[i].grid(column=3+i, row=3, rowspan=3)
                self.chanvar[i].set(0)
                
                ttk.Label(mainframe, text=self.settings[i]["name"]).grid(column=3+i, row=7, sticky=W)

                self.colourpicker[i] = Canvas(mainframe, width=30, height=30, background='white')
                # save current colours in self.settings
                self.settings[i]["h"] = 0
                self.settings[i]["s"] = 0
                self.settings[i]["v"] = 0
                print( self.settings[i])
                self.colourpicker[i].grid(column=3+i, row=6)
                self.colourpicker[i].bind("<Button-1>", partial( self.setcolour, i) )

        for child in mainframe.winfo_children(): 
            child.grid_configure(padx=5, pady=5)

        self.scene_entry.focus()
        root.bind("<Return>", self.addbutton)

        self.systemonline = False

    def changestate(self):
        if (self.livestate.get() == 0):
            self.messagetext.set("Change state to not live" )
        else:
            if (self.systemonline == False):
                # Start comms
                self.openSerial( settings["port"]["name"], settings["port"]["speed"] )
                self.messagetext.set("Go live, port open" )
            else:
                self.messagetext.set("Change state to live" )

            if (self.systemonline == True):
                # Send all channels at set speed
                t = self.speedvar.get()
                for i in self.settings.keys():
                    if (isinstance(i,int)):
                        h = self.settings[i]["h"]
                        s = self.settings[i]["s"]
                        v = self.chanvar[i].get()
                        self.sendDMX( i, t, h, s, v)
            else:
                self.messagetext.set("Cannot open port" )
                self.livestate.set(0)

    def updatespeed(self, val):
        self.messagetext.set("Change speed " + str(self.speedvar.get()) )
        self.speedtext.set(str(self.speedvar.get()/10.0) + " sec")

    def updatechan(self, i, val):
        self.messagetext.set("Change chan brightness "+ str(i) + "," + str(self.chanvar[i].get()) )
        self.chantext[i].set(str(int(self.chanvar[i].get()*100/255)) + " %")
        # If live send this channel immediately
        if (self.livestate.get() == 1):
            t = self.speedvar.get()
            h = self.settings[i]["h"]
            s = self.settings[i]["s"]
            v = self.chanvar[i].get()
            self.sendDMX( i, 0, h, s, v)
            
    def save(self):
        # Reorganise by scene id
        self.newscenes = {}
        i = 1
        for s in self.sceneslist:
            self.newscenes[i] = self.scenesdata[s]
            i = i + 1
        print( self.newscenes)
        WriteDMXScenes(scenesfilename, self.newscenes)
        self.messagetext.set("Saved")

    def up(self):
        if (len( self.scenelistbox.curselection() ) == 0):
            self.messagetext.set("Scene not selected")
            return
        pos1 = self.scenelistbox.curselection()[0]
        pos0 = pos1-1
        if ( pos1 == 0):
            self.messagetext.set("Already at the top")
            return
        self.messagetext.set("Up")
        self.sceneslist[ pos1], self.sceneslist[ pos0] = self.sceneslist[ pos0], self.sceneslist[ pos1]
        self.scenesvar.set(self.sceneslist)
        self.scenelistbox.selection_clear(pos1)
        self.scenelistbox.selection_set(pos0)
        self.scenelistbox.see(pos0)

    def down(self):
        if (len( self.scenelistbox.curselection() ) == 0):
            self.messagetext.set("Scene not selected")
            return
        pos1 = self.scenelistbox.curselection()[0]
        pos2 = pos1+1
        if ( pos1 == len( self.sceneslist )-1):
            self.messagetext.set("Already at the bottom")
            return
        self.messagetext.set("Down")
        self.sceneslist[ pos1], self.sceneslist[ pos2] = self.sceneslist[ pos2], self.sceneslist[ pos1]
        self.scenesvar.set(self.sceneslist)
        self.scenelistbox.selection_clear(pos1)
        self.scenelistbox.selection_set(pos2)
        self.scenelistbox.see(pos2)

    def delete(self):
        if (len( self.scenelistbox.curselection() ) == 0):
            self.messagetext.set("Scene not selected")
            return
        self.messagetext.set("Delete " + str(self.scenelistbox.curselection()[0]) )
        # Delete a scene from data and list
        self.scenesdata.pop( self.sceneslist[ self.scenelistbox.curselection()[0] ] )
        self.sceneslist.pop( self.scenelistbox.curselection()[0])
        self.scenesvar.set(self.sceneslist)

    def update(self):
        if (len( self.scenelistbox.curselection() ) == 0):
            self.messagetext.set("Scene not selected")
            return
        self.messagetext.set("Update " + str(self.scenelistbox.curselection()[0]) )
        # Modify scenes
        self.scenesdata.pop( self.sceneslist[ self.scenelistbox.curselection()[0] ] )
        self.insertscenedata()

    def add(self):
        self.messagetext.set("Add " + self.scene.get())
        # check for duplicates or blanks
        if ( self.scene.get() == "" ):
            self.messagetext.set("Blank scene name")
            return
        if ( self.scene.get() in self.sceneslist ):
            self.messagetext.set("Duplicate scene name")
            return
        self.sceneslist.append( self.scene.get() )
        self.scenesvar.set(self.sceneslist)
        # select last new entry
        i = len( self.sceneslist )-1
        self.scenelistbox.selection_clear(0,i+1)
        self.scenelistbox.selection_set(i)
        self.scenelistbox.see(i)
        self.insertscenedata()

    def insertscenedata(self):
        # Add channel colours to the scenes
        scene = {}
        scene[ "name"] = self.sceneslist[ self.scenelistbox.curselection()[0] ]
        scene[ "time"] = self.speedvar.get()
        sets = {}
        for i in self.settings.keys():
            if (isinstance(i,int)):
                colour = {}
                colour[ "h"] = self.settings[i]["h"]
                colour[ "s"] = self.settings[i]["s"]
                colour[ "v"] = self.chanvar[i].get()
                sets[ self.settings[i]["name"] ] = colour
        scene[ "sets"] = sets
        # Add scene by name
        self.scenesdata[ self.sceneslist[ self.scenelistbox.curselection()[0] ] ] = scene
        print( self.scenesdata[ scene[ "name"] ])

    def sceneselection(self, i):
        if (len( self.scenelistbox.curselection() ) == 0):
            self.messagetext.set("Scene not selected")
            return
        scenename = self.sceneslist[ self.scenelistbox.curselection()[0] ]
        self.messagetext.set("Select scene " + str(i[0]) + " " + scenename )
        # Scene speed
        print( self.scenesdata[ scenename])
        self.speedvar.set( self.scenesdata[ scenename]["time"] )
        self.speedtext.set(str(self.speedvar.get()/10.0) + " sec")
        # Set up scene colours per channel
        for sc in self.scenesdata[ scenename]["sets"].keys():
            # We have channel name, need number
            chan_num = 0
            for c in self.settings.keys():
                if self.settings[c]["name"] == sc:
                    chan_num = c
                    break
            if (c != 0):
                h = int(self.scenesdata[ scenename]["sets"][sc]["h"])
                s = int(self.scenesdata[ scenename]["sets"][sc]["s"])
                v = int(self.scenesdata[ scenename]["sets"][sc]["v"])
                self.chanvar[c].set( v)
                self.chantext[c].set(str(int(self.chanvar[c].get()*100/255)) + " %")
                print( "h,s,v: ", h, s, v)
                r, g, b = hsv_to_rgb( h/255, s/255, 1.0)
                print( "Sat r,g,b: ", r,g,b)
                # convert to long, then convert to 6 digit hex
                hexcolour = "#" + ("000000" + hex( self.rgb_to_long(r, g, b) )[2:])[-6:]
                print( "hex: ", hexcolour)
                self.colourpicker[c].create_rectangle( 0, 0, 30, 30, fill=hexcolour)
                # write colours to channel setup
                self.settings[c]["h"] = int(h)
                self.settings[c]["s"] = int(s)
                self.settings[c]["v"] = int(v)
        # If live send this scene at speed
        if (self.livestate.get() == 1):
            t = self.speedvar.get()
            for i in self.settings.keys():
                if (isinstance(i,int)):
                    h = self.settings[i]["h"]
                    s = self.settings[i]["s"]
                    v = self.chanvar[i].get()
                    self.sendDMX( i, t, h, s, v)
                            
    def setcolour(self, i, j):
        self.messagetext.set("Choose colour " + str(i) )
        # askcolor() returns a tuple of the form
        # ((r,g,b), hex) or (None, None) if cancelled
        color = askcolor(parent=root,
                         title='Choose color for {}'.format(i))
        if color[1]:
            print( color[0])
            r, g, b = color[0] #unpack tuple
            print( "New r,g,b: ", r,g,b)
            h, s, v = rgb_to_hsv( r/256, g/256, b/256)
            print( "h,s,v: ", h,s,v)
            # update slider v
            self.chanvar[i].set(v*256)
            self.chantext[i].set(str(int(self.chanvar[i].get()*100/255)) + " %")
            # set colour square
            r, g, b = hsv_to_rgb( h, s, 1.0)
            print( "Sat r,g,b: ", r,g,b)
            # convert to long, then convert to 6 digit hex
            hexcolour = "#" + ("000000" + hex( self.rgb_to_long(r, g, b) )[2:])[-6:]
            print( "hex: ", hexcolour)
            self.colourpicker[i].create_rectangle( 0, 0, 30, 30, fill=hexcolour)
            # write colours to channel setup
            self.settings[i]["h"] = int(h*255)
            self.settings[i]["s"] = int(s*255)
            self.settings[i]["v"] = int(v*255)
            print( self.settings[i])
            # if Live set this colour now
            if (self.livestate.get() == 1):
                h = self.settings[i]["h"]
                s = self.settings[i]["s"]
                v = self.chanvar[i].get()
                self.sendDMX( i, 0, h, s, v)

    def sendDMX( self, i, t, h, s, v):
        r, g, b = hsv_to_rgb( h/255.0, s/255.0, v/255.0)
        print( "Sending: ", i, t, int(r*255), int(g*255), int(b*255) )
        # Get channels of R G B (W optional, will be send the v value)
        chanr = settings[i]["r"]
        chang = settings[i]["g"]
        chanb = settings[i]["b"]
        chanw = settings[i]["w"]
        self.sendDMXvalue( chanr, t, int(r*255))
        self.sendDMXvalue( chang, t, int(g*255))
        self.sendDMXvalue( chanb, t, int(b*255))
        if (int(chanw) >= 0):
            self.sendDMXvalue( chanw, t, int(v))

    def openSerial( self, name, speed):
        try:
            print( name, speed)
            self.serialDMX = serial.Serial(name, speed, timeout=0.5)
            self.systemonline = True
        except Exception as e:
            print("Serial error: " + e)
            self.systemonline = False

    def sendDMXvalue( self, chan, timer, val):
        commandtext =   "F" + ("00"+str(chan))[-3:] + "V" + ("00"+str(val))[-3:] + "P" + ("00"+str(timer ))[-3:] + "E\r"
        print( "Send: " + commandtext)
        self.serialDMX.write( commandtext.encode() )
        r = ""
        ms = time.time() * 1000.0
        while True:
            if self.serialDMX.in_waiting > 0:
                r = self.serialDMX.read().decode()
                #print("Response " + r )
            if (r.startswith( "A") ):
                break
            ms2 = time.time() * 1000.0
            if (ms2 - ms > 1000):
                print("Serial Timeout")
                break

    def rgb_to_long( self, r, g, b):
        return int(b*255) + 256 * int(g*255) + 256 * 256 * int(r*255)


p = os.path.dirname(os.path.abspath(__file__))

settingfilename = p + '\\DMXSettings.csv'
scenesfilename = p + '\\DMXScenes.csv'
settings = ReadDMXSettings(settingfilename)
print( settings)

root = Tk()
DMXMini(root, settings, scenesfilename)
root.mainloop()

#self.serialDMX.close()






