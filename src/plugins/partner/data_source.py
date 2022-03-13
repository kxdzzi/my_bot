import random
from datetime import datetime

from httpx import AsyncClient
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from src.utils.cooldown_time import search_record, search_once
from src.utils.db import db
import random

client = AsyncClient()
'''异步请求客户端'''


async def set_find_partner_cooldown_time(group_id: int, cooldown_time: int):
    if cooldown_time < 60:
        return "分配情缘冷却时间必须高于 60 秒"
    db.group_cd_conf.update_one({"_id": group_id},
                                {"$set": {
                                    "分配情缘": cooldown_time
                                }}, True)
    msg = "修改成功！"
    return msg


async def set_find_partner_do_not_disturb(group_id: int,
                                          do_not_disturb_switch: bool):
    db.group_conf.update_one(
        {"_id": group_id},
        {"$set": {
            "partner_disturb_switch": do_not_disturb_switch
        }}, True)
    msg = "修改成功！"
    return msg


async def get_find_partner_to_group(user_id: int, group_id: int, end_str: str,
                                    group_member_list: list) -> Message:
    '''
    :说明
        分配情缘

    :参数
        * user_id：用户QQ
        * group_id：QQ群号

    :返回
        * Message：机器人返回消息
    '''
    # 请求方是否有情缘
    _con = db.user_info.find_one({'_id': user_id})
    if not _con:
        _con = {}
    if end_str == "情缘":
        if _con.get("partner"):
            msg = "有情缘了就安分点吧！"
            return msg
    gold = _con.get("gold", 0)
    if gold < 1:
        msg = f"你连一两银子都没有，这么穷怎么配跟{end_str}一起玩？"
        return msg
    # 随机到的人是否有情缘
    usr = random.choice(group_member_list)
    _con = db.user_info.find_one({'_id': usr["user_id"]})
    if _con:
        if _con.get("partner") or usr["user_id"] == user_id:
            msg = "你就认了吧，我也帮不了你了。"
            return msg

    app_name = "分配情缘"
    group_cd = db.group_cd_conf.find_one({'_id': group_id})
    # 查看冷却时间
    n_cd_time = 300
    if group_cd:
        n_cd_time = group_cd.get("分配情缘", 300)
    flag, cd_time = await search_record(user_id, app_name, n_cd_time)
    if not flag:
        msg = f"[分配{end_str}] 冷却 > [{cd_time}]"
        return msg
    # 记录一次查询
    await search_once(user_id, app_name)
    db.user_info.update_one({"_id": user_id}, {"$inc": {"gold": -1}}, True)
    group_cf = db.group_conf.find_one({'_id': group_id})
    msg = MessageSegment.at(user_id)
    msg += f"组织给你分配的{end_str}是"
    if group_cf and group_cf.get("partner_disturb_switch"):
        msg += f" {usr['nickname']}({usr['user_id']}) "
    else:
        msg += MessageSegment.at(usr["user_id"])
    if end_str == "情缘":
        msg += "\n"
        msg_list = [
            "谁先说话谁是攻。",
            "好好想想自己什么条件再考虑接不接受。",
            "机会给你了，自己把握啊。",
            "总得有人主动才能有故事。",
            "关于情缘这事，别人可使不上劲儿。",
            "我只能帮你到这了。",
            "至于谁是攻，你们商量着来。",
            "主动点才能有情缘……甚至有孩子。",
            "赶紧去私聊啊，别愣着！",
            "胆大心细脸皮厚，这需要我教你吗？",
            "我觉得你们两个真挺配。",
            "问问群友们，这俩人配不配？",
            "哟，我觉得你们两个挺合适！",
            "一动不动是王八，谁先说话谁老大！",
            "终于不用天天刷世界求情缘了吗？",
            "缘分来之不易，差不多就得了。",
            "不凑合，真的不凑合，你们两个挺好的。",
            "知道怎么绑情缘吗？发送“求情缘@对方QQ”就可以了！",
            "我分配的上一对情缘现在已经领证了，你们呢？",
            "有了情缘也不能忘了我。",
            "啥时候奔现记得给我包个红包。",
            "讨论一下以后谁负责洗碗，谁负责拖地吧。",
            "这是机会啊，是机会啊！",
            "加油，你可以的。",
            "不要害羞，害羞成不了气候。",
            "拿出你刷世界求情缘的脸皮，该成不就成了嘛！",
            "有了情缘以后就该老实点了吧。",
            "终于找到情缘管管你了。",
            "我早就觉得你们两个是一对了。",
            "上线炸橙子去吧！",
            "你们交换礼物的时候别忘了给我也寄一份。",
            "这么好的情缘，要我的话直接就订机票了。",
            "以后对人家好一点啊。",
            "你们尽管情缘，死了情缘算我的。",
            "天造地设的一对！完美完美！",
            "令人羡慕的爱情……要开始了吗？",
            "你们会成为千古佳话的！",
            "好耶，万年寡王终于要脱单了吗？",
            "你不主动谁都帮不了你",
        ]
        msg += random.choice(msg_list)
    return msg


async def partner_request_to_group(user_id: int, user_name: str,
                                   at_qq: int) -> Message:
    app_name = "求情缘"
    cd_time = 180
    flag, cd_time = await search_record(user_id, app_name, cd_time)
    if not flag:
        msg = f"[{app_name}] 冷却 > [{cd_time}]"
        return msg

    # 请求方是否有情缘
    _con = db.user_info.find_one({'_id': user_id})
    if _con:
        if _con.get("partner"):
            msg = MessageSegment.at(user_id) + "你都有情缘了还要求情缘，你想干什？"
            return msg
    # 被请求方是否有情缘
    _con = db.user_info.find_one({'_id': at_qq})
    if not _con:
        _con = {}
    if _con.get("partner"):
        msg = MessageSegment.at(user_id) + "对方已经有情缘了，算了算了。"
        return msg
    # 是否重复申请
    partner_request_list = _con.get("partner_request", [])
    for partner_request in partner_request_list:
        if partner_request["qq"] == user_id:
            msg = "你已经在对方的鱼塘里了。"
            return msg
    # 加入鱼塘
    partner_request_list.append({
        "date_time": datetime.now(),
        "qq": user_id,
        "name": user_name
    })
    db.user_info.update_one(
        {'_id': at_qq}, {'$set': {
            "partner_request": partner_request_list
        }}, True)
    await search_once(user_id, app_name)
    msg = MessageSegment.at(at_qq)
    msg += "快来快来，有人向你求情缘了\n如果接受的话就发送“接受情缘" + MessageSegment.at(user_id) + "”\n"
    msg += "发送“情缘申请列表”可以查看谁向你求过情缘。"
    return msg


async def partner_agreed_to_group(user_id, user_name, at_qq):
    _con = db.user_info.find_one({'_id': user_id})
    at_name = None
    if _con:
        # 是否存在申请
        partner_request_list = _con.get("partner_request", [])
        for partner_request in partner_request_list:
            if partner_request["qq"] == at_qq:
                at_name = partner_request["name"]
    if not at_name:
        msg = "对方不在你的“情缘申请列表”中"
        return msg
    date_time = datetime.now()
    db.user_info.update_one({'_id': at_qq}, {
        '$set': {
            "partner": {
                "qq": user_id,
                "date_time": date_time,
                "name": user_name
            },
            "partner_request": []
        }
    }, True)
    db.user_info.update_one({'_id': user_id}, {
        '$set': {
            "partner": {
                "qq": at_qq,
                "date_time": date_time,
                "name": at_name
            },
            "partner_request": []
        }
    }, True)
    msg = f"恭喜【{at_name}】与【{user_name}】正式结为情缘！\n江湖风雨路，愿祝两相好。"
    return msg


async def get_partner_request_list(user_id: int, title: str) -> Message:
    # 请求方是否有情缘
    _con = db.user_info.find_one({'_id': user_id})
    if not _con or not _con.get("partner_request"):
        msg = MessageSegment.at(user_id) + "并没有人向你求情缘。"
        return msg
    msg = title + "\n\n"
    for partner in _con.get("partner_request"):
        msg += f"{partner['name']} {partner['date_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
    return msg


async def get_my_partner(user_id: int, user_name: str):
    _con = db.user_info.find_one({'_id': user_id})
    partner = None
    if _con:
        partner = _con.get("partner")
    if not partner:
        msg = MessageSegment.at(user_id) + "你还没有情缘。"
        return msg
    msg = f"{user_name}的情缘\n"
    qq_head = await _get_qq_img(partner['qq'])
    msg_head = MessageSegment.image(qq_head)
    msg += msg_head
    msg += f"{partner['name']}({partner['qq']})\n"
    msg += f"{partner['date_time'].strftime('%Y-%m-%d %H:%M:%S')} 结为情缘"
    return msg


async def parted_to_group(user_id: int):
    _con = db.user_info.find_one({'_id': user_id})
    partner = None
    if _con:
        partner = _con.get("partner")
    if not partner:
        msg = MessageSegment.at(user_id) + "你还没有情缘。"
        return msg
    db.user_info.update_one({'_id': user_id}, {'$set': {"partner": {}}}, True)
    db.user_info.update_one({'_id': partner['qq']},
                            {'$set': {
                                "partner": {},
                            }}, True)
    msg = MessageSegment.at(user_id) + "与" + MessageSegment.at(partner['qq'])
    msg += "分道扬镳。\n江湖路远，各自珍重。"
    return msg


async def clear_partner_request(user_id: int):
    db.user_info.update_one({'_id': user_id},
                            {'$set': {
                                "partner_request": []
                            }}, True)
    msg = "已经清空！"
    return msg


async def _get_qq_img(user_id: int) -> bytes:
    '''
    :说明
        获取QQ头像

    :参数
        * user_id：用户QQ

    :返回
        * bytes：头像数据
    '''
    num = random.randrange(1, 4)
    url = f'http://q{num}.qlogo.cn/g'
    params = {'b': 'qq', 'nk': user_id, 's': 100}
    resp = await client.get(url, params=params)
    return resp.content
