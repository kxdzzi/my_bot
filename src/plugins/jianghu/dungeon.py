from src.utils.db import db
from src.plugins.jianghu.jianghu import PK
import os
import yaml


dungeon = os.path.realpath(__file__+"/../jianghu_data/dungeon.yml")
with open(dungeon, "r", encoding="utf-8") as f:
    dungeon_data = yaml.load(f.read(), Loader=yaml.FullLoader)
首领信息 = dungeon_data.get("首领信息")
秘境信息 = dungeon_data.get("首领信息")


def 检查进度(user_id, 秘境名称):
    秘境进度 = {}
    if con := db.jianghu.find_one({"_id": user_id}):
        秘境进度 = con.get("秘境进度", {})
    前置秘境 = 秘境信息.get(秘境名称, {}).get("前置")
    if 前置秘境:
        秘境通关首领数量 = len((i for i in 秘境进度.get(前置秘境, {}).values() if i))
        if not(秘境名称 in 秘境信息 and 秘境通关首领数量 == len(秘境信息[前置秘境]["首领"])):
            return False
    return True


def 查看秘境(user_id, 秘境名称):
    # 查看秘境 秘境名称  显示副本的boss
    # 检查前置条件 检查秘境名称
    if not 检查进度(user_id, 秘境名称):
        return "秘境不存在或未通关前置秘境"


async def 挑战秘境(user_id, 首领名称):
    秘境名称 = 首领信息.get(首领名称, {}).get("秘境")
    if not 秘境名称:
        return "找不到首领名称或是未通关前置秘境"
    if not 检查进度(user_id, 秘境名称):
        return "找不到首领名称或是未通关前置秘境"
    首领编号 = 首领信息.get(首领名称, {}).get("编号")
    if not 首领编号:
        return "找不到首领名称或是未通关前置秘境"
    战斗 = PK()
    return 战斗.main("秘境首领", user_id, 首领编号)

# 挑战秘境 首领名称/秘境名称 挑战boss或是一键挑战
# 需要前置条件

# 秘境进度
# 秘境1 (3/3)
# 秘境1 (3/3)