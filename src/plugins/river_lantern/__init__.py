from nonebot import export, on_regex, on_notice
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.params import Depends
from nonebot.adapters.onebot.v11.event import GroupMessageEvent, PokeNotifyEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from src.utils.log import logger
from src.utils.content_check import content_check
import re

from . import data_source as source

Export = export()
Export.plugin_name = "河灯"
Export.plugin_command = "放河灯"
Export.plugin_usage = "戳一戳二猫子，就会得到一盏河灯。"
Export.default_status = True

sent_river_lantern = on_regex(r"^((放|匿名|回复)河灯.*)$",
                              permission=GROUP,
                              priority=5,
                              block=True)

my_river_lantern = on_regex(r"^(我的河灯)$",
                            permission=GROUP,
                            priority=5,
                            block=True)


async def _is_poke(bot: Bot, event: Event) -> bool:
    return isinstance(event, PokeNotifyEvent) and event.is_tome()


get_river_lantern = on_notice(rule=Rule(_is_poke), priority=3, block=True)

get_river_lantern2 = on_regex(r"^(捡河灯)|(捞河灯)$",
                              permission=GROUP,
                              priority=5,
                              block=True)


def get_content(event: GroupMessageEvent) -> str:
    '''从前置这些可前可后的消息中获取name'''
    text = event.get_plaintext()
    放河灯re = re.compile(r"^[放河灯匿名]{3,4} (.+)$")
    回复河灯re = re.compile(r"^回复河灯 *(\d+)(.+)$")
    类型 = ""
    if 河灯内容 := 放河灯re.findall(text):
        河灯内容 = 河灯内容[0]
        返回 = 河灯内容
        if text.startswith("匿名"):
            类型 = "匿名河灯"
        else:
            类型 = "放河灯"
    elif 河灯内容 := 回复河灯re.findall(text):
        河灯id, 河灯内容 = 河灯内容[0]
        返回 = (河灯id, 河灯内容)
        类型 = "回复河灯"
    else:
        return False, "",  "正确格式是：“放河灯 你想说的话”"
    if len(河灯内容) > 512:
        return False, "", "花笺最多只能写五百一十二个字，再多就写不下了！"
    if not content_check(河灯内容)[0]:
        return False, "", "你的花笺内容太不健康了，我可不敢给你放出去！"
    return True, 类型, 返回


@sent_river_lantern.handle()
async def _(event: GroupMessageEvent, res=Depends(get_content)):
    '''放一盏河灯'''
    user_id = event.user_id
    user_name = event.sender.nickname
    group_id = event.group_id
    result, 类型, content = res
    check_name, _ = content_check(user_name)
    if not check_name:
        await sent_river_lantern.finish("你的昵称违规了，小心被人举报啊！")
    if not result:
        await sent_river_lantern.finish(content)
    if 类型 == "匿名河灯":
        user_name = ""
    logger.debug(
        f"<y>群{group_id}</y> | <g>{user_id}</g> | <e>放河灯</e> | {content}")
    msg = await source.sent_river_lantern(user_id, user_name, 类型, content)
    await sent_river_lantern.finish(msg)


@my_river_lantern.handle()
async def _(event: GroupMessageEvent):
    '''查看个人河灯'''
    user_id = event.user_id
    user_name = event.sender.nickname
    msg = await source.my_river_lantern(user_id, user_name)
    await my_river_lantern.finish(msg)


@get_river_lantern.handle()
async def _(event: PokeNotifyEvent):
    '''戳一戳，捡一个河灯'''
    group_id = event.group_id
    user_id = event.user_id
    logger.debug(f"<y>群{group_id}</y> | <g>{user_id}</g> | <e>捡河灯</e>")
    msg = await source.get_river_lantern(group_id, user_id)
    await get_river_lantern.finish(msg)


@get_river_lantern2.handle()
async def _(event: GroupMessageEvent):
    '''戳一戳，捡一个河灯'''
    group_id = event.group_id
    user_id = event.user_id
    logger.debug(f"<y>群{group_id}</y> | <g>{user_id}</g> | <e>捡河灯</e>")
    msg = await source.get_river_lantern(group_id, user_id)
    await get_river_lantern.finish(msg)
