import re
import datetime
import math

from src.utils.db import db
from src.utils.email import mail_client
from src.plugins.jianghu.equipment import 材料等级表, 装备类型表
from src.plugins.jianghu.user_info import UserInfo
from nonebot.adapters.onebot.v11 import MessageSegment
from src.utils.browser import browser


async def 上架商品(寄售人id, 商品名称, 价格, 备注=""):
    if int(价格) < 1:
        return "价格不能少于1两银子"
    if int(价格) > 10000000:
        return "价格不能多于10000000两银子"
    if len(备注) > 30:
        return "备注不能多于30个字"
    # 判断有无
    if re.findall("^[赤橙黄绿青蓝紫彩][金木水火土]$", 商品名称):
        类型 = "材料"
        等级 = 材料等级表[商品名称[0]]
    elif re.findall("^(武器|外装|饰品)\d+$", 商品名称):
        类型 = "图纸"
        等级 = int(商品名称[2:])
    elif re.findall("^.{2,4}[剑杖扇灯锤甲服衫袍铠链牌坠玦环]$", 商品名称):
        类型 = 装备类型表[商品名称[-1]]
    else:
        return "找不到物品名字"

    # 删除背包
    if 类型 in ("材料", "图纸"):
        con = db.knapsack.find_one({"_id": 寄售人id})
        if not con or 商品名称 not in con.get(类型, []):
            return "物品不存在"
        con[类型][商品名称] -= 1
        if con[类型][商品名称] == 0:
            del con[类型][商品名称]
        db.knapsack.update_one({"_id": 寄售人id}, {"$set": con}, True)
    elif 类型 in ("武器", "外装", "饰品"):
        con = db.equip.find_one({"_id": 商品名称})
        if not con or 寄售人id != con.get("持有人", 0):
            return "你没有这件装备"
        装备 = db.jianghu.find_one({"_id": 寄售人id})["装备"]
        if 商品名称 == 装备[con["类型"]]:
            return "该装备正在使用，无法上架"
        等级 = con.get("装备分数", 0)
        db.equip.update_one({"_id": 商品名称}, {"$set": {"持有人": -1}}, True)

    # 重构商品: {类型, 名称, 等级, 寄售人id, 寄售时间, 关注, 备注}
    data = {
        "类型": 类型,
        "等级": 等级,
        "价格": int(价格),
        "名称": 商品名称,
        "寄售人": 寄售人id,
        "日期": datetime.datetime.now(),
        "关注": 0,
        "备注": 备注
    }
    # 上架
    编号 = db.insert_auto_increment("auction_house", data)
    return f"上架[{商品名称}]成功！商品编号：{编号}"


async def 我的商品(操作人id, 命令):
    filter = {"寄售人": 操作人id}
    总数 = db.auction_house.count_documents(filter)
    当前页 = 1
    if 当前页re := re.findall("\d+", 命令):
        当前页 = int(当前页re[0])
    limit = 15
    skip = (当前页 - 1) * limit
    页数 = math.ceil(总数 / limit)
    if 当前页 > 页数:
        return f"只能查到{页数}页"
    result = db.auction_house.find(filter=filter, limit=limit, skip=skip)
    datas = []
    for i in result:
        寄售人 = UserInfo(i["寄售人"])
        datas.append({
            "编号": i["_id"],
            "类型": i["类型"],
            "等级": i["等级"],
            "价格": f"{i['价格']:,}",
            "名称": i["名称"],
            "寄售人": 寄售人.基础属性['名称'],
            "日期": i["日期"].strftime("%Y-%m-%d"),
            "关注": i["关注"],
            "备注": i["备注"],
        })
    pagename = "auction_house.html"
    img = await browser.template_to_image(pagename=pagename,
                                          datas=datas,
                                          当前页=当前页,
                                          页数=页数)
    return MessageSegment.image(img)


async def 下架商品(操作人id, 商品id):
    # 寄售人id是否等于操作人id
    商品 = db.auction_house.find_one({"_id": 商品id})
    if not 商品:
        return "商品不存在！"
    商品类型 = 商品["类型"]
    商品名称 = 商品["名称"]
    寄售人 = 商品["寄售人"]
    if 寄售人 != 操作人id:
        return "这个商品不是你寄售的！"

    # 获得商品
    if 商品类型 in ("材料", "图纸"):
        con = db.knapsack.find_one({"_id": 操作人id})
        if not con:
            con = {}
        if not con.get(商品类型):
            con[商品类型] = {}
        if not con[商品类型].get(商品名称):
            con[商品类型][商品名称] = 0
        con[商品类型][商品名称] += 1
        db.knapsack.update_one({"_id": 操作人id}, {"$set": con}, True)
    elif 商品类型 in ("武器", "外装", "饰品"):
        db.equip.update_one({"_id": 商品名称}, {"$set": {"持有人": 操作人id}}, True)
    # 交易行删除商品
    db.auction_house.delete_one({"_id": 商品id})
    return f"下架{商品名称}成功！"


async def 购买商品(购买人id, 商品id):
    # 购买人银两是否足够
    商品 = db.auction_house.find_one({"_id": 商品id})
    if not 商品:
        return "商品不存在！"
    商品价格 = 商品["价格"]
    商品类型 = 商品["类型"]
    商品名称 = 商品["名称"]
    寄售人 = 商品["寄售人"]
    user_info = db.user_info.find_one({"_id": 购买人id})
    拥有银两 = 0
    if user_info:
        拥有银两 = user_info.get("gold", 0)
    if 商品价格 > 拥有银两:
        return "银两不足！"
    # 获得商品
    if 商品类型 in ("材料", "图纸"):
        con = db.knapsack.find_one({"_id": 购买人id})
        if not con:
            con = {}
        if not con.get(商品类型):
            con[商品类型] = {}
        if not con[商品类型].get(商品名称):
            con[商品类型][商品名称] = 0
        con[商品类型][商品名称] += 1
        db.knapsack.update_one({"_id": 购买人id}, {"$set": con}, True)
    elif 商品类型 in ("武器", "外装", "饰品"):
        db.equip.update_one({"_id": 商品名称}, {"$set": {"持有人": 购买人id}}, True)
    # 交易行删除商品
    db.auction_house.delete_one({"_id": 商品id})
    # 寄售人获得 银两 使用qq邮箱接收信息
    手续费 = 商品价格 // 100
    获得银两 = 商品价格 - 手续费
    db.user_info.update_one({"_id": 购买人id}, {"$inc": {"gold": -商品价格}})
    db.user_info.update_one({"_id": 寄售人}, {"$inc": {"gold": 获得银两}})
    当前时间 = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    购买人 = UserInfo(购买人id)
    await mail_client.send_mail(
        f"{寄售人}@qq.com", f"{商品名称}售卖成功通知",
        f"您寄售的[{商品名称}]于{当前时间}，被【{购买人.基础属性['名称']}】以{商品价格}两银子买走。扣除手续费{手续费}，共获得{获得银两}")
    return f"购买成功！花费{商品价格}两银子，获得[{商品名称}]"


async def 查找商品(condition=""):
    condition_list = condition.split()
    filter = {}
    sort = {}
    for i in condition_list[1:]:
        if re.findall(".+\d+-\d+", i):
            if i[:2] not in ("等级", "价格"):
                continue
            n1, n2 = [int(n) for n in i[2:].split("-")]
            if n1 > n2:
                n2, n1 = n1, n2
            filter[i[:2]] = {"$gte": n1, "$lte": n2}
        elif re.findall("^(等级|价格|日期|关注)[-\+]{0,1}$", i):
            sort[i[:2]] = -1 if i[-1] == "-" else 1
        elif re.findall("^[（\(].+[\)）]$", i):
            filter["备注"] = {"$regex": i[1:-1]}
        elif i == condition_list[1]:
            if i in ("武器", "外装", "饰品", "图纸", "材料", "秘籍", "其他"):
                filter["类型"] = i
            else:
                filter["名称"] = {"$regex": i}
    if not sort:
        sort = {"_id": -1}
    总数 = db.auction_house.count_documents(filter)
    当前页 = 1
    if 当前页re := re.findall("\d+", condition_list[0]):
        当前页 = int(当前页re[0])
    limit = 15
    skip = (当前页 - 1) * limit
    页数 = math.ceil(总数 / limit)
    if 当前页 > 页数:
        return f"只能查到{页数}页"
    result = db.auction_house.find(filter=filter,
                                   sort=list(sort.items()),
                                   limit=limit,
                                   skip=skip)
    datas = []
    for i in result:
        寄售人 = UserInfo(i["寄售人"])
        datas.append({
            "编号": i["_id"],
            "类型": i["类型"],
            "等级": i["等级"],
            "价格": f"{i['价格']:,}",
            "名称": i["名称"],
            "寄售人": 寄售人.基础属性['名称'],
            "日期": i["日期"].strftime("%Y-%m-%d"),
            "关注": i["关注"],
            "备注": i["备注"],
        })
    pagename = "auction_house.html"
    img = await browser.template_to_image(pagename=pagename,
                                          datas=datas,
                                          当前页=当前页,
                                          页数=页数)
    return MessageSegment.image(img)

