import time
from nonebot.adapters.onebot.v11 import Bot
from datetime import datetime

from src.utils.db import db


async def del_bot_to_group(bot: Bot, group_id, msg=None, exit_group=True):
    '''退群动作'''
    try:
        bot_id = int(bot.self_id)
        if exit_group:
            if msg:
                # 退群前发送消息
                await bot.send_group_msg(group_id=group_id, message=msg)
                time.sleep(0.5)
            # 退群
            await bot.set_group_leave(group_id=group_id, is_dismiss=False)
        # 删除数据库中的机器人记录
        db.group_conf.update_one({
            '_id': group_id,
            'bot_id': bot_id
        }, {'$set': {
            "bot_id": 0
        }})
        ret_msg = f"成功退群 {group_id}"
    except:
        ret_msg = f"退群 {group_id} 失败"
    return ret_msg


def add_black_list(_id, black_type, black_time, remark=""):
    """
    加黑
    """
    management_db = db.client["management"]
    if black_type == "QQ":
        black = management_db.user_black_list
    else:
        black = management_db.group_black_list
    today_time_int = int(time.mktime(datetime.now().timetuple())) * 1000
    black.update_one({"_id": _id}, {
        "$set": {
            "block_time": today_time_int + black_time * 1000,
            "remark": remark
        },
        "$inc": {
            "black_num": 1
        }
    }, True)


def check_black_list(_id, black_type):
    """
    检查是否在黑名单中
    """
    management_db = db.client["management"]
    if black_type == "QQ":
        black = management_db.user_black_list
    else:
        black = management_db.group_black_list
    today_time_int = int(time.mktime(datetime.now().timetuple())) * 1000
    black_info = black.find_one({
        '_id': _id,
        "block_time": {
            "$gt": today_time_int
        }
    })
    if black_info:
        return True, black_info.get("remarks")
    return False, ""
