import os
from glob import glob
import subprocess
import os.path as osp

import yaml
import omg
import shutil


### Load Config ###


def load_config(flnm):
    with open("resources/map_configs/{0}.yaml".format(flnm)) as stream:
        return yaml.safe_load(stream)

object_types = ['nourishment','poison','obstacle','distractor']

### Building ACS files ###

def make_acs(cfg,actor_names,actor_num_textures):
    
    acs = ""

    # Directives
    acs +="""// Directives
#import "acs/retinal.acs"
#include "zcommon.acs"

script "Load Config Information" OPEN {{

    // Metabolic variables
    metabolic_delay = {0};
    metabolic_damage = {1};
    """.format(cfg['metabolic']['delay'],cfg['metabolic']['damage'])

    for typ in object_types:
        xcfg = cfg[typ]
        acs += """
    // {0} variables
    {0}_unique = {1};
    {0}_init = {2};
    {0}_delay = {3};
    """.format(typ,len(xcfg['actors']),xcfg['init'],xcfg['delay'])

    acs += "\n    // Loading arrays"

    for i,(actor_name,num_textures) in enumerate(zip(actor_names,actor_num_textures)):
        acs += """
    actor_names[{0}] = "{1}";
    actor_num_textures[{0}] = {2};
    """.format(i,actor_name,num_textures)

    acs += "\n}"

    return acs

### Building Decorate Files ###

decorate_pre = {}

decorate_pre['nourishment'] = """ACTOR {0} : CustomInventory {{
    +INVENTORY.ALWAYSPICKUP
    States {{
        Pickup:
            TNT1 A 0 HealThing({1})
            Stop\n"""
decorate_pre['poison'] = """ACTOR {0} : CustomInventory {{
    +INVENTORY.ALWAYSPICKUP
    States {{
        Pickup:
            TNT1 A 0 DamageThing({1})
            Stop\n"""
decorate_pre['obstacle'] = """ACTOR {0} : TorchTree {{
    Radius 24
    States {{\n"""
decorate_pre['distractor'] = """ACTOR {0} : CustomInventory {{
    +INVENTORY.ALWAYSPICKUP
    States {{\n"""

def actor_code(i,j):
    # Convert k to caps alpha string
    return chr(65 + i) + texture_code(j)

def texture_code(j):
    # Convert k to a 3-digit alpha all-caps string
    return chr(65 + j // 26 ** 2) + chr(65 + (j // 26) % 26) + chr(65 + j % 26)

def make_decorate_include(actor_names):

    decorate = ""

    for actor_name in actor_names:
        decorate += "#include \"actors/{0}.dec\"\n".format(actor_name)

    return decorate

def make_decorate(cfg,actor_name,typ,actor_idx,num_textures):

    cfg = cfg[typ]['actors'][actor_name]

    decorate = ""
    if typ == "nourishment":
        decorate += decorate_pre[typ].format(actor_name,cfg['healing'])
    elif typ == "poison":
        decorate += decorate_pre[typ].format(actor_name,cfg['damage'])
    elif typ == "obstacle":
        decorate += decorate_pre[typ].format(actor_name)
    elif typ == "distractor":
        decorate += decorate_pre[typ].format(actor_name)
    else:
        raise ValueError("Invalid actor type: {0}".format(typ))

    # Multiline string for beginning of decorate file
    for j in range(num_textures):
        decorate += """        Tex{0}:
            {0} A -1\n""".format(actor_code(actor_idx,j))

    decorate += """        }
    }\n\n"""

    return decorate

### Loading Textures ###

def load_textures(wad,actor_idx,pngs):

    for j,png in enumerate(pngs):
        code = actor_code(actor_idx,j) + "A0"
        wad.sprites[code] = omg.Lump(from_file=png)

### Creating Scenarios ###


def create_base_wad():

    bpth = "resources/base"
    wad = omg.WAD()

    grspth = osp.join(bpth,"grass.png")
    wndpth = osp.join(bpth,"wind.png")

    tmppth = osp.join(bpth,"TEXTMAP.txt")
    mpipth = osp.join(bpth,"MAPINFO.txt")

    # Flats
    wad.ztextures['GRASS'] = omg.Lump(from_file=grspth)

    # Data
    wad.data['WIND'] = omg.Lump(from_file=wndpth)
    wad.data['MAPINFO'] = omg.Lump(from_file=mpipth)

    # Map preparation
    mpgrp = omg.LumpGroup()
    mpgrp['TEXTMAP'] = omg.Lump(from_file=tmppth)

    return wad,mpgrp

def make_scenario(scnnm):

    # Preloading
    cfg = load_config(scnnm)

    # Base directories
    rscdr = "resources"
    scndr = "scenarios"

    # Inupt Directories
    ibsdr = osp.join(rscdr,"base")
    iacsdr = osp.join(ibsdr,"acs")
    itxtdr = osp.join(rscdr,"textures")

    # Output Directories
    oroot = osp.join(scndr,scnnm)
    oacsdr = osp.join(oroot,"acs")
    omapdr = osp.join(oroot,"maps")
    osptdr = osp.join(oroot,"sprites")
    oactdr = osp.join(oroot,"actors")
    otxtdr = osp.join(oroot,"textures")

    # Remove exiting root directory
    if osp.exists(oroot):
        shutil.rmtree(oroot)

    # Create Directories
    os.makedirs(scndr,exist_ok=True)
    os.makedirs(oroot,exist_ok=True)
    os.makedirs(oacsdr,exist_ok=True)
    os.makedirs(omapdr,exist_ok=True)
    os.makedirs(osptdr,exist_ok=True)
    os.makedirs(oactdr,exist_ok=True)
    os.makedirs(otxtdr,exist_ok=True)

    # Textures
    shutil.copy(osp.join(ibsdr,"grass.png"),osp.join(otxtdr,"GRASS.png"))
    shutil.copy(osp.join(ibsdr,"wind.png"), osp.join(otxtdr,"WIND.png"))

    # Copy Data to Root
    shutil.copy(osp.join(ibsdr,"MAPINFO.txt"), osp.join(oroot,"MAPINFO.txt"))

    # Building decorate and loading textures

    actor_names = []
    actor_num_textures = []

    actor_idx = 0
    for typ in object_types:
        for actor_name in cfg[typ]['actors']:

            pngpths = cfg[typ]['actors'][actor_name]['textures']
            # get all pngs listend in pngpths and subdirs
            pngs = []
            for pngpth in pngpths:
                fllpth = osp.join(itxtdr,pngpth)
                # if pngpth is a png, add it
                if pngpth.endswith(".png"):
                    pngs.append(fllpth)
                elif osp.isdir(fllpth):
                    # if pngpth is a directory, recursively add all pngs
                    for root, _, files in os.walk(fllpth):
                        for file in files:
                            if file.endswith(".png"):
                                pngs.append(osp.join(root,file))
            pngs = pngs
                

            num_textures = len(pngs)

            for j,png in enumerate(pngs):
                code = actor_code(actor_idx,j) + "A0"
                # Copy png to sprite pth
                shutil.copy(png,osp.join(osptdr,code + ".png"))

            decorate = make_decorate(cfg,actor_name,typ,actor_idx,num_textures)
            # write decorate to actor pth
            with open(osp.join(oactdr,actor_name + ".dec"),'w') as f:
                f.write(decorate)

            actor_idx += 1
            actor_names.append(actor_name)
            actor_num_textures.append(num_textures)

    # Write decorate to root
    decorate = make_decorate_include(actor_names)

    with open(osp.join(oroot,"DECORATE.txt"),'w') as f:
        f.write(decorate)

    ## ACS ##

    # Defining paths

    bhipth = osp.join(oroot,scnnm + ".acs")
    bhopth = osp.join(oroot,scnnm + ".o")

    lbipth = osp.join(iacsdr,"retinal.acs")
    lbopth = osp.join(oacsdr,"RETINAL")

    # Copy retinal to acs pth
    shutil.copy(lbipth,oacsdr)

    tmppth = osp.join(ibsdr,"TEXTMAP.txt")

    # Write ACS
    with open(bhipth,'w') as f:
        acs = make_acs(cfg,actor_names,actor_num_textures)
        f.write(acs)

    # Compile ACS
    subprocess.call(["acc", "-i","/usr/share/acc", bhipth, bhopth])
    subprocess.call(["acc", "-i","/usr/share/acc", lbipth, lbopth])

    # Map Wad

    wad = omg.WAD()
    mpgrp = omg.LumpGroup()

    mpgrp['TEXTMAP'] = omg.Lump(from_file=tmppth)
    mpgrp['SCRIPTS'] = omg.Lump(from_file=bhipth)
    mpgrp['BEHAVIOR'] = omg.Lump(from_file=bhopth)
    wad.udmfmaps["MAP01"] = omg.UMapEditor(mpgrp).to_lumps()

    # Cleanup
    os.remove(bhopth)

    # Save wad to map dir
    wad.to_file(osp.join(omapdr,"MAP01.wad"))

    # Copy vizdoom config
    cnfnm = scnnm + ".cfg"
    shutil.copy(osp.join(ibsdr,"vizdoom.cfg"),osp.join(scndr,cnfnm))
    # add doom_scenario_path to beginning of cfg
    with open(osp.join(scndr,cnfnm),'r') as f:
        cfgtxt = f.read()
    cfgtxt = "doom_scenario_path = " + scnnm + "\n\n" + cfgtxt
    with open(osp.join(scndr,cnfnm),'w') as f:
        f.write(cfgtxt)
