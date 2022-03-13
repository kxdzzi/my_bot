from nonebot import export, on_regex
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP
from src.utils.log import logger
from src.utils.scheduler import scheduler

from . import data_source as source

Export = export()
Export.plugin_name = "每日签到"
Export.plugin_command = "签到"
Export.plugin_usage = "每天签到一次，可以获取银两，还可能获得神秘奖励"
Export.default_status = True


sign = on_regex(r"^签到$", permission=GROUP, priority=5, block=True)


@sign.handle()
async def _(event: GroupMessageEvent):
    '''签到系统'''
    user_id = event.user_id
    group_id = event.group_id
    user_name = event.sender.nickname
    logger.debug(
        f"<y>群({group_id})</y> | <g>{user_id}</g> | 请求签到"
    )
    msg = await source.get_sign_in(user_id, user_name, group_id)
    await sign.finish(msg)


@scheduler.scheduled_job("cron", hour=8, minute=0)
async def _():
    '''每天零点重置签到人数'''
    logger.info("正在重置签到人数")
    await source.reset_sign_nums()
    logger.info("签到人数已重置")
