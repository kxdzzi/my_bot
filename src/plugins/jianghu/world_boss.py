from src.utils.cooldown_time import search_record, search_once
from src.plugins.jianghu.jianghu import PK
from src.utils.db import db
import random

world_boss_dict = {"咸鱼": 1, "刀妈": 2, "阿鱼": 3, "忆竹": 4}


async def world_boss(user_id, 世界首领名称):
    if 世界首领名称 not in world_boss_dict:
        if 存活的首领 := db.npc.find({"类型": "首领", "重伤状态": False}):
            msg = "存活的世界首领"
            for 首领 in 存活的首领:
                msg += f"\n【{首领['名称']}】({首领['当前气血']})"
            return msg
        return "没有存活的世界首领"
    n_cd_time = 20
    app_name = "世界首领"
    flag, cd_time = await search_record(user_id, app_name, n_cd_time)
    if not flag:
        msg = f"{cd_time} 后才可以继续进攻"
        return msg
    await search_once(user_id, app_name)
    战斗 = PK()
    return 战斗.main("世界首领", user_id, world_boss_dict[世界首领名称])


def start_resurrection_world_boss():
    project = {"_id": 1, "体质": 1, "根骨": 1}
    if 已重伤首领 := db.npc.find({"类型": "首领", "重伤状态": True}, projection=project):
        已重伤首领列表 = list(已重伤首领)
        if 已重伤首领列表:
            复活首领 = random.choice(已重伤首领列表)
            db.npc.update_one({"_id": 复活首领["_id"]}, {
                "$set": {
                    "重伤状态": False,
                    "当前气血": 复活首领["体质"] * 30,
                    "当前内力": 复活首领["根骨"] * 5
                }
            }, True)
