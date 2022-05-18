import os
from nonebot import export, on_regex
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.adapters.onebot.v11.permission import GROUP
from src.utils.browser import browser
from src.utils.log import logger


img_dir = os.path.realpath(__file__ + "/../img/")

Export = export()
Export.plugin_name = "投喂"
Export.plugin_command = "投喂"
Export.plugin_usage = "钱多的老爷可以投喂，但是不会获得任何收益"
Export.default_status = True

tipping = on_regex(r"^(投喂|打赏)*$", permission=GROUP, priority=1, block=True)


@tipping.handle()
async def _(event: GroupMessageEvent):
    '''个人信息'''
    user_id = event.user_id
    group_id = event.group_id
    user_name = event.sender.nickname
    logger.info(f"<y>群{group_id}</y> | <g>{user_name}({user_id})</g> | 投喂")
    pagename = "tipping.html"
    img = await browser.template_to_image(pagename=pagename)
    await tipping.finish(MessageSegment.image(img))
