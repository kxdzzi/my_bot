
import datetime
from src.utils.db import db
from src.utils.log import logger
from src.utils.config import config
from src.utils.scheduler import scheduler


def remove_group_conf():
    """删除10天未发言的群记录"""
    logger.info("删除10天未发言的群记录")
    db.group_conf.delete_many({
        'last_sent': {
            "$lte": datetime.datetime.today() + datetime.timedelta(days=-3)
        }
    })


@scheduler.scheduled_job("cron", hour=4, minute=0)
async def _():
    '''每天4点开始偷偷的干活'''
    if config.node_info.get("node") == "main":
        remove_group_conf()
