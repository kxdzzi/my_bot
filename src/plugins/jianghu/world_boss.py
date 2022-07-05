from src.utils.cooldown_time import search_record, search_once
from nonebot.adapters.onebot.v11 import MessageSegment
from src.plugins.jianghu.jianghu import PK
from src.utils.db import db
import random

world_boss_dict = {"咸鱼": 1, "刀妈": 2, "阿鱼": 3, "忆竹": 4}


async def world_boss(user_id, 世界首领名称):
    if 世界首领名称 not in world_boss_dict:
        if not db.npc.count_documents({"类型": "首领", "重伤状态": False}):
            return "没有存活的世界首领"
        存活的首领 = db.npc.find({"类型": "首领", "重伤状态": False})
        msg = "存活的世界首领"
        for 首领 in 存活的首领:
            msg += f"\n【{首领['名称']}】({首领['当前气血']})"
        return msg
    app_name = "世界首领"
    if  db.user_info.find_one({"_id": user_id}).get("重伤状态"):
        return "你已重伤，无法进攻世界首领"
    if  db.npc.find_one({"_id": world_boss_dict[世界首领名称]}).get("重伤状态"):
        return "该首领已重伤，无法继续进攻"
    user_info = db.user_info.find_one({"_id": user_id})
    精力 = user_info.get("energy", 0)
    if 精力 < 4:
        return f"你只有{精力}精力, 无法获得奖励"
    db.user_info.update_one({"_id": user_id}, {"$inc": {"energy": -4}})
    n_cd_time = 5
    flag, cd_time = await search_record(user_id, app_name, n_cd_time)
    if not flag:
        msg = MessageSegment.at(user_id) + f"{cd_time}后才可以继续进攻, 精力-4, 当前精力: {精力-4}"
        return msg
    await search_once(user_id, app_name)
    战斗 = PK()
    return await 战斗.main("世界首领", user_id, world_boss_dict[世界首领名称])
