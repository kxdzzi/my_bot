import random
from datetime import datetime

from httpx import AsyncClient
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from src.utils.db import db
from src.utils.log import logger
from src.utils.browser import browser
from .zhouyi import suangua

client = AsyncClient()
'''异步请求客户端'''


async def get_sign_in(user_id: int, user_name: str, group_id: int) -> Message:
    '''
    :说明
        用户签到

    :参数
        * user_id：用户QQ
        * group_id：QQ群号

    :返回
        * Message：机器人返回消息
    '''
    gold = 0
    if _con := db.user_info.find_one({'_id': user_id}):
        if _con.get("is_sign"):
            logger.debug(f"<y>群({group_id})</y> | <g>{user_id}</g> | <y>重复签到</y>")
            msg = MessageSegment.text('每天只能签到一次，签到次数会在 8:00 重置')
            return msg
        gold = _con.get("gold", 0)
    suangua_data = suangua()
    prize_pool = db.bot_conf.find_one({'_id': 1}).get("prize_pool", 0)
    if prize_pool < 100000:
        prize_pool = 100000
    get_gold_num = random.randint(10, prize_pool // 1000)
    gold += get_gold_num
    db.bot_conf.update_one({'_id': 1},
                           {'$inc': {
                               "prize_pool": -get_gold_num,
                           }}, True)
    db.user_info.update_one(
        {'_id': user_id},
        {'$set': {
            "is_sign": True,
            "gold": gold,
            "gua": suangua_data
        }}, True)

    # 签到名次
    add_lucky = random.randint(1, 3)
    db.group_conf.update_one({'_id': group_id}, {'$inc': {
        "lucky": add_lucky
    }}, True)
    db.bot_conf.update_one({'_id': 1}, {'$inc': {"sign_num": 1}}, True)
    sign_num = db.bot_conf.find_one({'_id': 1}).get("sign_num", 0)
    logger.debug(f"<y>群({group_id})</y> | <g>{user_id}</g> | <g>签到成功</g>")
    pagename = "sign.html"
    img = await browser.template_to_image(user_name=user_name,
                                          user_id=user_id,
                                          pagename=pagename,
                                          sign_num=sign_num,
                                          get_gold_num=get_gold_num,
                                          add_lucky=add_lucky,
                                          gold=gold,
                                          **suangua_data)
    return MessageSegment.image(img)


async def reset_sign_nums():
    '''重置签到人数与福缘'''

    sign_num = db.bot_conf.find_one({'_id': 1}).get("sign_num", 0)
    prize_pool = sign_num * 5000
    db.bot_conf.update_one({"_id": 1},
                           {'$set': {
                               "sign_num": 0,
                               "prize_pool": prize_pool
                           }}, True)
    db.group_conf.update_many({}, {'$set': {"lucky": 0, "add_group_num": 0}}, True)
    db.user_info.update_many({},
                             {'$set': {
                                 "user_lucky": 1.0,
                                 "is_sign": False,
                                 "river_lantern": 0,
                                 "dungeon_num": 0,
                                 "contribution": 0,
                                 "energy": 100,
                                 "discard_equipment_num": 0
                             }}, True)
