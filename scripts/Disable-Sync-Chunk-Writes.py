#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
这个脚本用于自动关闭 sync-chunk-writes
Author: ZeHuaJun
Created on: 2024-06-14
"""

import re

f=open('server/server.properties','r')
alllines=f.readlines()
f.close()
f=open('server/server.properties','w+')
for eachline in alllines:
    a=re.sub('sync-chunk-writes=true','sync-chunk-writes=false',eachline)
f.writelines(a)
f.close()
