
import datetime

from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import PrivateMessageEvent
from nonebot.plugin import on_regex
from src.plugins.jianghu.auction_house import 下架商品
from src.utils.config import config
from src.utils.db import db
from src.utils.log import logger
from src.utils.scheduler import scheduler

activation = on_regex(pattern=r"^激活$",
                      priority=5,
                      block=True)


@activation.handle()
async def _(bot: Bot, event: PrivateMessageEvent):
    bot_id = int(bot.self_id)
    bot_info = db.bot_info.find_one({"_id": bot_id})
    if bot_info.get("master"):
        return
    user_id = int(event.user_id)
    db.bot_info.update_one(
        {"_id": bot_id},
        {"master": user_id, "enable": True, "access_group_num": 20},
        True)
    msg = "激活成功!"
    await activation.finish(msg)


async def remove_group_conf():
    """删除10天未发言的群记录"""
    logger.info("删除10天未发言的群记录")
    db.group_conf.delete_many({
        'last_sent': {
            "$lte": datetime.datetime.today() + datetime.timedelta(days=-3)
        }
    })
    logger.info("重置群完成")


async def archive_river_lantern():
    """河灯归档"""
    logger.info("河灯归档")
    river_lantern_info = db.river_lantern.find({
        'last_sent': {
            "$lte": datetime.datetime.today() + datetime.timedelta(days=-5)
        }
    })
    archive = db.client["archive"]["river_lantern"]
    for lantern in river_lantern_info:
        db.river_lantern.delete_one(lantern)
        del lantern["_id"]
        archive.insert_one(lantern)
    logger.info("河灯归档完成")


async def pull_off_shelves():
    """下架商品"""
    logger.info("下架商品")
    try:
        shelves = db.auction_house.find({
            '日期': {
                "$lte": datetime.datetime.today() + datetime.timedelta(days=-5)
            }
        })

        for i in shelves:
            await 下架商品(i["寄售人"], i["_id"])
        logger.info("自动下架商品完成")
    except Exception as e:
        logger.error(f"下架商品失败: {str(e)}")


@scheduler.scheduled_job("cron", hour=4, minute=0)
async def _():
    '''每天4点开始偷偷的干活'''

    if config.node_info.get("node") == config.node_info.get("main"):
        await remove_group_conf()
        await archive_river_lantern()
        await pull_off_shelves()


@scheduler.scheduled_job("cron", hour=0, minute=0)
async def _():
    '''0点重置'''
    # 重置战斗记录编号
    db.counters.update_one({"_id": "pk_log"}, {"$set": {"sequence_value": 0}})
