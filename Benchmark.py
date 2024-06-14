#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 这个基准测试脚本来自 https://github.com/brucethemoose/Minecraft-Performance-Flags-Benchmarks 作者为 brucethemoose 使用 MIT 协议开源
# ZeHuaJun 进行二次更改

# 此基准测试脚本仅用于 在 Linux 上的 Fabric 我的世界 服务器性能测试

import os,time,shutil,glob,datetime,json,platform,signal,statistics,pprint,subprocess,csv,atexit,traceback
import psutil  
import pexpect
from pexpect import popen_spawn


#----------------------------重复信息----------------------------

# 我的世界服务器路径
serverpath = r"server"


# Java 路径



#-----------------------基准测试数据--------------------------
benchname = r"Benchmark Test"

blist = [

#  {
#    "Name": "Server benchmark name", 
#    "Command": Full java command to launch the server, except for forge/fabric arguments,
#    "Path": full path to the server, 
#    "Iterations": # of iterations to run and average together
#  }

  {
    "Name": "m", 
    "Command": "/usr/lib/jvm/temurin-21-jdk-amd64/bin/java -Xmx12G",
    "Path": serverpath,
    "Iterations": 1
  }

]

#----------------------其他选项--------------------------

#服务器基准测试选项
nogui = False     # 是否运行专用服务器GUI
carpet = 67 #如果存在“地毯”织物mod，则模拟玩家的数量
fabric_chunkgen_command = r"chunky start"      # 要在 fabric packs 中使用的块生成命令
fabric_chunkgen_expect =  r"[Chunky] Task finished for"   # 块生成完成时要查找的字符串
startuptimeout= 350 # 在认为服务器已关闭/卡住之前等待的秒数
chunkgentimeout = 600 # 在考虑服务器已关闭/卡住之前等待区块生成的秒数 
totaltimeout = 1200 # 整个服务器在超时前可以运行的秒数。
forceload_cmd= r"forceload add -120 -120 120 120" # 用于强制加载矩形的命令。也可以是其他一些服务器控制台命令



#----------------------无用选项--------------------------

# 对于 Forge 的服务端基准测试选项
forge_chunkgen_command = r"forge generate 0 0 0 3000"     #用于 Forge packs 的块生成命令
forge_chunkgen_expect =  r"Finished generating"           # 块生成完成时要查找的字符串

# 客户端基准测试选项
prismpath = r"C:/Games/Prism-Windows-Portable-1.4.0/Prism.exe" #Full path to Prism executable file
prisminstances = r"" #Full path to Prism instance folder. Normally in %appdata%/roaming/Prism on windows, but you can leave this blank if using Prism portable. 
presentmonpath = r"presentmon.exe"  #full path to Intel presentmon executable file
warmup = 90    #Seconds to wait after hitting the "singleplayer" button before starting the benchmark. Give enough time for the world to load, and java to "warm up"
benchtime = 90 #Seconds to run the benchmark
focusclick = False #Middle click before searching for buttons, only really necessary for fullscreen Minecraft






#-------------------------代码----------------------------
# 您不应该配置此行以下的任何内容！

debug = False
loadedstring = r"textures/atlas/mob_effects.png-atlas" #String to look for in a log when a client is finished loading
benchlog = os.path.normpath(os.path.join(os.getcwd(), "Benchmarks/", str(datetime.datetime.now())[:-7].replace(" ", "_").replace(":","-") + "_" + benchname.replace(" ", "_") + r".json")) #Benchmark log path
csvpath = os.path.normpath(os.path.join(os.getcwd(),  "Benchmarks", "presentmon.csv"))
cvpath = os.path.abspath("CV_Images")


def benchmark(i): #"i is the benchmark index"
  iter = 1

  #Init
  spark = False
  hascarpet = False
  g1gc = False
  chunkgen_command = ""
  chunkgen_expect = ""
  
  plat = "Linux"
  if "Windows" in platform.system():
    plat = "Windows"
  ngui = ""
  if nogui:
    ngui = " nogui"
  if "PrismInstance" in blist[i] and ("Command" in blist[i] or "Path" in blist[i]):
    raise Exception("Each benchmark instance should ether have a command and path entry, or a Prism instance entry, not both")
  
  #Function to wait for a given line to appear in a log file. 
  def waitforlogline(lfile, key, ldelay = 1, ltimeout = 1800):
    lt = float(time.time() + float(ltimeout))
    with open(lfile, "r") as t:
      while True:
        for line in t.readlines():
          if key in line:
            return
        time.sleep(ldelay)
        if time.time() > lt:
          raise Exception("Cannot find " + key + " in log!")
  def safemean(l):  #average lists while ignoring strings in them
    l = [x for x in l if not isinstance(x, str)]
    if len(l) > 1:
      return round(statistics.mean(l), 2)
    elif len(l) == 1:
      return l[0]
    else:
      return "-"
  def safevar(l):  #pvariance lists while ignoring strings in them
    l = [x for x in l if not isinstance(x, str)]
    if len(l) > 1:
      return round(statistics.pvariance(l), 2)
    else:
      return "-"

  if "PrismInstance" in blist[i]:
    #---Client branch---
    import pygetwindow as gw
    from guibot.guibot import GuiBot 
    from guibot.controller import PyAutoGUIController
    from guibot.config import GlobalConfig
    from guibot.finder import TemplateFinder
    import pydirectinput
    import pyautogui
    #Only import client modules in client branch.

    if plat != "Windows":
      raise Exception("Benchmarking is only supported on Windows!")
    prismfolder = os.path.normpath(os.path.join(os.path.dirname(prismpath), "instances", blist[i]["PrismInstance"]))
    if not os.path.isdir(prismfolder):
      prismfolder = os.path.join(prisminstances, blist[i]["PrismInstance"])
      if not os.path.isdir(prismfolder):
        raise Exception("Either your Prism instance path or your selected instance is incorrect: " + prismfolder)
    prismfolder = (glob.glob(os.path.join(prismfolder, "minecraft")) + glob.glob(os.path.join(prismfolder, ".minecraft")))[0]
    if not os.path.isdir(prismfolder):
      raise Exception("Prism instance not valid!")
    plog = os.path.join(prismfolder, "logs", "latest.log")
    try:
      worldfolder = glob.glob(os.path.join(prismfolder, "saves", "*"))[0]
    except:
      raise Exception("Please create a world in this instance before running the benchmark!")
    worldbackup = os.path.join(prismfolder, "world_backup")

    os.chdir(prismfolder)
    
    #initialize lists
    blist[i]["Average_FPS"] = []
    blist[i][r"1%_Frametime_ms"] = []
    blist[i][r"5%_Frametime_ms"] = []
        #Try to find Spark and/or Carpet mods
    if os.path.isdir("mods"):
      mods = glob.glob("mods/*.jar")
      spark = any('spark' in s for s in mods) #Check for Spark mod
      if spark:                         
        blist[i]["GC_Stop_MS"] = []
        blist[i]["GC_Stops"] = []
        blist[i]["Oldgen_GCs"] = []
        blist[i]["Memory_Usage"] = []
        blist[i]["CPU_Usage"] = []

    def restore_world():
      if os.path.isdir(worldfolder) and os.path.isdir(worldbackup):
        try: 
          shutil.rmtree(worldfolder)
        except:
          time.sleep(7)   #Give the old server some time to close
          shutil.rmtree(worldfolder)
        os.rename(worldbackup, worldfolder)
    atexit.register(restore_world)
    restore_world() #restore backup in case it wasnt restored on exit before

    for n in range(1, blist[i]["Iterations"] + 1):  #Run benchmark for # of iterations
      try:
        #Backup existing world to restore later
        if os.path.isdir(worldfolder) and not os.path.isdir(worldbackup):
          try:
            shutil.copytree(worldfolder, worldbackup)
          except:
            time.sleep(3)
            shutil.copytree(worldfolder, worldbackup, dirs_exist_ok=True)
        for proc in psutil.process_iter(['name']):   #Check for an existing javaw process
          if "javaw" in str(proc.name):
            raise Exception("Please kill all existing 'javaw' processes")
        if os.path.exists(plog): #Remove old log
          os.remove(plog)    

        try: 
          subprocess.run([presentmonpath, "-terminate_existing"], creationflags = subprocess.CREATE_NEW_CONSOLE, shell=True)
        except:
          pass
        try:  
          clientprocess = subprocess.Popen([prismpath, "--launch", blist[i]["PrismInstance"]], creationflags=subprocess.HIGH_PRIORITY_CLASS | subprocess.CREATE_NEW_CONSOLE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True) #launch the client
        except Exception as e:
          print("Error starting client:")
          raise e

        #Wait for client to start up
        time.sleep(15)
        waitforlogline(plog, loadedstring)
        title = None
        for t in gw.getAllTitles():
          if "Minecraft" or "minecraft" in t:
            title = t
        mcwindow = gw.getWindowsWithTitle(title)[0]
        mcwindow.maximize() #Maximuze and activate the window so GUIbot can "see" it.
        mcwindow.activate()
        time.sleep(4)
        if debug: print("Starting machine vision search")
        GlobalConfig.smooth_mouse_drag = False
        GlobalConfig.delay_after_drag = 0
        ctl = PyAutoGUIController()
        gfinder = TemplateFinder()
        guibot = GuiBot(ctl,gfinder)
        guibot.add_path(cvpath)
        _timeout = time.time() + 100
        def middleclick():
          pydirectinput.mouseDown(button='left')
          pydirectinput.mouseUp(button='left')

        #Try to find matches PNGs in CV_Images and click on them:
        def ClickPlay():
          while True:
            print("Searching for 'Play' button")
            time.sleep(0.3)
            if guibot.exists("Play1"):
              guibot.click("Play1")
              break
            elif guibot.exists("Play2"):
              guibot.click("Play2")
              break
            elif guibot.exists("Play3"):
              guibot.click("Play3")
              break
            elif guibot.exists("Play4"):
              guibot.click("Play4")
              break
            else:
              if focusclick:
                middleclick()
              if time.time() > _timeout:
                raise Exception("Cannot find 'Play' Button to click! This may be a machine vision issue if the start screen is modded.")
        def ClickVersion():
          while True:
            print("Searching for 'Version' string")
            time.sleep(0.5)
            if guibot.exists("Version1"):
              guibot.click("Version1")
              ClickPlay()
              break
            elif guibot.exists("Version2"):
              guibot.click("Version2")
              ClickPlay()
              break
            elif guibot.exists("Version3"):
              guibot.click("Version3")
              ClickPlay()
              break
            elif guibot.exists("Version4"):
              guibot.click("Version4")
              ClickPlay()
              break
            else:
              if time.time() > _timeout:
                raise Exception("Cannot find world to click! Please create a world before running the script. This may be a machine vision issue if the start screen is modded.")
        while True:
          print("Searching for Singleplayer button!")
          time.sleep(1)
          if guibot.exists("Singleplayer1"):
            guibot.click("Singleplayer1")
            ClickVersion()
            break
          elif guibot.exists("Singleplayer2"):
            guibot.click("Singleplayer2")
            ClickVersion()
            break
          elif guibot.exists("Singleplayer3"):
            guibot.click("Singleplayer3")
            ClickVersion()
            break
          elif guibot.exists("Singleplayer4"):
            guibot.click("Singleplayer4")
            ClickVersion()
            break
          else:
            if time.time() > _timeout:
              raise Exception("Cannot find 'Singleplayer' button to click! This may be a machine vision issue if the start screen is modded.")
        #Client control here
        time.sleep(warmup)
        
        #pyautogui.keyDown('w')
        #pyautogui.keyDown('space')
        #pyautogui.mouseDown(button='left')
        #pyautogui.move(0, 30, 1)
        pydirectinput.keyDown('space')
        pydirectinput.keyDown('w')
        pydirectinput.mouseDown(button='left')


        if os.path.isfile(csvpath):
          os.remove(csvpath)
        pmonprocess = subprocess.Popen([presentmonpath, "-process_name", "javaw.exe", "-output_file", csvpath, "-terminate_on_proc_exit"], creationflags = subprocess.CREATE_NEW_CONSOLE, shell=True)
        time.sleep(benchtime)

        #Bench period here

        try: 
          subprocess.run([presentmonpath, "-terminate_existing"], creationflags = subprocess.CREATE_NEW_CONSOLE, shell=True)
        except:
          pass
        pmonprocess.terminate()
        #pyautogui.keyUp('w')
        #pyautogui.keyUp('space')
        #pyautogui.mouseUp(button='left')
        pydirectinput.keyUp('w')
        pydirectinput.keyUp('space')
        pydirectinput.mouseUp(button='left')
        if spark:
          pydirectinput.press(r"/")
          pydirectinput.typewrite("sparkc health --memory")
          pydirectinput.press(r"enter")
          pydirectinput.press(r"/")
          pydirectinput.typewrite("sparkc gc")
          pydirectinput.press(r"enter")
          time.sleep(0.3) #make sure log is written to disk
          with open(plog, "r") as f:     #Get spark info from the log
            lines=f.readlines()
            iter = 0
            for l in lines: 
              if "Memory usage:" in l:
                blist[i]["Memory_Usage"].append(float(lines[iter].split(r"Memory usage:\n")[-1].split("GB")[0].strip())) #Memory
              if "CPU usage" in l:
                blist[i]["CPU_Usage"].append(float(lines[iter].split(r"(process)\n\n>")[0].split(",")[-1].split(r"%")[0].strip())) #CPU
              if ("G1 Young Generation" in l) or ("ZGC Pauses collector:" in l) or ("Shenandoah Pauses collector" in l):
                blist[i]["GC_Stop_MS"].append(float(lines[iter].split("ms avg")[0].split(r"\n")[-1].strip()))
                blist[i]["GC_Stops"].append(int(lines[iter].split("ms avg,")[1].split("total")[0].strip()))   #GC Stop-the-world info
              if ("G1 Old Generation" in l):
                g1gc = True
                blist[i]["Oldgen_GCs"].append(int(lines[iter].split(r"G1 Old Generation collector:\n")[-1].split("collections")[0].strip()))    #G1GC Old Gen collections 
              iter = iter + 1


        clientprocess.terminate()  #close presentmon and kill the minecraft client
        time.sleep(1)
        try:
          for proc in psutil.process_iter(['name']):   #Make sure the java client is really dead, as it likes to hang
            if "javaw" in str(proc.name):
              if debug: print("Killing client")
              proc.kill()
        except:
          print("Failed to run psutil loop to kill Minecraft")
        
        frametimes = []
        with open(csvpath, "r") as f:
          csv_reader = csv.DictReader(f, delimiter = ',')
          for line in csv_reader:
            if line['msBetweenPresents'] is not None:
              frametimes.append(float(line['msBetweenPresents']))
        blist[i]["Average_FPS"].append(round(1000 / statistics.mean(frametimes),2)) #Average FPS
        blist[i][r"1%_Frametime_ms"].append(round(statistics.mean(sorted(frametimes)[round(len(frametimes) * 0.99 - 1):]), 2))  #Slowest 1% of frametimes average
        blist[i][r"5%_Frametime_ms"].append(round(statistics.mean(sorted(frametimes)[round(len(frametimes) * 0.95 - 1):]), 2))  #Slowest 5% of frametimes average
        time.sleep(9) #Give the client some time to close, otherwise it may not start up again.
        restore_world()
        with open(benchlog, "w") as f:
          json.dump(blist[0:i+1], f, indent=4)  #Write current data to the benchmark log
        #End of iteration loop
      except Exception as e: #Clean up
        try: 
          subprocess.run([presentmonpath, "-terminate_existing"])
        except:pass
        try:
          clientprocess.terminate()  #close presentmon and kill the minecraft client
          pmonprocess.terminate()
          time.sleep(1)
        except:pass
        try:
          for proc in psutil.process_iter(['name']):   #Make sure the java client is really dead, as it likes to hang
            if "javaw" in str(proc.name):
              if debug: print("Killing client")
              proc.kill()
        except:pass
        time.sleep(4) #Give the client some time to close, otherwise it may not start up again.
        restore_world()
        time.sleep(1)
        print("Error in client benchmark iteration!")
        print(traceback.format_exc())



    try: 
      if blist[i]["Iterations"] >= 2:
        blist[i]["Net_Average_FPS"] = safemean(blist[i]["Average_FPS"])
        blist[i]["Average_FPS_Variance"] = safevar(blist[i]["Average_FPS"])
        blist[i][r"Average_1%_Frametime_ms"] = safemean(blist[i][r"1%_Frametime_ms"])
        blist[i][r"PVariance_1%_Frametime_ms"] = safevar(blist[i][r"1%_Frametime_ms"])
        blist[i][r"Average_5%_Frametime_ms"] = safemean(blist[i][r"5%_Frametime_ms"])
        blist[i][r"PVariance_5%_Frametime_ms"] = safevar(blist[i][r"5%_Frametime_ms"])
        if spark:
          blist[i]["Average_GC_Stop_MS"] = safemean(blist[i]["GC_Stop_MS"])
          blist[i]["PVariance_GC_Stop_MS"] = safevar(blist[i]["GC_Stop_MS"])
          blist[i]["Average_GC_Stops"] = safemean(blist[i]["GC_Stops"])
          blist[i]["Average_Memory_Usage_GB"] = safemean(blist[i]["Memory_Usage"])
          blist[i]["Average_CPU_Usage"] = safemean(blist[i]["CPU_Usage"])
          if g1gc:
            if len(blist[i]["Oldgen_GCs"]) > 1:
              blist[i]["Average_Oldgen_GCs"] = safemean(blist[i]["Oldgen_GCs"])
    except Exception as e:
      print("Error saving client benchmark data!")
      print(traceback.format_exc())
        


  
    #---end of client branch---

  elif "Command" in blist[i] and "Path" in blist[i]:
    #---Server branch---
    
    blist[i]["Startup_Times"] = []
    blist[i]["Chunkgen_Times"] = []
    os.chdir(blist[i]["Path"])
    #return world to pre-benchmark state
    def restore_world():
      if os.path.isdir("world") and os.path.isdir("_world_backup"):
        try:
          shutil.rmtree("world")
        except:
          time.sleep(7) #The old server is still up, give it some time to close
          shutil.rmtree("world")
        os.rename("_world_backup", "world")
    atexit.register(restore_world)
    restore_world() #restore backup in case it wasnt restored on exit before

    #Start building the Minecraft command
    if plat == "Linux":
      command = "nice -n -18 " + blist[i]["Command"]
    else:
      command = blist[i]["Command"]

    #Try to find Fabric
    d = glob.glob("*.jar")
    for f in d:
      if ("fabric-" in os.path.basename(f)) and "fabric-installer" not in os.path.basename(f):
        if debug: print("Found Fabric: " + f)
        chunkgen_command = fabric_chunkgen_command
        chunkgen_expect = fabric_chunkgen_expect
        command = command + " -jar " + os.path.basename(f)
        if nogui:
          command = command + ngui
        break
    
    #Try to find Forge
    d = glob.glob(r"libraries/net/minecraftforge/forge/*/win_args.txt")
    if len(d) == 1:
      if debug: print("Found Forge" + d[0])
      chunkgen_command = forge_chunkgen_command
      chunkgen_expect = forge_chunkgen_expect
      if plat == "Linux":
        command = command + " @" + os.path.normpath(os.path.join(os.path.dirnamme(d[0]), r"unix_args.txt")) + ngui + r' "$@"'
      else:
        command = command + " @" + os.path.normpath(d[0]) + r" %*"
        if nogui:
          command = command + " --nogui"
      

    #Try to find Spark and/or Carpet mods
    if os.path.isdir("mods"):
      mods = glob.glob("mods/*.jar")
      spark = any('spark' in s for s in mods) #Check for Spark mod
      if spark:
        blist[i]["Average_TPS_Values"] = []   #initialize lists
        blist[i]["GC_Stop_MS"] = []
        blist[i]["GC_Stops"] = []
        blist[i]["Oldgen_GCs"] = []
        blist[i]["Memory_Usage"] = []
        blist[i]["CPU_Usage"] = []
      hascarpet =  any('fabric-carpet' in s for s in mods)
      if hascarpet:
        blist[i]["Player_Spawn_Times"] = []
      
    else: 
      if debug: print("No mods folder found")

    #Helper function for crash notification
    def qw(s):
      print("Startup error, please check the server log: " + s)
      blist[i]["Startup_Times"].append(s)
      blist[i]["Chunkgen_Times"].append(s)

    #bench minecraft for # of iterations  
    for n in range(1, blist[i]["Iterations"] + 1):
      #Backup existing world to restore later
      if os.path.isdir("world") and not os.path.isdir("_world_backup"):
        try:
          shutil.copytree("world", "_world_backup")
        except:
          time.sleep(3)
          shutil.copytree("world", "_world_backup", dirs_exist_ok=True)
      try:
        #Delete chunky config if found, as it stores jobs there
        if os.path.isfile(r"config/chunky.json"):
          if debug: print("Removing chunky config")
          os.remove(r"config/chunky.json")

        #Start Minecraft
        print("Running '" + blist[i]["Name"] + "' iteration " + str(n))
        if debug:print(command)
        start = time.time()
        try:
          
          mcserver = popen_spawn.PopenSpawn(command, timeout=totaltimeout, maxread=20000000)   #Start Minecraft server
        except Exception as e:
          print("Error running the command:")
          print(command)
          raise e
        if debug: print("Starting server: " + command)
        time.sleep(0.01)
        if plat == "Windows":
          try:
            for proc in psutil.process_iter(['name']):   #Set to high process priority in windows, for greater consistency when run in the background
              if "java" in str(proc.name):
                if debug: print("Setting Priority")
                proc.nice(psutil.HIGH_PRIORITY_CLASS)
          except:
            print("Failed to set process priority, please run this benchmark as an admin!")
        crash = False
        index = mcserver.expect_exact(pattern_list=[r'''! For help, type "help"''', 'Minecraft Crash Report', pexpect.EOF, pexpect.TIMEOUT], timeout=startuptimeout)  #wait until the server is started
        if index == 0:
          if debug: print("Server started")
        elif index == 1:
          mcserver.sendline('stop')
          time.sleep(0.01)
          mcserver.kill(signal.SIGTERM)
          qw("CRASH")
          print(command)
          crash = True
        elif index == 2:
          qw("STOPPED")
          print(command)
          crash = True
        elif index == 3:
          mcserver.sendline('stop')
          mcserver.kill(signal.SIGTERM)
          qw("TIMEOUT")
          print(command)
          crash = True
        if not crash:
          blist[i]["Startup_Times"].append(round(time.time() - start , 2))
          time.sleep(6)    #Let the server "settle"
          if hascarpet:
            if debug: print("Spawning players")
            start = time.time()
            for x in range(1, carpet + 1):
              mcserver.sendline("player " + str(x) + " spawn")
              mcserver.expect_exact(str(x) + " joined the game")
              mcserver.sendline("player " + str(x) + " look 30 " + str(int(round(360 * x / carpet))))
              mcserver.sendline("player " + str(x) + " jump continuous")
              mcserver.sendline("player " + str(x) + " move forward")
              mcserver.sendline("player " + str(x) + " sprint")
              mcserver.sendline("player " + str(x) + " attack continuous")
            blist[i]["Player_Spawn_Times"].append(round(time.time() - start , 3))
          mcserver.sendline(forceload_cmd) 
          time.sleep(1)    #Let it settle some more
          if debug: print("Generating chunks...")
          start = time.time()
          mcserver.sendline(chunkgen_command)   #Generate chunks
          index = mcserver.expect_exact(pattern_list=[chunkgen_expect, 'Minecraft Crash Report', pexpect.EOF, pexpect.TIMEOUT], timeout=chunkgentimeout)
        
          if index == 0:
            if debug: print("Chunks finished. Stopping server...")
            blist[i]["Chunkgen_Times"].append(round(time.time() - start, 2))
            if spark:
              mcserver.sendline("spark health --memory")
              mcserver.expect_exact("TPS from last 5")
              mcserver.sendline("spark gc")
              mcserver.expect_exact("Garbage Collector statistics")
              time.sleep(0.5) #make sure log is flushed to disk
              with open("logs/latest.log", "r") as f:     #Get spark info from the log
                lines=f.readlines()
                iter = 0
                for l in lines:
                  if "TPS from last 5" in l:
                    blist[i]["Average_TPS_Values"].append(float(lines[iter+1].split(",")[-1][1:-1].split("*")[-1])) #TPS
                  if "Memory usage:" in l:
                    blist[i]["Memory_Usage"].append(float(lines[iter+1].split("GB")[0].strip())) #Memory
                  if "CPU usage" in l:
                    blist[i]["CPU_Usage"].append(float(lines[iter+2].split(",")[-1].split(r"%")[0].strip())) #CPU
                  if ("G1 Young Generation" in l) or ("ZGC Pauses collector:" in l) or ("Shenandoah Pauses collector" in l):
                    blist[i]["GC_Stop_MS"].append(float(lines[iter+1].split("ms avg")[0].strip()))
                    blist[i]["GC_Stops"].append(int(lines[iter+1].split("ms avg,")[-1].split("total")[0].strip()))   #GC Stop-the-world info
                  if ("G1 Old Generation" in l):
                    g1gc = True
                    blist[i]["Oldgen_GCs"].append(int(lines[iter+1].split("collections")[0].strip()))    #G1GC Old Gen collections 
                  iter = iter + 1
          elif index == 1:
            blist[i]["Chunkgen_Times"].append("CRASH")
          elif index == 2:
            blist[i]["Chunkgen_Times"].append("STOPPED")
          elif index == 3:
            blist[i]["Chunkgen_Times"].append("TIMEOUT")
          mcserver.kill(signal.SIGTERM)
        if debug: pprint.pprint(blist[i])
        with open(benchlog, "w") as f:
          json.dump(blist[0:i+1], f, indent=4)  #Write current data to the benchmark log
      except Exception as e:
        print("Error in iteration!")
        print(traceback.format_exc())
        try:
          mcserver.kill(signal.SIGTERM)
          time.sleep(2)
        except:pass
      try:
        restore_world() #Restore the world backup
      except:
        try:
          mcserver.kill(signal.SIGTERM)
        except:pass
        time.sleep(5)
        restore_world() #Sometimes shutil fails if the server is still up, so try again. 

    #End of iteration loop
    try: #Dont let funky data kill the benchmark
      if blist[i]["Iterations"] >= 2:
        blist[i]["Average_Chunkgen_Time"] = safemean(blist[i]["Chunkgen_Times"])
        blist[i]["Average_Startup_Time"] = safemean(blist[i]["Startup_Times"])
        blist[i]["PVariance_Chunkgen_Time"] = safevar(blist[i]["Chunkgen_Times"])
        blist[i]["Pvariance_Startup_Time"] = safevar(blist[i]["Startup_Times"])
        if spark:
          blist[i]["Average_TPS"] = safemean(blist[i]["Average_TPS_Values"])
          blist[i]["PVariance_TPS"] = safevar(blist[i]["Average_TPS_Values"])
          blist[i]["Average_GC_Stop_MS"] = safemean(blist[i]["GC_Stop_MS"])
          blist[i]["PVariance_GC_Stop_MS"] = safevar(blist[i]["GC_Stop_MS"])
          blist[i]["Average_GC_Stops"] = safemean(blist[i]["GC_Stops"])
          blist[i]["Average_Memory_Usage_GB"] = safemean(blist[i]["Memory_Usage"])
          blist[i]["Average_CPU_Usage"] = safemean(blist[i]["CPU_Usage"])
          if g1gc:
            if len(blist[i]["Oldgen_GCs"]) > 1:
              blist[i]["Average_Oldgen_GCs"] = safemean(blist[i]["Oldgen_GCs"])
        if carpet:
          blist[i]["Average_Spawn_Time"] = safemean(blist[i]["Player_Spawn_Times"])
          blist[i]["Player_Spawn_Variance"] = safevar(blist[i]["Player_Spawn_Times"])
    except Exception as e:
      print("Error saving benchmark data!")
      print(traceback.format_exc())

    #---End of server bench branch---
  
  with open(benchlog, "w") as f:
    json.dump(blist[0:i+1], f, indent=4)  #Write current data to the benchmark log
  
  #End of benchmark


#-------------------------------Main thread---------------------------------------------

iter = 0
for bench in blist:
  benchmark(iter)
  iter = iter + 1
  print("Bench completed.")
print("All benches completed.")

#Do stuff with the data in blist here.
