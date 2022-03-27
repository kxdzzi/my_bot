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
    n_cd_time = 10
    app_name = "世界首领"
    world_boss_num = db.user_info.find_one_and_update(
            filter={"_id": user_id},
            update={"$inc": {"world_boss_num": 1}},
            upsert=True
        ).get("world_boss_num", 0)
    剩余次数 = 4 - world_boss_num
    if 剩余次数 < -1:
        return
    if 剩余次数 <= 0:
        return MessageSegment.at(user_id) + "进攻次数用尽，发送“领取首领奖励”可以领取奖励"
    flag, cd_time = await search_record(user_id, app_name, n_cd_time)
    if not flag:
        msg = MessageSegment.at(user_id) + f"{cd_time}后才可以继续进攻，还可以进攻当前首领{剩余次数}次"
        return msg
    await search_once(user_id, app_name)
    战斗 = PK()
    return await 战斗.main("世界首领", user_id, world_boss_dict[世界首领名称])


def start_resurrection_world_boss():
    db.user_info.update_many({}, {"$set": {"world_boss_num": 0}}, True)
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
