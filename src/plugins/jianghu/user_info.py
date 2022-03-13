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


dungeon_boss = os.path.realpath(__file__+"/../jianghu_data/dungeon_boss.yml")


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
        self.名称 = self.基础属性["名称"]
        self.当前气血 = self.基础属性["当前气血"]
        self.当前内力 = self.基础属性["当前内力"]
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

        self.初始状态["状态抗性"] = 0

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

    def 计算当前状态(self):
        self.初始化状态()
        for k in self.初始状态:
            self.当前状态[k] = self.初始状态[k] + self.动态状态[k]
        if self.当前气血 > self.当前状态["气血上限"]:
            self.当前气血 = self.当前状态["气血上限"]
            db.jianghu.update_one({"_id": self.user_id}, {"$set": {"当前气血": self.当前气血}}, True)
        if self.当前内力 > self.当前状态["内力上限"]:
            self.当前内力 = self.当前状态["内力上限"]
            db.jianghu.update_one({"_id": self.user_id}, {"$set": {"当前内力": self.当前内力}}, True)

    def 普通攻击(self):
        身法 = self.基础属性["身法"]
        if self.当前状态["外功攻击"] - 身法 < 0:
            攻击下限 = 0
        else:
            攻击下限 = self.当前状态["外功攻击"] - 身法

        攻击伤害 = randint(攻击下限, self.当前状态["外功攻击"] + 身法)
        return ["外功伤害", 攻击伤害, self.当前状态["外功穿透"]]

    def 改变当前状态(self, 变动信息: dict):
        for k, v in 变动信息.items():
            if k in self.动态状态:
                self.动态状态[k] += v
            if k in self.基础属性:
                self.基础属性[k] += v
        self.计算当前状态()

    def 气血变化(self, 气血变化量):
        if self.基础属性.get("类型") in ("首领", ):
            db.npc.update_one({"_id": self.user_id}, {"$inc": {"当前气血": 气血变化量}}, True)
            self.当前气血 = db.npc.find_one({"_id": self.user_id})["当前气血"]
        elif self.基础属性.get("类型") == "秘境首领":
            self.当前气血 += 气血变化量
        else:
            db.jianghu.update_one({"_id": self.user_id}, {"$inc": {"当前气血": 气血变化量}}, True)
            self.当前气血 = db.jianghu.find_one({"_id": self.user_id})["当前气血"]

    def 内力变化(self, 内力变化量):
        if self.基础属性.get("类型") in ("首领", ):
            db.npc.update_one({"_id": self.user_id}, {"$inc": {"当前内力": 内力变化量}}, True)
            self.当前内力 = db.npc.find_one({"_id": self.user_id})["当前内力"]
        elif self.基础属性.get("类型") == "秘境首领":
            self.当前内力 += 内力变化量
        else:
            db.jianghu.update_one({"_id": self.user_id}, {"$inc": {"当前内力": 内力变化量}}, True)
            self.当前内力 = db.jianghu.find_one({"_id": self.user_id})["当前内力"]


