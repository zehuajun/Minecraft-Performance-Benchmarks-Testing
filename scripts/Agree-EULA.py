#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
这个脚本用于自动同意 Minecraft EULA
Author: ZeHuaJun
Created on: 2024-06-14
"""

import re

f=open('server/eula.txt','r')
alllines=f.readlines()
f.close()
f=open('server/eula.txt','w+')
for eachline in alllines:
    a=re.sub('false','true',eachline)
f.writelines(a)
f.close()

print("已同意 Minecraft EULA")
