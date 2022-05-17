import math
import random
import copy
import re
import os
from datetime import datetime

from nonebot.adapters.onebot.v11 import Bot
from src.plugins.jianghu.user_info import UserInfo
from src.plugins.jianghu.skill import Skill

from httpx import AsyncClient
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from src.utils.db import db
from src.utils.log import logger
from src.utils.browser import browser
from src.plugins.jianghu.shop import shop
from src.plugins.jianghu.equipment import 打造装备, 合成图纸, 合成材料, 装备价格, 镶嵌装备, 材料等级表
from src.plugins.jianghu.jianghu import PK
from src.plugins.jianghu.world_boss import world_boss, start_resurrection_world_boss
from src.utils.cooldown_time import search_record, search_once
from src.plugins.jianghu.dungeon import 挑战秘境, 查看秘境, 秘境进度


client = AsyncClient()
'''异步请求客户端'''


async def get_my_info(user_id: int, user_name: str) -> Message:
    '''
    :说明
        个人信息

    :参数
        * user_id：用户QQ

    :返回
        * Message：机器人返回消息
    '''

    _con = db.user_info.find_one({'_id': user_id})
    if not _con:
        _con = {}
    last_sign = _con.get("last_sign")
    today = datetime.today()
    suangua_data = {}
    if last_sign and today.date() == last_sign.date():
        suangua_data = _con.get("gua", {})
    gold = _con.get("gold", 0)
    jianghu_data = UserInfo(user_id)
    user_stat = jianghu_data.当前状态
    user_stat["当前气血"] = jianghu_data.当前气血
    user_stat["当前内力"] = jianghu_data.当前内力
    base_attribute = jianghu_data.基础属性
    pagename = "my_info.html"
    if base_attribute.get("击杀人", 0) >= 10000:
        base_attribute["击杀人"] = db.jianghu.find_one({"_id": base_attribute["击杀人"]})["名称"]
    else:
        base_attribute["击杀人"] = "未知目标"
    img = await browser.template_to_image(user_name=user_name,
                                          user_id=user_id,
                                          pagename=pagename,
                                          gold=gold,
                                          user_stat=user_stat,
                                          base_attribute=base_attribute,
                                          suangua_data=suangua_data)
    return MessageSegment.image(img)


async def bind_email(user_id, res):
    if not res:
        return "输入错误"
    my_email = res[0]
    email_pattern = re.compile(r"^\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$")
    match = email_pattern.search(my_email)
    if not match:
        return "邮箱格式错误"
    db.jianghu.update_one({"_id": user_id}, {"$set": {"email": my_email}}, True)
    return "邮箱绑定成功"


async def set_name(user_id, res):
    if not res:
        return "输入错误"
    name = res[0]
    zhPattern = re.compile(u'[\u4e00-\u9fa5]+')
    match = zhPattern.search(name)
    if not match:
        return "名字需要八字以内的汉字"
    if db.jianghu.find_one({"名称": name}) or name == "无名":
        return "名称重复"
    usr = UserInfo(user_id)
    if usr.基础属性["善恶值"] < -1000:
        return "狡诈恶徒不得改名!"
    if usr.名称 != "无名":
        msg = "，花费一百两银子。"
        gold = 0
        con = db.user_info.find_one({"_id": user_id})
        if con:
            gold = con.get("gold", 0)
        if gold < 100:
            return "改名需要花费一百两银子，你的银两不够！"
        db.user_info.update_one({"_id": user_id}, {"$inc": {"gold": -100}})
    else:
        msg = "，首次改名不需要花费银两。"
    db.jianghu.update_one({"_id": user_id}, {"$set": {"名称": name}}, True)
    return "改名成功" + msg


async def dig_for_treasure(user_id, number):
    精力 = db.user_info.find_one({"_id": user_id}).get("energy", 0)
    消耗精力 = number * 10
    if 精力 < 消耗精力:
        精力 = 0
        return f"精力不足, 你只有{精力}精力, 挖宝{number}次需要{消耗精力}精力"
    获得物品 = {}
    for i in random.choices(["青铜宝箱", "精铁宝箱", "素银宝箱", "鎏金宝箱"], k=number):
        if i not in 获得物品:
            获得物品[i] = 0
        获得物品[i] += 1
    db.knapsack.update_one({"_id": user_id}, {"$inc": 获得物品}, True)
    db.user_info.update_one({"_id": user_id}, {"$inc": {"energy": -10}})
    msg = f"精力-10, 获得: {'、'.join([f'{k}*{v}' for k, v in 获得物品.items()])}"
    return msg


async def give_gold(user_id, user_name, at_qq, gold):
    '''赠送银两'''

    logger.debug(f"赠送银两 | <e>{user_id} -> {at_qq}</e> | {gold}")
    at_user_info = UserInfo(at_qq)
    if at_user_info.名称 == "无名":
        return "对方未改名, 无法赠送银两"
    user_info = UserInfo(user_id)
    善恶值 = user_info.基础属性["善恶值"]
    手续费比例 = -善恶值 / 4000
    if 手续费比例 >= 1:
        手续费比例 = 0.9
    if 手续费比例 < 0:
        手续费比例 = 0
    con = db.user_info.find_one({"_id": user_id})
    if not con:
        con = {}
    if con.get("gold", 0) < gold:
        logger.debug(f"赠送银两 | <e>{user_id} -> {at_qq}</e> | <r>银两不足</r>")
        return f"{user_name}，你的银两不足！"
    db.user_info.update_one({"_id": user_id}, {"$inc": {"gold": -gold}}, True)
    手续费 = int(gold * 手续费比例)
    赠送银两 = gold - 手续费
    db.user_info.update_one({"_id": at_qq}, {"$inc": {"gold": 赠送银两}}, True)
    logger.debug(f"赠送银两 | <e>{user_id} -> {at_qq}</e> | <g>成功！</g>")
    if 手续费 > 0:
        msg = f"成功赠送{赠送银两}两银子！(善恶值: {善恶值}, 赠送银两扣除手续费{手续费})"
    else:
        msg = f"成功赠送{赠送银两}两银子！"
    return msg


async def purchase_goods(user_id, res):
    user_info = UserInfo(user_id)
    if user_info.基础属性["善恶值"] < -2000:
        return "善恶值过低, 无法购买物品"
    if len(res) > 2:
        return "输入错误"
    数量 = 1
    商品 = res[0]
    价格 = shop.get(商品, {}).get("价格")
    if len(res) == 2:
        数量 = int(res[1])
    if not 价格:
        return "找不到物品"
    if 数量 < 1:
        return "数量不可以小于1"
    总价 = 价格 * 数量
    con = db.user_info.find_one({"_id": user_id})
    if not con:
        con = {}
    if con.get("gold", 0) < 总价:
        logger.debug(f"购买商品 | {商品} | <e>{user_id}</e> | <r>银两不足</r>")
        return "你的银两不足！"
    db.user_info.update_one({"_id": user_id}, {"$inc": {"gold": -总价}}, True)
    db.knapsack.update_one({"_id": user_id}, {"$inc": {商品: 数量}}, True)
    return "购买成功!"


async def use_goods(user_id, res):
    if len(res) > 2:
        return "输入错误"
    数量 = 1
    物品 = res[0]
    使用物品 = shop.get(物品, {}).get("使用")
    使用数量限制 = shop.get(物品, {}).get("使用数量", 1)
    if not 使用物品:
        return "物品不存在"
    if len(res) == 2:
        数量 = int(res[1])
    if 数量 > 使用数量限制:
        return f"该物品一次只能用{使用数量限制}个"
    con = db.knapsack.find_one({"_id": user_id})
    if not con:
        con = {}
    if con.get(物品, 0) < 数量:
        logger.debug(f"使用物品 | {物品} | <e>{user_id}</e> | <r>物品数量不足</r>")
        return "你的物品数量不足！"
    user_info = UserInfo(user_id)
    db.knapsack.update_one({"_id": user_id}, {"$inc": {物品: -数量}}, True)
    msg = 使用物品(user_info, 数量)
    return msg


async def remove_equipment(user_id, 装备名称):
    """摧毁装备"""
    con = db.equip.find_one({"_id": 装备名称})
    if not con:
        return "该装备不存在"
    if con["持有人"] != user_id:
        return "你没有此装备"
    if con.get("标记"):
        return "该装备已被标记，无法摧毁"
    装备 = db.jianghu.find_one({"_id": user_id})["装备"]
    if 装备名称 == 装备[con["类型"]]:
        return "该装备正在使用，无法摧毁"

    db.equip.delete_one({"_id": 装备名称})
    return f"成功摧毁装备{装备名称}"


async def tag_gear(user_id, 装备名称: str, 标记: str):
    '''标记装备'''
    if 标记 and len(标记) != 2:
        return "标记必须为两个字"
    con = db.equip.find_one({"_id": 装备名称})
    if not con:
        return "该装备不存在"
    if con["持有人"] != user_id:
        return "你没有此装备"
    if 标记:
        db.equip.update_one({"_id": 装备名称}, {"$set": {"标记": 标记}}, True)
    else:
        db.equip.update_one({"_id": 装备名称}, {"$unset": {"标记": 1}}, True)
    return "标记成功！"


async def sell_equipment(user_id, 装备名称: str):
    '''出售装备'''
    获得银两 = 0
    if 装备名称.isdigit():
        售卖分数 = int(装备名称)
        cons = db.equip.find({"持有人": user_id})
        for con in cons:
            装备名称 = con['_id']
            装备 = db.jianghu.find_one({"_id": user_id})["装备"]
            if 装备名称 == 装备[con["类型"]] or con.get("标记"):
                continue
            银两 = 装备价格(con)
            if (con.get("装备分数", 0) + con.get("镶嵌分数", 0)) <= 售卖分数:
                获得银两 += 银两
                db.equip.delete_one({"_id": 装备名称})
    else:
        con = db.equip.find_one({"_id": 装备名称})
        if not con:
            return "该装备不存在"
        if con["持有人"] != user_id:
            return "你没有此装备"
        装备 = db.jianghu.find_one({"_id": user_id})["装备"]
        if 装备名称 == 装备[con["类型"]]:
            return "该装备正在使用，无法出售"
        获得银两 += 装备价格(con)
        db.equip.delete_one({"_id": 装备名称})
    db.user_info.update_one({"_id": user_id}, {"$inc": {"gold": 获得银两}}, True)

    return f"出售成功，获得银两：{获得银两}"


async def rebuild_equipment(user_id, 装备一名称, 装备二名称):
    '''重铸装备'''
    if 装备一名称[-1] != 装备二名称[-1]:
        return "同类型装备才可以重铸"
    装备 = db.jianghu.find_one({"_id": user_id})["装备"]
    装备一 = db.equip.find_one({"_id": 装备一名称})
    if not 装备一:
        return "装备一不存在"
    if 装备一["持有人"] != user_id:
        return "你没有装备一"
    装备二 = db.equip.find_one({"_id": 装备二名称})
    if not 装备二:
        return "装备二不存在"
    if 装备二.get("标记"):
        return f"{装备二名称}已被标记，只能作为保留属性的装备（第一槽位）进行重铸。"
    if 装备二["持有人"] != user_id:
        return "你没有装备二"
    if 装备一名称 == 装备[装备一["类型"]]:
        return "该装备一正在使用，无法重铸"
    if 装备二名称 == 装备[装备二["类型"]]:
        return "该装备二正在使用，无法重铸"
    del 装备一["_id"]
    db.equip.update_one({"_id": 装备二名称}, {"$set": 装备一})
    db.equip.delete_one({"_id": 装备一名称})
    return "装备重铸成功"


async def build_equipment(user_id, res):
    """打造装备"""
    if len(res.split()) != 3:
        return "输入错误"
    材料re = re.compile(" ([赤橙黄绿青蓝紫彩][金木水火土])")
    材料list = 材料re.findall(res)
    图纸re = re.compile(" ([武器外装饰品]{2}\d*)")
    图纸list = 图纸re.findall(res)
    if not all([材料list, 图纸list]):
        return "输入错误"
    材料名称 = 材料list[0]
    图纸名称 = 图纸list[0]

    con = db.knapsack.find_one({"_id": user_id})
    if con:
        材料 = con.get("材料", {})
        图纸 = con.get("图纸", {})
        if len(图纸名称) == 2:
            图纸名称列表 = [i for i in 图纸.keys() if 图纸名称 in i]
            if not 图纸名称列表:
                return "图纸数量不足"
            图纸名称 = sorted(图纸名称列表, key=lambda x: int(x[2:]), reverse=True)[0]
        材料数量 = 材料.get(材料名称, 0)
        图纸数量 = 图纸.get(图纸名称, 0)
    if 材料数量 < 1:
        return "材料不足"
    if 图纸数量 < 1:
        return "图纸不足"
    材料数量 -= 1
    材料[材料名称] = 材料数量
    if 材料数量 == 0:
        del 材料[材料名称]
    图纸数量 -= 1
    图纸[图纸名称] = 图纸数量
    if 图纸数量 == 0:
        del 图纸[图纸名称]
    装备 = 打造装备(材料名称, 图纸名称)
    装备["打造人"] = user_id
    装备["持有人"] = user_id
    装备["打造日期"] = datetime.now()
    db.equip.insert_one(装备)
    db.knapsack.update_one({"_id": user_id}, {"$set": {
        "材料": 材料,
        "图纸": 图纸
    }}, True)
    msg = f"消耗{图纸名称}、{材料名称}打造成功！\n装备名称：{装备['_id']}（{装备['装备分数']}）\n基础属性：{装备['基础属性']}\n"
    if 装备.get("附加属性"):
        msg += f"附加属性：{装备['附加属性']}\n"
    打造人 = db.jianghu.find_one({'_id': 装备['打造人']})
    msg += f"打造人：{打造人['名称']}\n打造时间：{装备['打造日期'].strftime('%Y-%m-%d %H:%M:%S')}"
    return msg


async def discard_equipment(user_id, res):
    """丢弃装备"""
    if len(res.split()) != 2:
        return "输入错误"
    装备_re = re.compile(r" (.{2,4}[剑杖扇灯锤甲服衫袍铠链牌坠玦环]{1})")
    装备list = 装备_re.findall(res)
    if not 装备list:
        return "输入错误"
    装备名称 = 装备list[0]
    善恶值 = db.jianghu.find_one({"_id": user_id})["善恶值"]
    装备 = db.equip.find_one({"_id": 装备名称})
    if 装备["持有人"] != user_id:
        return "你没有这件装备"
    用户装备 = db.jianghu.find_one({"_id": user_id})["装备"]
    if 装备['_id'] == 用户装备[装备["类型"]]:
        return "该装备正在使用, 无法丢弃"
    装备["持有人"] = -2
    db.equip.update_one({"_id": 装备名称}, {"$set": 装备})
    装备分数 = 装备.get("装备分数", 0) + 装备.get("镶嵌分数", 0)
    if 装备["打造人"] != user_id:
        return f"丢弃装备【{装备名称}】({装备分数})成功, 丢弃非自己打造的装备无法获得善恶值"
    discard_equipment_num = db.user_info.find_one_and_update(
            filter={"_id": user_id},
            update={"$inc": {"discard_equipment_num": 1}},
            upsert=True
        ).get("discard_equipment_num", 0)
    剩余次数 = 5 - discard_equipment_num
    if 剩余次数 <= 0:
        return f"丢弃装备【{装备名称}】({装备分数})成功, 每天只可以获得5次善恶值"
    善恶增加上限 = int(装备分数 / 1000 - abs(善恶值 / 200))
    if 善恶增加上限 < 0:
        善恶增加上限 = 0
    增加善恶值 = random.randint(0, 善恶增加上限)
    当前善恶值 = db.jianghu.find_one_and_update(
            filter={"_id": user_id},
            update={"$inc": {"善恶值": 增加善恶值}},
            upsert=True
        ).get("善恶值", 0)
    return f"丢弃装备【{装备名称}】({装备分数})成功, 善恶值+{增加善恶值}, 当前善恶值: {当前善恶值+增加善恶值}\n"\
           f"今日已获得善恶值: {discard_equipment_num+1}/5次"


async def inlay_equipment(user_id, res):
    """镶嵌装备"""
    if len(res.split()) != 3:
        return "输入错误"
    材料re = re.compile(" ([赤橙黄绿青蓝紫彩][金木水火土])")
    装备_re = re.compile(r" (.{2,4}[剑杖扇灯锤甲服衫袍铠链牌坠玦环]{1})")
    材料list = 材料re.findall(res)
    装备list = 装备_re.findall(res)
    if not all([材料list, 装备list]):
        return "输入错误"
    材料名称 = 材料list[0]
    装备名称 = 装备list[0]

    con = db.knapsack.find_one({"_id": user_id})
    善恶值 = db.jianghu.find_one({"_id": user_id})["善恶值"]
    装备 = db.equip.find_one({"_id": 装备名称})
    if 装备["持有人"] != user_id:
        return "你没有这件装备"
    if con:
        材料 = con.get("材料", {})
        材料数量 = 材料.get(材料名称, 0)
    if 材料数量 < 1:
        return "材料不足"
    材料数量 -= 1
    材料[材料名称] = 材料数量
    if 材料数量 == 0:
        del 材料[材料名称]
    db.knapsack.update_one({"_id": user_id}, {"$set": {"材料": 材料}}, True)
    装备 = 镶嵌装备(装备, 材料名称, 善恶值)
    db.equip.update_one({"_id": 装备名称}, {"$set": 装备})
    return f'镶嵌分数: {装备["镶嵌分数"]}, 镶嵌属性: {装备["镶嵌属性"]}'


async def compose(user_id, res):
    con = db.knapsack.find_one({"_id": user_id})
    if not con:
        return "物品不足"
    if res[0] == "合成材料":
        材料 = con.get("材料", {})
        材料限制等级 = 材料等级表["彩"]
        if len(res) == 2 and res[1].strip() in 材料等级表:
            材料限制等级 = 材料等级表[res[1].strip()]
        原始材料集合 = copy.deepcopy(材料)
        while True:
            材料副本 = copy.deepcopy(材料)
            for 材料名称, 材料数量 in 材料副本.items():
                材料等级 = 材料等级表[材料名称[0]]
                if 材料数量 < 3 or 材料等级 >= 材料限制等级:
                    continue
                合成结果, 获得材料 = 合成材料(材料名称)
                if 材料名称 == 获得材料:
                    材料[材料名称] -= 2
                else:
                    if 获得材料 not in 材料:
                        材料[获得材料] = 0
                    材料[获得材料] += 1
                    材料[材料名称] -= 3
                if 材料[材料名称] <= 0:
                    del 材料[材料名称]
            可继续合成数量 = [v for k, v in 材料.items() if v >= 3 and 材料等级表[k[0]] < 材料限制等级]
            if not 可继续合成数量:
                break
        db.knapsack.update_one({"_id": user_id}, {"$set": {"材料": 材料}}, True)

        最终合成结果 = {}
        for i in set(材料.keys()) & set(原始材料集合.keys()):
            if i not in 最终合成结果:
                最终合成结果[i] = 0
            最终合成结果[i] -= 原始材料集合.get(i, 0)
            最终合成结果[i] += 材料.get(i, 0)
        装备列表 = sorted(最终合成结果.items(), key=lambda x: x[1], reverse=True)
        return f"材料合成完成：{'、'.join([f'{k}{v:+}' for k, v in 装备列表 if v != 0])}"
    elif res[0] == "合成图纸":
        图纸 = con.get("图纸", {})
        原始图纸 = copy.deepcopy(图纸)
        if not 图纸:
            return "你没有图纸"
        用户图纸列表 = []
        用户输入图纸列表 = []
        过滤条件 = []
        等级限制 = []
        合成最高等级 = 0
        for r in res:
            if re.match(r"^(武器\d+|外装\d+|饰品\d+)$", r):
                用户输入图纸列表.append(r)
            if re.match(r"^(武器|外装|饰品)$", r):
                过滤条件.append(r)
            if re.match(r"^(\d+)-(\d+)$", r):
                等级限制 = list(map(int, r.split("-")))
            if re.match(r"^(\d+)$", r):
                合成最高等级 = int(r)
        if not any([过滤条件, 等级限制, 合成最高等级, 用户输入图纸列表]) and len(res) > 1:
            return "你看看你整了些啥?命令没学会就去看看江湖闯荡指南!"

        if 用户输入图纸列表 and not any([过滤条件, 等级限制, 合成最高等级]):
            过滤条件 = []
        elif not 过滤条件:
            过滤条件 = ["武器", "外装", "饰品"]

        if 合成最高等级 > 3000 or 合成最高等级 == 0:
            合成最高等级 = 3000
        最低, 最高 = 1, 合成最高等级
        if 等级限制:
            最低, 最高 = min(等级限制), max(等级限制)
        if 最高 > 1500:
            最高 = 1500
        while True:
            # 按条件过滤图纸
            用户图纸列表 = [i for i in 用户输入图纸列表 if i in 图纸]
            过滤后图纸 = list(set([i for i in 图纸.keys() if i[:2] in 过滤条件 and 最低 <= int(i[2:]) <=最高] + 用户图纸列表))
            if not 过滤后图纸:
                break
            # 排序
            过滤后图纸 = sorted(过滤后图纸, key=lambda x: int(x[2:]), reverse=True)

            # 首尾分组
            for n, i in enumerate(过滤后图纸):
                if (int(i[2:]) + int(过滤后图纸[-1][2:])) < 合成最高等级:
                    break
            可合成 = 过滤后图纸[n:]
            待合成 = []
            for i in range(len(可合成) // 2):
                首, 尾 = 可合成[i], 可合成[-(i+1)]
                if (int(首[2:]) + int(尾[2:])) <= 合成最高等级:
                    待合成.append((首, 尾))
            if not 待合成:
                break
            for x, y in 待合成:
                获得图纸 = 合成图纸(x, y)
                if not 图纸.get(获得图纸):
                    图纸[获得图纸] = 0
                图纸[获得图纸] += 1
                图纸[x] -= 1
                图纸[y] -= 1
                for n in (x, y):
                    if 图纸[n] <= 0:
                        del 图纸[n]
        最终合成结果 = {}
        for i in set(图纸.keys()) | set(原始图纸.keys()):
            if i not in 最终合成结果 :
                最终合成结果[i] = 0
            最终合成结果[i] -= 原始图纸.get(i, 0)
            最终合成结果[i] += 图纸.get(i, 0)
            结果列表 = sorted(最终合成结果.items(), key=lambda x: int(x[0][2:]), reverse=True)
        结果列表 = [f'{k}{v:+}' for k, v in 结果列表 if v != 0]
        end = " ..." if len(结果列表) > 20 else ""
        if 结果列表:
            msg = f"图纸合成完成：{'、'.join(结果列表[:20])}{end}"
            db.knapsack.update_one({"_id": user_id}, {"$set": {"图纸": 图纸}}, True)
        else:
            msg = "你输入的条件根本找不到图纸!自己打开背包检查一下去!"
        return msg
    return "输入错误"


async def ranking(user_id):
    con = db.knapsack.find_one({"_id": user_id}, projection={"_id": 0})
    if not con:
        return "你的背包啥都没有"
    user_info = UserInfo(user_id)
    data = {'物品': [], '名称': user_info.基础属性['名称']}
    for i in con:
        if not con[i]:
            continue
        if i == "材料":
            材料列表 = sorted(con[i].items(),
                          key=lambda x: 材料等级表[x[0][0]],
                          reverse=True)
            data['材料'] = 材料列表
        elif i == "图纸":
            图纸列表 = sorted(con[i].items(),
                          key=lambda x: int(x[0][2:]),
                          reverse=True)
            data['图纸'] = 图纸列表
        else:
            data['物品'].append({"名称": i, "数量": con[i]})
    pagename = "knapsack.html"
    img = await browser.template_to_image(pagename=pagename, **data)
    return MessageSegment.image(img)


async def my_gear(user_id, 内容):
    '''我的装备'''
    n = 1
    if isinstance(内容, str):
        limit = 20
        filter = {"持有人": user_id, "标记": 内容}
    else:
        limit = 10
        n = 内容
        filter = {"持有人": user_id}
    装备数量 = db.equip.count_documents(filter)
    页数 = math.ceil(装备数量 / limit)
    if n > 页数:
        return f"你只有{页数}页装备"
    skip = limit * (n - 1)
    sort = list({'装备分数': -1}.items())
    cons = db.equip.find(filter=filter, sort=sort, limit=limit, skip=skip)
    if not cons:
        return "你没有装备"
    user_info = UserInfo(user_id)
    装备data_list = []
    for con in cons:
        是否装备 = user_info.基础属性["装备"].get(con["类型"]) == con['_id']
        装备data = {
            "名称": con['_id'],
            "装备分数": con.get('装备分数', 0),
            "镶嵌分数": con.get('镶嵌分数', 0),
            "是否装备": 是否装备
        }
        if con.get('标记'):
            装备data['标记'] = f"[{con.get('标记')}]"
        装备data_list.append(装备data)
    user_info.基础属性['名称']
    data = {"持有人": user_info.基础属性['名称'], "页数": 页数, "当前页": n, "装备": 装备data_list}
    pagename = "equip.html"
    img = await browser.template_to_image(pagename=pagename, **data)
    return MessageSegment.image(img)


async def check_gear(user_id, res):
    """查看装备"""
    if not res:
        return "查看格式错误"
    gear_name = res[0]
    if gear_name.isdigit():
        if con := db.auction_house.find_one({"_id": int(gear_name)}):
            gear_name = con.get("名称", "")
    if len(gear_name) == 2:
        datas = db.equip.find({"持有人": user_id, "标记": gear_name})
    else:
        datas = db.equip.find({"_id": gear_name})
    ret_data_list = []
    for data in datas:
        打造人_info = UserInfo(data['打造人'])
        data['打造人'] = 打造人_info.基础属性['名称']
        if data['持有人'] == -1:
            data['持有人'] = "售卖中"
        elif data['持有人'] == -2:
            data['持有人'] = "埋藏"
        else:
            持有人_info = UserInfo(data['持有人'])
            data['持有人'] = 持有人_info.基础属性['名称']
        data['打造日期'] = data['打造日期'].strftime("%Y-%m-%d")
        ret_data_list.append(data)
    if not ret_data_list:
        return "查不到此装备"
    ret_data = {
        "datas": ret_data_list
    }
    pagename = "check_equip.html"
    img = await browser.template_to_image(pagename=pagename, **ret_data)
    return MessageSegment.image(img)


async def use_gear(user_id, res):
    """使用装备"""
    if not res:
        return "输入格式错误"
    gear_name = res[0]
    if len(gear_name) == 2:
        cons = db.equip.find({"持有人": user_id, "标记": gear_name})
        if not cons:
            return "找不到被标记的装备"
    else:
        con = db.equip.find_one({"_id": gear_name})
        if not con:
            return "不存在这件装备"
        if con["持有人"] != user_id:
            return "你没有这件装备"
        cons = [con]
    user_info = UserInfo(user_id)
    for con in cons:
        装备 = user_info.基础属性["装备"]
        装备.update({con['类型']: con['_id']})
    db.jianghu.update_one({'_id': user_id}, {"$set": {"装备": 装备}})
    return f"装备{gear_name}成功"


async def pk_world_boss(user_id, res):
    """世界首领"""
    世界首领名称 = ""
    if res:
        世界首领名称 = res[0]
    data = await world_boss(user_id, 世界首领名称)
    if not data:
        return
    if isinstance(data, Message) or isinstance(data, str):
        return data
    pagename = "pk.html"
    img = await browser.template_to_image(pagename=pagename, **data)
    return MessageSegment.image(img)


async def claim_rewards(user_id):
    """领取首领奖励"""
    user = db.user_info.find_one_and_update({"_id": user_id}, {"$set": {"contribution": 0}})
    contribution = 0
    if user:
        contribution = int(user.get("contribution", 0))
    if not contribution:
        return "你没有贡献值"
    获得银两 = random.randint(0, contribution//7)
    contribution -= 获得银两
    图纸分 = contribution // 3
    材料分 = contribution - 图纸分
    获得彩材料 = 材料分 // 720000
    获得紫材料 = (材料分 - 获得彩材料*720000) // 150000
    if 获得紫材料 < 0:
        获得紫材料 = 0
    获得图纸 = 图纸分 // 550000
    背包 = db.knapsack.find_one({"_id": user_id})
    图纸 = 背包.get("图纸", {})
    材料 = 背包.get("材料", {})
    msg = ""
    for _ in range(获得彩材料):
        材料属性 = random.choice("金木水火土")
        获得材料名称 = "彩" + 材料属性
        if 获得材料名称 not in 材料:
            材料[获得材料名称] = 0
        材料[获得材料名称] += 1
        msg += f", {获得材料名称}"
    for _ in range(获得紫材料):
        材料属性 = random.choice("金木水火土")
        获得材料名称 = "紫" + 材料属性
        if 获得材料名称 not in 材料:
            材料[获得材料名称] = 0
        材料[获得材料名称] += 1
        msg += f", {获得材料名称}"
    for _ in range(获得图纸):
        图纸等级 = random.randint(2000, 3000)
        图纸类型 = random.choice(["武器", "饰品", "外装"])
        获得图纸名称 = 图纸类型 + str(图纸等级)
        if 获得图纸名称 not in 图纸:
            图纸[获得图纸名称] = 0
        图纸[获得图纸名称] += 1
        msg += f", {获得图纸名称}"
    db.knapsack.update_one({"_id": user_id}, {"$set": {"图纸": 图纸, "材料": 材料}})
    db.user_info.update_one({"_id": user_id}, {"$inc": {"gold": 获得银两}})
    return f"消耗{contribution}贡献值, 获得银两{获得银两}" + msg


async def start_dungeon(user_id, res):
    """挑战秘境"""
    秘境首领 = ""
    if res:
        秘境首领 = res[0]
    data = await 挑战秘境(user_id, 秘境首领)
    if isinstance(data, str):
        return data
    pagename = "pk.html"
    img = await browser.template_to_image(pagename=pagename, **data)
    return MessageSegment.image(img)


async def view_dungeon(user_id, res):
    """查看秘境"""
    秘境名称 = ""
    if res:
        秘境名称 = res[0]
    return await 查看秘境(user_id, 秘境名称)


async def dungeon_progress(user_id):
    """秘境进度"""
    return await 秘境进度(user_id)


async def resurrection_world_boss():
    """复活世界首领"""
    start_resurrection_world_boss()


async def set_skill(user_id, res):
    """配置武学"""
    已领悟武学 = []
    武学 = [""] * 5
    武学配置 = {}
    con = db.jianghu.find_one({"_id": user_id})
    if con:
        已领悟武学 = con.get("已领悟武学", [])
        武学 = con.get("武学", 武学)
        武学配置 = con.get("武学配置", 武学配置)
    if len(res) == 1 and len(res[0]) == 2:
        skill_name = res[0]
        if skill_name not in 武学配置:
            return "格式错误，或找不到该武学配置，请发送“查看武学配置”进行查看"
        武学 = 武学配置[skill_name]
    elif len(res) == 2:
        skill_name = res[0]
        skill_index = int(res[1]) - 1
        if skill_index > 4:
            return "技能槽位不能大于5"
        if skill_name == "-":
            skill_name = ""
        elif skill_name not in 已领悟武学:
            return "你没有学会该武学"
        武学[skill_index] = skill_name
    else:
        return "格式输入错误，请发送“江湖”查看武学说明。"
    db.jianghu.update_one({"_id": user_id}, {"$set": {"武学": 武学}}, True)
    return f"配置武学{skill_name}成功！"


async def save_skill(user_id, res):
    """保存武学配置"""
    if len(res) != 1 or len(res[0]) != 2:
        return "输入格式错误，配置名称只能是两个字"
    setting_name = res[0]
    con = db.jianghu.find_one({"_id": user_id})
    武学 = [""] * 5
    武学配置 = {}
    if con:
        武学 = con.get("武学", 武学)
        武学配置 = con.get("武学配置", 武学配置)
    武学配置[setting_name] = 武学
    if len(武学配置) > 10:
        return "最多只能保存10套武学配置"
    db.jianghu.update_one({"_id": user_id}, {"$set": {"武学配置": 武学配置}}, True)
    return f"保存武学配置{setting_name}成功！"


async def view_skill(res):
    """查看武学配置"""
    if len(res) != 1:
        return "输入格式错误"
    sk = Skill()
    武学 = sk.skill.get(res[0])
    if not 武学:
        return "找不到该武学"
    return 武学["招式"].__doc__.strip()


async def view_skill_set(user_id):
    """查看武学配置"""
    con = db.jianghu.find_one({"_id": user_id})
    user_info = UserInfo(user_id)
    武学配置 = {}
    if con:
        武学配置 = con.get("武学配置", 武学配置)

    if not 武学配置:
        return "你没保存任何武学配置，发送“保存武学配置 名字”就可以保存当前武学配置了。"
    msg = f"{user_info.名称}的武学配置"
    for k, v in 武学配置.items():
        msg += f"\n\n[{k}]\n{v}"
    return msg


async def del_skill(user_id, res):
    """删除武学配置"""
    if len(res) != 1 or len(res[0]) != 2:
        return "输入格式错误，配置名称只能是两个字"
    setting_name = res[0]
    con = db.jianghu.find_one({"_id": user_id})
    武学配置 = {}
    if con:
        武学配置 = con.get("武学配置", 武学配置)
    if setting_name not in 武学配置:
        return "你没有该武学配置，请发送查看武学配置进行查看"
    del 武学配置[setting_name]
    db.jianghu.update_one({"_id": user_id}, {"$set": {"武学配置": 武学配置}}, True)
    return f"删除武学配置{setting_name}成功！"


async def forgotten_skill(user_id, res):
    """遗忘武学"""
    if len(res) != 1:
        return "输入格式错误"
    skill_name = res[0]
    con = db.jianghu.find_one({"_id": user_id})
    已领悟武学 = []
    武学 = [""] * 5
    if con:
        已领悟武学 = con.get("已领悟武学", [])
        武学 = con.get("武学", 武学)
    if skill_name not in 已领悟武学:
        return "你都没学会，忘什么忘？"
    for n, i in enumerate(武学):
        if i == skill_name:
            武学[n] = ""
    已领悟武学.remove(skill_name)
    db.jianghu.update_one({"_id": user_id}, {"$set": {"武学": 武学, "已领悟武学": 已领悟武学}}, True)
    return f"遗忘武学{skill_name}成功！"


async def comprehension_skill(user_id, res):
    """领悟武学"""
    if not res:
        return "输入格式错误"
    银两 = int(res[0])
    if 银两 <= 0:
        return "想领悟武学，多多少少的也得花一点银子吧……"
    拥有银两 = 0
    con = db.user_info.find_one({"_id": user_id})
    if con:
        拥有银两 = con.get("gold", 0)
    if 拥有银两 < 银两:
        return "你的银两不足"

    user_info = UserInfo(user_id)
    已领悟武学 = user_info.基础属性.get("已领悟武学", [])
    sl = Skill()
    全部武学 = list(sl.skill.keys())
    全部武学数量 = len(全部武学)
    已领悟武学数量 = len(已领悟武学)
    if 已领悟武学数量 == 全部武学数量:
        return "你已经学会了所有武学，不需要再领悟了！"

    # 检查领悟武学cd
    n_cd_time = 60
    app_name = "领悟武学"
    flag, cd_time = await search_record(user_id, app_name, n_cd_time)
    if not flag:
        msg = f"{cd_time} 后才可以继续领悟"
        return msg
    await search_once(user_id, app_name)

    db.user_info.update_one({"_id": user_id}, {"$inc": {"gold": -银两}}, True)
    if random.randint(1, 100) < 银两:
        武学 = random.choice(全部武学)
        if 武学 in 已领悟武学:
            return "领悟失败"
    else:
        return "领悟失败"
    已领悟武学.append(武学)
    db.jianghu.update_one({"_id": user_id}, {"$set": {"已领悟武学": 已领悟武学}}, True)
    return f"花费{银两}两银子，成功领悟武学：{武学}"


async def impart_skill(user_id, at_qq, 武学):
    """传授武学"""
    user_info = UserInfo(user_id)
    if 武学 not in user_info.基础属性.get("已领悟武学", []):
        return "你都没学会这门招式，怎么传授给别人？"
    at_info = UserInfo(at_qq)
    被传授方武学 = at_info.基础属性.get("已领悟武学", [])
    if 武学 in 被传授方武学:
        return "对方已经学会了该武学，不用花冤枉钱了。"
    拥有银两 = 0
    con = db.user_info.find_one({"_id": user_id})
    if con:
        拥有银两 = con.get("gold", 0)
    需要花费银两 = 1000
    if 拥有银两 < 需要花费银两:
        return f"传授武学需要{需要花费银两}两银子，你的银两不足"
    被传授方武学.append(武学)
    db.user_info.update_one({"_id": user_id}, {"$inc": {"gold": -需要花费银两}}, True)
    db.jianghu.update_one({"_id": at_qq}, {"$set": {"已领悟武学": 被传授方武学}}, True)
    return f"花费{需要花费银两}两银子，成功传授武学：{武学}"


async def pk_log(日期, 编号):
    战斗记录 = db.pk_log.find_one({"编号": 编号, "日期": 日期})
    if not 战斗记录:
        return "没有找到对应的战斗记录"
    data = {
        "战斗记录": 战斗记录.get("记录")
    }
    pagename = "pk_log.html"
    img = await browser.template_to_image(pagename=pagename, **data)
    return MessageSegment.image(img)


async def pk(动作, user_id, 目标):
    if 目标.isdigit():
        目标_id = int(目标)
        跨群 = False
    else:
        if 目标 == "无名":
            return "此人过于神秘, 无法进攻"
        江湖info = db.jianghu.find_one({"名称": 目标})
        if not 江湖info:
            return "找不到正确的目标"
        目标_id = 江湖info["_id"]
        跨群 = True
    if 目标_id == user_id:
        return "不可以打自己"
    消耗精力 = 0
    msg = ""
    if 动作 == "偷袭":
        消耗精力 = 1
    elif 动作 == "死斗":
        消耗精力 = 3
    if 跨群:
        if 动作 == "切磋":
            return "不能通过名称进行切磋"
        消耗精力 *= 2
    if 消耗精力:
        精力 = db.user_info.find_one({"_id": user_id}).get("energy", 0)
        if 精力 < 消耗精力:
            精力 = 0
            return f"精力不足, 你只有{精力}精力, {动作}需要{消耗精力}精力"
        msg = f"{动作}成功, 精力-{消耗精力}"
    db.user_info.update_one({"_id": user_id}, {"$inc": {"energy": -消耗精力}})
    战斗 = PK()
    data = await 战斗.main(动作, user_id, 目标_id, msg)
    if isinstance(data, str):
        return data
    pagename = "pk.html"
    img = await browser.template_to_image(pagename=pagename, **data)
    return MessageSegment.image(img)


async def give(user_id, at_qq, 物品列表):
    user_info = UserInfo(at_qq)
    if user_info.名称 == "无名":
        return "对方未改名, 无法赠送"
    材料re = re.compile(r"^([赤橙黄绿青蓝紫彩][金木水火土])$")
    图纸re = re.compile(r"^([武器外装饰品]{2}\d+)$|^(图纸(\d+-\d+){0,1})$")
    装备_re = re.compile(r"^(.{2,4}[剑杖扇灯锤甲服衫袍铠链牌坠玦环]{0,1})$")
    msg = "赠送完成"
    for 物品 in 物品列表:
        数量 = 1
        if "*" in 物品:
            物品, 数量 = 物品.split("*")
            数量 = int(数量.strip())
            if 数量 < 1:
                msg += "\n赠送失败：物品数量格式不对"
                continue
        物品 = 物品.strip()
        if 物品 in shop:
            类型 = "物品"
        elif 材料re.match(物品):
            类型 = "材料"
        elif 图纸re.match(物品):
            类型 = "图纸"
        elif 装备_re.match(物品):
            类型 = "装备"
        else:
            msg += "\n赠送失败：物品名称不对"
            continue
        if 类型 in ["材料", "图纸", "物品"]:
            con = db.knapsack.find_one({"_id": user_id})
            if not con:
                msg += f"\n赠送失败：{物品}数量不足"
                continue
            if 类型 == "物品":
                if con.get(物品, 0) < 数量:
                    msg += f"\n赠送失败：{物品}数量不足"
                    continue
                msg += f"\n{物品}*{数量}赠送成功！"
                db.knapsack.update_one({"_id": user_id}, {"$inc": {物品: -数量}}, True)
                db.knapsack.update_one({"_id": at_qq}, {"$inc": {物品: 数量}}, True)
            else:
                # 重置双方物品
                data = con.get(类型, {})
                at_con = db.knapsack.find_one({"_id": at_qq})

                if 类型 == "图纸" and "-" in 物品:
                    下限, 上限 = re.findall(r"(\d+)", 物品)
                    下限, 上限 = int(下限), int(上限)
                    if 下限 > 上限:
                        下限, 上限 = 上限, 下限
                    可赠送物品数量 = 0
                    可赠送物品 = []
                    for k, v in data.items():
                        if 下限 <= int(k[2:]) <= 上限:
                            可赠送物品数量 += v
                            可赠送物品.append(k)
                    if 可赠送物品数量 < 数量:
                        msg += f"\n赠送失败：{物品}数量不足，可赠送数量为{可赠送物品数量}"
                        continue
                    for k in 可赠送物品:
                        if 数量 <= 0:
                            break
                        if data[k] >= 数量:
                            data[k] -= 数量
                            赠送数量 = 数量
                            数量 = 0
                        else:
                            数量 -= data[k]
                            赠送数量 = data[k]
                            data[k] = 0
                        if data[k] <= 0:
                            del data[k]
                        at_data = {k: 0}
                        if at_con:
                            at_data = at_con.get(类型, {k: 0})
                        if k not in at_data:
                            at_data[k] = 0
                        at_data[k] += 赠送数量
                        msg += f"\n{k}*{赠送数量}赠送成功！"
                        db.knapsack.update_one({"_id": user_id}, {"$set": {
                            类型: data
                        }}, True)
                        db.knapsack.update_one({"_id": at_qq}, {"$set": {
                            类型: at_data
                        }}, True)
                else:
                    if data.get(物品, 0) < 数量:
                        msg += f"\n赠送失败：{物品}数量不足"
                        continue
                    data[物品] -= 数量
                    if data[物品] <= 0:
                        del data[物品]
                    if at_con:
                        at_data = at_con.get(类型, {物品: 0})
                    if not at_data.get(物品):
                        at_data[物品] = 0
                    at_data[物品] += 数量
                    db.knapsack.update_one({"_id": user_id}, {"$set": {
                        类型: data
                    }}, True)
                    db.knapsack.update_one({"_id": at_qq}, {"$set": {
                        类型: at_data
                    }}, True)
                    msg += f"\n{物品}*{数量}赠送成功！"
        else:
            if len(物品) == 2:
                datas = db.equip.find({"持有人": user_id, "标记": 物品})
            else:
                datas = db.equip.find({"_id": 物品})
            if not datas:
                msg += f"\n赠送失败：名称不对"
                continue
            for data in datas:
                if data["持有人"] != user_id:
                    msg += f"\n{data['_id']}赠送失败：你没有这件装备或是该装备正在售卖。"
                    continue
                交易时间 = data.get("交易时间")
                if 交易时间:
                    交易保护时间 = 1800 - (datetime.now() - 交易时间).seconds
                    if 交易保护时间 > 0:
                        msg += f"\n{data['_id']}正在交易保护期间，无法赠送。剩余时间：{交易保护时间}秒"
                        continue
                装备 = db.jianghu.find_one({"_id": user_id})["装备"]
                if data['_id'] == 装备[data["类型"]]:
                    msg += f"\n赠送失败：{data['_id']}正在使用，无法赠送"
                    continue
                msg += f"\n{data['_id']}赠送成功！"
                db.equip.update_one({"_id": data["_id"]}, {"$set": {"持有人": at_qq, "交易时间": datetime.now()}}, True)
    return msg


async def healing(user_id, target_id):
    user = UserInfo(target_id)
    if not user.基础属性["重伤状态"]:
        return "未重伤，不需要疗伤"
    gold = 0
    con = db.user_info.find_one({"_id": user_id})
    if con:
        gold = con.get("gold", 0)
    if gold < 100:
        return "疗伤需要一百两银子，你的银两不够！"
    db.user_info.update_one({"_id": user_id}, {"$inc": {"gold": -100}}, True)
    db.jianghu.update_one({"_id": target_id}, {
        "$set": {
            "重伤状态": False,
            "当前气血": user.当前状态["气血上限"],
            "当前内力": user.当前状态["内力上限"]
        }
    }, True)
    return "花费一百两银子，疗伤成功！"


async def gad_guys_ranking(bot: Bot, user_id):
    '''恶人排行'''
    logger.debug(f"恶人排行 | <e>{user_id}</e>")
    filter = {'善恶值': {"$ne": None}}
    sort = list({'善恶值': 1}.items())
    limit = 10
    msg = "恶人排行\n"

    result = db.jianghu.find(filter=filter, sort=sort, limit=limit)
    for n, i in enumerate(result):
        重伤 = "x" if i.get("重伤状态") else ""
        msg += f"{n+1} {重伤}{i.get('名称')} {i.get('善恶值', 0)}\n"
    return msg


async def good_guys_ranking(bot: Bot, user_id):
    '''善人排行'''
    logger.debug(f"善人排行 | <e>{user_id}</e>")
    filter = {}
    sort = list({'善恶值': -1}.items())
    limit = 10
    msg = "善人排行\n"
    result = db.jianghu.find(filter=filter, sort=sort, limit=limit)
    for n, i in enumerate(result):
        重伤 = "x" if i.get("重伤状态") else ""
        msg += f"{n+1} {重伤}{i['名称']} {i['善恶值']}\n"
    return msg


async def gear_ranking(bot: Bot, user_id):
    '''神兵排行'''
    logger.debug(f"神兵排行 | <e>{user_id}</e>")
    project = {
        "总装分": {"$sum": ['$装备分数', '$镶嵌分数']},
        "持有人": 1
    }
    sort = {'总装分': -1}
    limit = 10
    msg = "神兵排行\n"

    result = db.equip.aggregate([
        {"$project": project},
        {"$sort": sort},
        {"$limit": limit}
    ])
    for n, i in enumerate(result):
        user_info = UserInfo(i['持有人'])
        重伤 = "x" if user_info.基础属性.get("重伤状态") else ""
        名称 = user_info.基础属性["名称"]
        msg += f"{n+1} {i['_id']} {i['总装分']} {重伤}{名称}\n"
    return msg


async def gold_ranking(bot: Bot, user_id):
    '''银两排行'''

    logger.debug(f"银两排行 | <e>{user_id}</e>")
    filter = {}
    sort = list({'gold': -1}.items())
    limit = 10
    msg = "银两排行\n"

    result = db.user_info.find(filter=filter, sort=sort, limit=limit)
    for n, i in enumerate(result):
        user_info = UserInfo(i['_id'])
        重伤 = "x" if user_info.基础属性.get("重伤状态") else ""
        名称 = user_info.基础属性["名称"]
        msg += f"{n+1} {重伤}{名称} {i['gold']}\n"

    ret = db.user_info.aggregate([{
        "$sort": {
            "gold": -1
        }
    }, {
        "$group": {
            "_id": None,
            "all": {
                "$push": "$_id"
            }
        }
    }, {
        "$project": {
            "_id": 0,
            "index": {
                "$indexOfArray": ["$all", user_id]
            }
        }
    }])
    if not ret:
        msg += "\n找不到你的记录!"
        return msg
    index = list(ret)[0]["index"] + 1
    msg += f"\n你的排名:{index}"
    return msg

