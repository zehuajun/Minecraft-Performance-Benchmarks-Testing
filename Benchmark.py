#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 这个基准测试脚本来自 https://github.com/brucethemoose/Minecraft-Performance-Flags-Benchmarks 作者为 brucethemoose 使用 MIT 协议开源
# ZeHuaJun 进行二次更改

# 此基准测试脚本仅用于 在 Linux 上的 Fabric 我的世界 服务器性能测试

import os,time,shutil,glob,datetime,json,signal,statistics,pprint,subprocess,csv,atexit,traceback
import psutil  
import pexpect
from pexpect import popen_spawn



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
    "Path": "/home/runner/work/Minecraft-Performance-Benchmarks-Testing/Minecraft-Performance-Benchmarks-Testing/server",
    "Iterations": 1
  }

]

#----------------------其他选项--------------------------

#服务器基准测试选项
carpet = 67 #如果存在“地毯”织物mod，则模拟玩家的数量
fabric_chunkgen_command = r"chunky start"      # 要在 fabric packs 中使用的块生成命令
fabric_chunkgen_expect =  r"[Chunky] Task finished for"   # 块生成完成时要查找的字符串
startuptimeout= 350 # 在认为服务器已关闭/卡住之前等待的秒数
chunkgentimeout = 600 # 在考虑服务器已关闭/卡住之前等待区块生成的秒数 
totaltimeout = 1200 # 整个服务器在超时前可以运行的秒数。
forceload_cmd= r"forceload add -120 -120 120 120" # 用于强制加载矩形的命令。也可以是其他一些服务器控制台命令




#-------------------------代码----------------------------
# 您不应该配置此行以下的任何内容！

debug = True
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


  if "Command" in blist[i] and "Path" in blist[i]:
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
    command = "nice -n -18 " + blist[i]["Command"]

    #Try to find Fabric
    d = glob.glob("*.jar")
    for f in d:
      if ("fabric-" in os.path.basename(f)) and "fabric-installer" not in os.path.basename(f):
        if debug: print("Found Fabric: " + f)
        chunkgen_command = fabric_chunkgen_command
        chunkgen_expect = fabric_chunkgen_expect
        command = command + " -jar " + os.path.basename(f)
        command = command + ngui
        break


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
              print("第 " + str(x) + " 个假人加入服务器")
              time.sleep(8)
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
