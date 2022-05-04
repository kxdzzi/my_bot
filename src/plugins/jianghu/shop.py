import random
from src.utils.db import db
from src.plugins.jianghu.user_info import UserInfo


def 材料盒(自己: UserInfo, 数量: int):
    user_id = 自己.基础属性["_id"]
    已有数量 = 0
    con = db.knapsack.find_one({"_id": user_id})
    材料 = {}
    if con:
        材料 = con.get("材料", {})
    msg = "获得材料：\n"
    获取物品列表 = {}
    for _ in range(数量):
        材料属性 = random.choice("金木水火土")
        材料等级 = random.choice("赤橙")
        材料名称 = 材料等级 + 材料属性
        材料数量 = random.randint(1, 3)
        已有数量 = 材料.get(材料名称, 0)
        已有数量 += 材料数量
        材料.update({材料名称: 已有数量})
        if not 获取物品列表.get(材料名称):
            获取物品列表[材料名称] = 0
        获取物品列表[材料名称] += 材料数量
    msg += "、".join([f"{k} * {v}" for k, v in 获取物品列表.items()])
    db.knapsack.update_one({"_id": user_id}, {"$set": {"材料": 材料}}, True)
    return msg


def 图纸盒(自己: UserInfo, 数量: int):
    user_id = 自己.基础属性["_id"]
    con = db.knapsack.find_one({"_id": user_id})
    图纸 = {}
    if con:
        图纸 = con.get("图纸", {})
    msg = "获得图纸：\n"
    获取物品列表 = {}
    for _ in range(数量):
        图纸样式 = random.choice(["武器", "外装", "饰品"])
        图纸等级 = random.randint(10, 30)
        图纸名称 = 图纸样式 + str(图纸等级)
        已有数量 = 0
        已有数量 = 图纸.get(图纸名称, 0)
        已有数量 += 1
        图纸.update({图纸名称: 已有数量})
        if not 获取物品列表.get(图纸名称):
            获取物品列表[图纸名称] = 0
        获取物品列表[图纸名称] += 1
    msg += "、".join([f"{k} * {v}" for k, v in 获取物品列表.items()])
    db.knapsack.update_one({"_id": user_id}, {"$set": {"图纸": 图纸}}, True)
    return msg


def 活血丹(自己: UserInfo, 数量: int):
    if 自己.基础属性["重伤状态"]:
        return "重伤状态下无法使用"
    for _ in range(数量):
        自己.当前气血 += 1000
    if 自己.当前气血 > 自己.当前状态["气血上限"]:
        自己.当前气血 = 自己.当前状态["气血上限"]
    db.jianghu.update_one({"_id": 自己.基础属性["_id"]}, {"$set": {
        "当前气血": 自己.当前气血,
    }}, True)
    return f"使用活血丹成功，当前气血为{自己.当前气血}"


def 大活血丹(自己: UserInfo, 数量: int):
    if 自己.基础属性["重伤状态"]:
        return "重伤状态下无法使用"

    自己.当前气血 = 自己.当前状态["气血上限"]
    db.jianghu.update_one({"_id": 自己.基础属性["_id"]}, {"$set": {
        "当前气血": 自己.当前气血,
    }}, True)
    return f"使用大活血丹成功，当前气血为{自己.当前气血}"


def 疏络丹(自己: UserInfo, 数量: int):
    if 自己.基础属性["重伤状态"]:
        return "重伤状态下无法使用"
    for _ in range(数量):
        自己.当前内力 += 500
    if 自己.当前内力 > 自己.当前状态["内力上限"]:
        自己.当前内力 = 自己.当前状态["内力上限"]
    db.jianghu.update_one({"_id": 自己.基础属性["_id"]}, {"$set": {
        "当前内力": 自己.当前内力,
    }}, True)
    return f"使用疏络丹成功，当前内力为{自己.当前内力}"


def 大疏络丹(自己: UserInfo, 数量: int):
    if 自己.基础属性["重伤状态"]:
        return "重伤状态下无法使用"

    自己.当前内力 = 自己.当前状态["内力上限"]
    db.jianghu.update_one({"_id": 自己.基础属性["_id"]}, {"$set": {
        "当前内力": 自己.当前内力,
    }}, True)
    return f"使用大疏络丹成功，当前内力为{自己.当前内力}"


def 大洗髓丹(自己: UserInfo, 数量: int):
    pass


def 洗髓丹体质(自己: UserInfo, 数量: int):
    pass


def 洗髓丹力道(自己: UserInfo, 数量: int):
    pass


def 洗髓丹元气(自己: UserInfo):
    pass


def 洗髓丹根骨(自己: UserInfo):
    pass


def 洗髓丹身法(自己: UserInfo):
    pass


shop = {
    "材料盒": {
        "价格": 10,
        "使用": 材料盒,
        "使用数量": 10000000
    },
    "图纸盒": {
        "价格": 10,
        "使用": 图纸盒,
        "使用数量": 10000000
    },
    "活血丹": {
        "价格": 50,
        "使用": 活血丹,
        "使用数量": 10
    },
    "大活血丹": {
        "价格": 500,
        "使用": 大活血丹,
        "使用数量": 1
    },
    "疏络丹": {
        "价格": 30,
        "使用": 疏络丹,
        "使用数量": 10
    },
    "大疏络丹": {
        "价格": 300,
        "使用": 大疏络丹,
        "使用数量": 1
    },
    # "大洗髓丹": {
    #     "价格": 5000,
    #     "使用": 大洗髓丹,
    #     "使用数量": 1
    # },
    # "洗髓丹体质": {
    #     "价格": 150,
    #     "使用": 洗髓丹体质,
    #     "使用数量": 5
    # },
    # "洗髓丹力道": {
    #     "价格": 150,
    #     "使用": 洗髓丹力道,
    #     "使用数量": 5
    # },
    # "洗髓丹元气": {
    #     "价格": 150,
    #     "使用": 洗髓丹元气,
    #     "使用数量": 5
    # },
    # "洗髓丹根骨": {
    #     "价格": 150,
    #     "使用": 洗髓丹根骨,
    #     "使用数量": 5
    # },
    # "洗髓丹身法": {
    #     "价格": 150,
    #     "使用": 洗髓丹身法,
    #     "使用数量": 5
    # }
}
