import random

import requests
from nonebot import export, on_regex, on_message
import re
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11.permission import GROUP
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from nonebot import on_regex
from nonebot.adapters.onebot.v11 import Bot, MessageSegment
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from src.utils.chat import chat
from tortoise import os

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

img_dir = os.path.realpath(__file__ + "/../img/")

Export = export()
Export.plugin_name = "斗图功能"
Export.plugin_command = "黄图"
Export.plugin_usage = "斗不过你我就生气"
Export.default_status = True

yellow = on_regex(r"^(黄图|色图)$", permission=GROUP, priority=5, block=True)
xz_huopen = on_regex(r"^.{0,5}(肖战|xz|火盆)+.{0,5}$",
                     permission=GROUP,
                     priority=5,
                     block=True)
xz_xia = on_regex(r"^.{0,5}(虾|🦞|🦐)+.{0,5}$",
                  permission=GROUP,
                  priority=5,
                  block=True)

ermaozi = on_message(rule=to_me(),
                     permission=GROUP,
                     priority=10,
                     block=True)


@yellow.handle()
async def _():
    yellow_dir = os.path.join(img_dir, "yellow")
    yellow_path = os.path.join(yellow_dir,
                               random.choice(os.listdir(yellow_dir)))
    with open(yellow_path, "rb") as f:
        msg = MessageSegment.image(f.read())
    await yellow.finish(msg)


@xz_huopen.handle()
async def _():
    huopen = os.path.join(img_dir, "pk", "huopen.gif")
    with open(huopen, "rb") as f:
        msg = MessageSegment.image(f.read())
    await xz_huopen.finish(msg)


@xz_xia.handle()
async def _():
    huopen = os.path.join(img_dir, "pk", "xia.gif")
    with open(huopen, "rb") as f:
        msg = MessageSegment.image(f.read())
    await xz_xia.finish(msg)


@ermaozi.handle()
async def _(event: GroupMessageEvent):
    content = ""
    for i in event.message:
        if i.type == "text":
            content += i.data.get("text", "")
    if content:
        msg = await chat(content)
    else:
        msg = "你说的啥？我看不懂，我觉得你是在为难我二猫子！"
    await ermaozi.finish(msg)
