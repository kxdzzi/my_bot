
import datetime
from src.utils.db import db
from src.utils.log import logger
from src.utils.config import config
from src.utils.scheduler import scheduler
from src.plugins.jianghu.auction_house import 下架商品


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
