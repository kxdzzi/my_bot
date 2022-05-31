#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import nonebot
from nonebot.adapters.onebot.v11 import Adapter

from src.utils.moinkeypath import monkeypatch
from src.utils.scheduler import start_scheduler

global BOT_NAME_MAP
BOT_NAME_MAP = {}

# 猴子补丁，针对windows平台，更换事件循环
monkeypatch()
nonebot.init()
app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter(Adapter)

# 开启定时器
driver.on_startup(start_scheduler)

# 加载管理插件
nonebot.load_plugins("src/managers")
# 加载其他插件
nonebot.load_plugins("src/plugins")


if __name__ == "__main__":
    nonebot.run()
