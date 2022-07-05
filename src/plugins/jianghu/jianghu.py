import random

from numpy import arctan
from datetime import datetime
from src.plugins.jianghu.user_info import UserInfo
from src.plugins.jianghu.skill import Skill
from src.utils.db import db
import re
from src.utils.log import logger


class PK(Skill):

    async def compute_buff(self, a: UserInfo):
        pass

    async def compute_debuff(self, 自己: UserInfo, 伤害来源: UserInfo):

        for index, debuff in enumerate(自己.debuff):
            if debuff["type"] == "伤害":
                attack = debuff["伤害"]["attack"]
                damage_value = debuff["伤害"]["damage_value"]
                penetrate = debuff["伤害"]["penetrate"]
                self.造成伤害(伤害来源, 自己, attack, damage_value, penetrate)
            elif debuff["type"] == "减益":
                自己.改变当前状态(debuff["减益"])
            自己.debuff[index]["剩余回合"] -= 1
        自己.debuff = [debuff for debuff in 自己.debuff if debuff["剩余回合"] > 0]

    async def 发动攻击(self, 攻: UserInfo, 守: UserInfo, 当前回合: int):
        攻方主动技能槽位 = [i for i in 攻.基础属性["武学"] if i and self.skill[i]["type"] == "主动招式"]
        self.战斗记录(f"【{攻.名称}】行动")
        攻方限制状态 = [debuff["type"] for debuff in 攻.debuff]
        if "定身" in 攻方限制状态:
            self.战斗记录(f"{攻.名称} 被【定身】当前回合无法行动")
            return
        if 攻方主动技能槽位:
            攻方主动技能 = random.choice(攻方主动技能槽位)
            if 当前回合 < 5 and 当前回合 < len(攻方主动技能槽位):
                攻方主动技能 = 攻方主动技能槽位[当前回合]
            if self.skill[攻方主动技能]["招式类型"] == "外功招式" and "缴械" in 攻方限制状态:
                self.战斗记录(f"{攻.名称} 被【缴械】，{攻方主动技能}无法施放")
                return
            elif self.skill[攻方主动技能]["招式类型"] == "内功招式" and "封内" in 攻方限制状态:
                self.战斗记录(f"{攻.名称} 被【封内】，{攻方主动技能}无法施放")
                return
            重伤状态 = self.skill[攻方主动技能]["招式"](攻, 守)
        else:
            重伤状态, _ = self.造成伤害("普通攻击", 攻, 守, *攻.普通攻击())
        return 重伤状态

    async def 善恶值变化(self, user_id: int, 善恶值: int):
        db.jianghu.update_one({"_id": user_id}, {"$inc": {"善恶值": 善恶值}}, True)

    async def 抢走银两(self, 抢劫方id: int, 被抢方id: int, 银两数量: int):
        if 抢劫方id:
            db.user_info.update_one({"_id": 抢劫方id}, {"$inc": {"gold": 银两数量}})
        if 被抢方id:
            db.user_info.update_one({"_id": 被抢方id}, {"$inc": {"gold": -银两数量}})

    async def 偷袭死斗结算(self, 胜方: UserInfo, 败方: UserInfo):
        gold = 0
        msg = ""
        胜方id = 胜方.基础属性["_id"]
        败方id = 败方.基础属性["_id"]
        胜方名称 = 胜方.基础属性['名称']
        败方名称 = 败方.基础属性['名称']
        总善恶 = 胜方.基础属性['善恶值'] + 败方.基础属性['善恶值']
        抢夺系数 = arctan(-总善恶 / 1000) / 10 + 0.16

        if con := db.user_info.find_one({"_id": 败方id}):
            gold = con.get("gold", 0)
        if gold > 10:
            抢走金额 = random.randint(1, int(gold * 抢夺系数))
            await self.抢走银两(胜方id, 败方id, 抢走金额)
            msg = f"【{胜方名称}】抢走了【{败方名称}】 {抢走金额} 两银子"
        db.jianghu.update_one({"_id": 败方id}, {"$set": {
            "重伤状态": True,
        }}, True)
        return msg

    async def 秘境首领掉落(self, 击杀者: int, 秘境首领: UserInfo):
        user_info = db.user_info.find_one({"_id": 击杀者})
        击败首领次数 = user_info.get("dungeon_num", 0)
        if 击败首领次数 >= 5:
            return "每天只有前 5 次击败秘境首领可以获得奖励"
        精力 = user_info.get("energy", 0)
        if 精力 < 4:
            精力 = 0
            return f"你只有{精力}精力, 无法获得奖励"
        msg = f"今天第 {击败首领次数+1} 次击败秘境首领！消耗精力4, 当前精力{精力-4}<br>"

        掉落 = 秘境首领.基础属性["掉落"]
        物品 = random.choice(list(掉落.keys()))
        数量 = random.randint(1, 掉落[物品])

        材料 = {}
        图纸 = {}
        if con := db.knapsack.find_one({"_id": 击杀者}):
            材料 = con.get("材料", {})
            图纸 = con.get("图纸", {})
        if re.match("[赤橙黄绿青蓝紫彩][金木水火土]", 物品):
            材料数量 = 材料.get(物品, 0) + 数量
            材料.update({物品: 材料数量})
            msg += f"获得材料：{物品}*{数量}<br>"
        else:
            图纸数量 = 图纸.get(物品, 0) + 数量
            图纸.update({物品: 图纸数量})
            msg += f"获得图纸：{物品}*{数量}<br>"
        db.knapsack.update_one({"_id": 击杀者}, {"$set": {
            "材料": 材料,
            "图纸": 图纸
        }}, True)

        # 更新秘境进度
        秘境进度 = db.jianghu.find_one({"_id": 击杀者}).get("秘境进度", {})
        if 秘境首领.基础属性["秘境"] not in 秘境进度:
            秘境进度[秘境首领.基础属性["秘境"]] = {}
        秘境进度[秘境首领.基础属性["秘境"]][秘境首领.名称] = True
        db.jianghu.update_one({"_id": 击杀者}, {"$set": {"秘境进度": 秘境进度}}, True)
        db.user_info.update_one({"_id": 击杀者}, {"$inc": {"dungeon_num": 1, "energy": -4}}, True)
        msg += 秘境首领.基础属性["提示"]
        return msg

    async def 世界首领重伤惩罚(self, 重伤者: int):
        gold = 0
        if con := db.user_info.find_one({"_id": 重伤者}):
            gold = con.get("gold", 0)
        if gold > 10:
            抢走金额 = random.randint(1, int(gold * 0.1))
            await self.抢走银两(0, 重伤者, 抢走金额)
        db.jianghu.update_one({"_id": 重伤者}, {"$set": {
            "重伤状态": True,
        }}, True)
        return f"损失 {抢走金额} 两银子"

    async def 战斗结算(self, action, 攻方: UserInfo, 守方: UserInfo, msg=""):
        攻方_id = 攻方.基础属性["_id"]
        守方_id = 守方.基础属性["_id"]
        日期 = datetime.now().strftime("%Y%m%d")
        data = {
            "日期": int(日期),
            "攻方": 攻方_id,
            "守方": 守方_id,
            "记录": self.战斗内容
        }
        self.编号 = db.insert_auto_increment("pk_log", data=data, id_name="编号")
        永久编号 = f"{日期}-{self.编号}"
        攻方.最终结算(永久编号, 守方_id)
        守方.最终结算(永久编号, 攻方_id)
        if 攻方.本场战斗重伤:
            胜方 = "守"
        elif 守方.本场战斗重伤:
            胜方 = "攻"
        else:
            胜方 = ""
        data = {
            "攻方": {
                "名称": 攻方.基础属性['名称'],
                "id": 攻方_id,
                "当前气血": 攻方.当前气血,
                "气血上限": 攻方.当前状态['气血上限'],
                "气血百分比": 攻方.当前气血/攻方.当前状态['气血上限']*100,
                "减血百分比": (self.攻方初始气血 - 攻方.当前气血)/攻方.当前状态['气血上限']*100,
                "当前内力": 攻方.当前内力,
                "内力上限": 攻方.当前状态['内力上限'],
                "内力百分比": 攻方.当前内力/攻方.当前状态['内力上限']*100,
                "减内百分比": (self.攻方初始内力 - 攻方.当前内力)/攻方.当前状态['内力上限']*100
            },
            "守方": {
                "名称": 守方.基础属性['名称'],
                "id": 守方_id,
                "当前气血": 守方.当前气血,
                "气血上限": 守方.当前状态['气血上限'],
                "气血百分比": 守方.当前气血/守方.当前状态['气血上限']*100,
                "减血百分比": (self.守方初始气血 - 守方.当前气血)/守方.当前状态['气血上限']*100,
                "当前内力": 守方.当前内力,
                "内力上限": 守方.当前状态['内力上限'],
                "内力百分比": 守方.当前内力/守方.当前状态['内力上限']*100,
                "减内百分比": (self.守方初始内力 - 守方.当前内力)/守方.当前状态['内力上限']*100
            }
        }
        if not 胜方:
            data["攻方"]["平"] = True
            data["守方"]["平"] = True
        if action in ("偷袭", "死斗"):
            善恶值 = 0
            if action == "死斗":
                善恶值 = -2
            if 胜方 == "攻":
                善恶值 -= 1
                data["结算"] = await self.偷袭死斗结算(攻方, 守方)
                data["攻方"]["胜负"] = True
                data["守方"]["胜负"] = False
            elif 胜方 == "守":
                data["结算"] = await self.偷袭死斗结算(守方, 攻方)
                data["攻方"]["胜负"] = False
                data["守方"]["胜负"] = True
            if 善恶值:
                await self.善恶值变化(攻方_id, 善恶值)
                data["善恶值"] = f"{攻方.基础属性['名称']} 善恶值 {善恶值}"
        if action == "切磋":
            if 胜方 == "攻":
                data["攻方"]["胜负"] = True
                data["守方"]["胜负"] = False
                data["守方"]["当前气血"] = 1
                守方.当前气血 = 1
                db.jianghu.update_one({"_id": 守方_id}, {"$set": {
                    "当前气血": 1,
                    "重伤状态": False
                }}, True)
            elif 胜方 == "守":
                data["攻方"]["胜负"] = False
                data["守方"]["胜负"] = True
                data["攻方"]["当前气血"] = 1
                攻方.当前气血 = 1
                db.jianghu.update_one({"_id": 攻方_id}, {"$set": {
                    "当前气血": 1,
                    "重伤状态": False
                }}, True)
        if action == "世界首领":
            贡献值 = - 攻方.本次伤害 // 10
            data["守方"]["类型"] = "首领"
            if 胜方 == "攻":
                data["攻方"]["胜负"] = True
                data["守方"]["胜负"] = False
                db.npc.update_one({"_id": 守方_id}, {"$set": {
                    "重伤状态": True,
                }}, True)
            elif 胜方 == "守":
                data["攻方"]["胜负"] = False
                data["守方"]["胜负"] = True
                data["结算"] = await self.世界首领重伤惩罚(攻方_id)
                return data
            else:
                data["攻方"]["平"] = True
                data["守方"]["平"] = True
            if 攻方.本次伤害:
                if not data.get("结算"):
                    data["结算"] = ""
                data["结算"] += f"{攻方.基础属性['名称']} 对 {守方.基础属性['名称']} 造成了 {-攻方.本次伤害} 伤害，贡献值 +{贡献值}, 精力-4"
                db.user_info.update_one({"_id": 攻方.user_id},
                                      {"$inc": {"contribution": 贡献值}}, True)
                if data["守方"]["气血百分比"] < 70 < data["守方"]["气血百分比"]+data["守方"]["减血百分比"]:
                    db.user_info.update_one({"_id": 攻方.user_id}, {"$mul": {"contribution": 1.5}}, True)
                    data["结算"] += f"<br>首领气血被攻下三成，当前贡献值提高 50%！"
                elif data["守方"]["气血百分比"] < 40 < data["守方"]["气血百分比"]+data["守方"]["减血百分比"]:
                    db.user_info.update_one({"_id": 攻方.user_id}, {"$mul": {"contribution": 1.4}}, True)
                    data["结算"] += f"<br>首领气血被攻下六成，当前贡献值提高 40%！"
                elif data["守方"]["气血百分比"] < 10 < data["守方"]["气血百分比"]+data["守方"]["减血百分比"]:
                    db.user_info.update_one({"_id": 攻方.user_id}, {"$mul": {"contribution": 1.3}}, True)
                    data["结算"] += f"<br>首领气血被攻下九成，当前贡献值提高 30%！"
                elif data["守方"]["气血百分比"] <= 0 < data["守方"]["气血百分比"]+data["守方"]["减血百分比"]:
                    db.user_info.update_one({"_id": 攻方.user_id}, {"$mul": {"contribution": 1.2}}, True)
                    data["结算"] += f"<br>首领气被击败！当前贡献值提高 20%！"
                user = db.user_info.find_one({"_id": 攻方.user_id})
                精力 = user['energy']
                data["结算"] += f"<br>当前贡献：{int(user['contribution'])}<br>当前精力: {精力}"
                logger.info(f"<y>{攻方.名称}</y> | <g>世界首领</g> | 伤害：{攻方.本次伤害} | 首领气血：{守方.当前气血}/{守方.当前状态['气血上限']} | 精力：{精力}")

        if action == "秘境首领":
            data["守方"]["类型"] = "首领"
            if 胜方 == "攻":
                data["攻方"]["胜负"] = True
                data["守方"]["胜负"] = False
                data["结算"] = await self.秘境首领掉落(攻方_id, 守方)
            elif 胜方 == "守":
                data["攻方"]["胜负"] = False
                data["守方"]["胜负"] = True
                data["结算"] = await self.世界首领重伤惩罚(攻方_id)
                return data
        if msg:
            data["结算"] += f"<br>{msg}"
        return data

    async def 战前恢复(self, user_info: UserInfo):
        if not user_info.基础属性["气海开关"]:
            return
        气血上限 = user_info.当前状态["气血上限"]
        当前气血 = user_info.当前气血
        需恢复气血 = 气血上限 - 当前气血
        if 需恢复气血 > user_info.当前气海:
            user_info.气血变化(user_info.当前气海)
            user_info.气海变化(-user_info.当前气海)
        else:
            user_info.气血变化(需恢复气血)
            user_info.气海变化(-需恢复气血)
        内力上限 = user_info.当前状态["内力上限"]
        当前内力 = user_info.当前内力
        需恢复内力 = 内力上限 - 当前内力
        if 需恢复内力 > user_info.当前气海:
            user_info.内力变化(user_info.当前气海)
            user_info.气海变化(-user_info.当前气海)
        else:
            user_info.内力变化(需恢复内力)
            user_info.气海变化(-需恢复内力)

    async def main(self, action, 攻方id: int, 守方id: int, msg=""):
        攻方 = UserInfo(攻方id)
        if 攻方.基础属性['名称'] == '无名':
            return "需要改名后才能发起进攻"
        守方 = UserInfo(守方id, action=action)
        self.战斗记录(f"{攻方.名称} ---{action}--> {守方.名称}")
        await self.战前恢复(攻方)
        await self.战前恢复(守方)
        self.攻方初始气血 = 攻方.当前气血
        self.守方初始气血 = 守方.当前气血
        self.攻方初始内力 = 攻方.当前内力
        self.守方初始内力 = 守方.当前内力
        if 攻方.基础属性["重伤状态"]:
            return "你已重伤，无法进攻"
        if 守方.基础属性["重伤状态"]:
            return "对方已重伤，无法进攻"
        回合数 = {"切磋": 10, "偷袭": 10, "死斗": 50, "世界首领": 5, "秘境首领": 10}
        for 当前回合 in range(回合数[action]):
            self.战斗记录(f"---------------- 第 {当前回合+1} 回合 --------------")
            await self.compute_buff(攻方)
            await self.compute_buff(守方)
            await self.compute_debuff(攻方, 守方)
            await self.compute_debuff(守方, 攻方)
            if random.randint(1, 攻方.当前状态['速度']) > random.randint(
                    1, 守方.当前状态['速度']):
                if await self.发动攻击(攻方, 守方, 当前回合):
                    break
                if await self.发动攻击(守方, 攻方, 当前回合):
                    break
            else:
                if await self.发动攻击(守方, 攻方, 当前回合):
                    break
                if await self.发动攻击(攻方, 守方, 当前回合):
                    break
        self.战斗记录("------------------ 战斗结束 -----------------")
        data = await self.战斗结算(action, 攻方, 守方, msg)
        data["战斗编号"] = self.编号
        return data


