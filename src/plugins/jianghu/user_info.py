import imp
from random import randint
from src.utils.db import db
import os
import yaml


def init_user_info(user_id):
    init_data = {
        "_id": user_id,
        "名称": "无名",
        "体质": 20,
        "身法": 5,
        "力道": 5,
        "根骨": 5,
        "元气": 5,
        "当前气血": 600,
        "当前内力": 50,
        "当前气海": 1000,
        "气海上限": 1000,
        "重伤状态": False,
        "善恶值": 0,
        "可用属性": 5,
        "已用属性": 0,
        "武学": ["", "", "", "", ""],
        "已领悟武学": [],
        "装备": {
            "外装": "",
            "武器": "",
            "饰品": "",
        },
    }
    db.jianghu.insert_one(init_data)
    return init_data


dungeon_boss = os.path.realpath(__file__ + "/../jianghu_data/dungeon_boss.yml")


class UserInfo():

    def __init__(self, user_id, action="") -> None:
        self.user_id = user_id
        if action == "世界首领":
            user_info = db.npc.find_one({"_id": user_id})
            if not user_info:
                return
        elif action == "秘境首领":
            with open(dungeon_boss, "r", encoding="utf-8") as f:
                boss_data = yaml.load(f.read(), Loader=yaml.FullLoader)
                user_info = boss_data[user_id]
        else:
            user_info = db.jianghu.find_one({"_id": user_id})
            if not user_info:
                user_info = init_user_info(user_id)
        self.基础属性 = user_info
        self.装备列表 = []
        for i in self.基础属性["装备"].values():
            装备 = db.equip.find_one({"_id": i}, projection={"_id": 0})
            if 装备:
                self.装备列表.append(装备)
        self.本次伤害 = 0
        self.本次治疗 = 0
        self.气血变化量 = 0
        self.内力变化量 = 0
        self.名称 = self.基础属性["名称"]
        self.当前气血 = self.基础属性["当前气血"]
        self.当前内力 = self.基础属性["当前内力"]
        self.当前气海 = self.基础属性["当前气海"]
        self.重伤状态 = self.基础属性["重伤状态"]
        self.初始状态 = {}
        self.当前状态 = {}
        self.动态状态 = {}
        self.获取基础属性()
        self.初始化动态状态()
        self.计算当前状态()

    def 恢复所有气血(self):
        self.当前气血 = self.当前状态['气血上限']

    def 获取基础属性(self):
        # 初始化buff
        self.buff = []
        self.debuff = []
        for i in self.装备列表:
            self.buff.extend(i.get("buff", []))
            self.debuff.extend(i.get("debuff", []))
            for k, v in i.get("基础属性", {}).items():
                self.基础属性[k] += v

    def 初始化状态(self):
        # 初始化属性
        self.初始状态["速度"] = self.基础属性["身法"]

        self.初始状态["气血上限"] = self.基础属性["体质"] * 30
        self.初始状态["内力上限"] = self.基础属性["根骨"] * 5
        # self.初始状态["当前内力"] = self.基础属性["当前内力"]

        self.初始状态["外功攻击"] = self.基础属性["力道"] * 2
        self.初始状态["外功穿透"] = self.基础属性.get("外功穿透", 0)

        self.初始状态["内功攻击"] = self.基础属性["元气"] * 2
        self.初始状态["内功穿透"] = self.基础属性.get("内功穿透", 0)

        self.初始状态["状态抗性"] = self.基础属性["根骨"]

        self.初始状态["外功防御"] = self.基础属性.get("外功防御", 0)
        self.初始状态["内功防御"] = self.基础属性.get("内功防御", 0)

    def 初始化动态状态(self):
        self.动态状态["速度"] = 0

        self.动态状态["气血上限"] = 0
        self.动态状态["内力上限"] = 0

        self.动态状态["外功攻击"] = 0
        self.动态状态["外功穿透"] = 0

        self.动态状态["内功攻击"] = 0
        self.动态状态["内功穿透"] = 0

        self.动态状态["状态抗性"] = 0

        self.动态状态["外功防御"] = 0
        self.动态状态["内功防御"] = 0

        for i in self.装备列表:
            for k, v in i.get("附加属性", {}).items():
                self.动态状态[k] += v
            for k, v in i.get("镶嵌属性", {}).items():
                self.动态状态[k] += v

    def 计算当前状态(self):
        self.初始化状态()
        for k in self.初始状态:
            self.当前状态[k] = self.初始状态[k] + self.动态状态[k]
        if self.当前气血 > self.当前状态["气血上限"]:
            self.当前气血 = self.当前状态["气血上限"]
            db.jianghu.update_one({"_id": self.user_id},
                                  {"$set": {
                                      "当前气血": self.当前气血
                                  }}, True)
        if self.当前内力 > self.当前状态["内力上限"]:
            self.当前内力 = self.当前状态["内力上限"]
            db.jianghu.update_one({"_id": self.user_id},
                                  {"$set": {
                                      "当前内力": self.当前内力
                                  }}, True)

    def 普通攻击(self):
        浮动 = self.基础属性["身法"] // 2
        if self.当前状态["外功攻击"] - 浮动 < 0:
            攻击下限 = 0
        else:
            攻击下限 = self.当前状态["外功攻击"] - 浮动

        攻击伤害 = randint(攻击下限, self.当前状态["外功攻击"] + 浮动)
        return ["外功伤害", 攻击伤害, self.当前状态["外功穿透"]]

    def 改变当前状态(self, 变动信息: dict):
        for k, v in 变动信息.items():
            if k in self.动态状态:
                self.动态状态[k] += v
            if k in self.基础属性:
                self.基础属性[k] += v
        self.计算当前状态()

    def 最终结算(self, 战斗编号=None, 敌方id=None):
        """
        # 是否重伤, 是否本场战斗重伤, 剩余血量
        """
        self.本场战斗重伤 = False
        if self.基础属性.get("类型") in ("首领", ):
            db_con = db.npc
        else:
            db_con = db.jianghu

        if self.基础属性.get("类型") == "秘境首领":
            user_info = self.基础属性
        else:
            user_info = db_con.find_one({"_id": self.user_id})

        if user_info["重伤状态"]:
            self.重伤状态 = True
            return

        self.当前气血 = user_info["当前气血"] + self.气血变化量
        self.当前内力 = user_info["当前内力"] + self.内力变化量
        if self.当前气血 <= 0:
            self.当前气血 = 0
            self.重伤状态 = True
            self.本场战斗重伤 = True
        if self.当前内力 < 0:
            self.当前内力 = 0

        if self.基础属性.get("类型") != "秘境首领":
            db_con.update_one(
                {"_id": self.user_id},
                {"$set": {
                    "当前气血": self.当前气血,
                    "当前内力": self.当前内力,
                    "当前气海": self.当前气海,
                    "重伤状态": self.重伤状态,
                    "击杀人": 敌方id,
                    "战斗编号": 战斗编号
                }}, True)

    def 气血变化(self, 气血变化量):
        气血变化量 = int(气血变化量)

        有效变化 = 气血变化量
        # 治疗溢出
        损失气血 = self.当前状态['气血上限'] - self.当前气血
        if 气血变化量 > 损失气血 >= 0:
            有效变化 = 损失气血

        # 重伤
        if (气血变化量 + self.当前气血) <= 0:
            有效变化 = -self.当前气血
            self.重伤状态 = True
        self.当前气血 += 有效变化
        self.气血变化量 += 有效变化

        return 有效变化

    def 内力变化(self, 内力变化量, 强行扣除=False):
        内力变化量 = int(内力变化量)

        有效变化 = 内力变化量
        # 回内溢出
        损失内力 = self.当前状态['内力上限'] - self.当前内力
        if 内力变化量 > 损失内力 >= 0:
            有效变化 = 损失内力

        # 内力不足
        if 内力变化量 + self.当前内力 < 0:
            有效变化 = 0
            if 强行扣除:
                有效变化 = -self.当前内力

        self.当前内力 += 有效变化
        self.内力变化量 += 有效变化

        return 有效变化

    def 气海变化(self, 气海变化量):
        气海变化量 = int(气海变化量)

        有效变化 = 气海变化量
        # 回气溢出
        损失气海 = self.基础属性['气海上限'] - self.当前气海
        if 气海变化量 > 损失气海 >= 0:
            有效变化 = 损失气海

        # 气海不足
        if 气海变化量 + self.当前气海 < 0:
            气海变化量 = 0
            有效变化 = 0

        self.当前气海 += 有效变化

        return 有效变化
