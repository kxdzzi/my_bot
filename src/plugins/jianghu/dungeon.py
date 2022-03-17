from src.utils.db import db
from src.plugins.jianghu.jianghu import PK
import os
import yaml


dungeon = os.path.realpath(__file__+"/../jianghu_data/dungeon.yml")
with open(dungeon, "r", encoding="utf-8") as f:
    dungeon_data = yaml.load(f.read(), Loader=yaml.FullLoader)
首领信息 = dungeon_data.get("首领信息")
秘境信息 = dungeon_data.get("秘境信息")

dungeon_boss = os.path.realpath(__file__+"/../jianghu_data/dungeon_boss.yml")
with open(dungeon_boss, "r", encoding="utf-8") as f:
    dungeon_boss_data = yaml.load(f.read(), Loader=yaml.FullLoader)


async def 检查进度(user_id, 秘境名称):
    用户秘境进度 = {}
    if con := db.jianghu.find_one({"_id": user_id}):
        用户秘境进度 = con.get("秘境进度", {})
    前置秘境 = 秘境信息.get(秘境名称, {}).get("前置")
    if 前置秘境:
        秘境通关首领数量 = len([i for i in 用户秘境进度.get(前置秘境, {}).values() if i])
        if not(秘境名称 in 秘境信息 and 秘境通关首领数量 == len(秘境信息[前置秘境]["首领"])):
            return False
    return True


async def 秘境进度(user_id):
    用户秘境进度 = {}
    if con := db.jianghu.find_one({"_id": user_id}):
        用户秘境进度 = con.get("秘境进度", {})
    if not 用户秘境进度:
        return "你还没有挑战过任何秘境"
    msg = "秘境进度"
    for 秘境名称, data in 用户秘境进度.items():
        已通过数量 = len([i for i in data.values() if i])
        总数 = len(秘境信息[秘境名称]["首领"])
        msg += f"\n{秘境名称}: {已通过数量}/{总数}"
    return msg


async def 查看秘境(user_id, 秘境名称):
    # 查看秘境 秘境名称  显示副本的boss
    # 检查前置条件 检查秘境名称
    if not await 检查进度(user_id, 秘境名称):
        return "秘境不存在或未通关前置秘境"
    当前秘境进度 = {}
    if con := db.jianghu.find_one({"_id": user_id}):
        当前秘境进度 = con.get("秘境进度", {}).get(秘境名称, {})
    msg = f"【{秘境名称}】"
    for 首领编号 in 秘境信息[秘境名称]["首领"]:
        首领名称 = dungeon_boss_data[首领编号]['名称']
        msg += f"\n{首领名称}"
        if 当前秘境进度.get(首领名称):
            msg += " 已击杀"
    return msg


async def 挑战秘境(user_id, 首领名称):
    秘境名称 = 首领信息.get(首领名称, {}).get("秘境")
    if not 秘境名称:
        return "找不到首领名称或是未通关前置秘境"
    if not await 检查进度(user_id, 秘境名称):
        return "找不到首领名称或是未通关前置秘境"
    首领编号 = 首领信息.get(首领名称, {}).get("编号")
    if not 首领编号:
        return "找不到首领名称或是未通关前置秘境"
    战斗 = PK()
    return await 战斗.main("秘境首领", user_id, 首领编号)
