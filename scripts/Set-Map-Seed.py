#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
这个脚本用于设置一个固定的种子
Author: ZeHuaJun
Created on: 2024-06-14
"""

import re

f=open('server/server.properties','r')
alllines=f.readlines()
f.close()
f=open('server/server.properties','w+')
for eachline in alllines:
    a=re.sub('level-seed=','level-seed=114514',eachline)
f.writelines(a)
f.close()