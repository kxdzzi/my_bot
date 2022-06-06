import os
import random
import time
from datetime import datetime
from typing import Literal, Optional

from httpx import AsyncClient
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment
from nonebot.adapters.onebot.v11.event import (GroupIncreaseNoticeEvent,
                                               GroupMessageEvent)
from nonebot.plugin import get_loaded_plugins
from src.utils.black_list import add_black_list, check_black_list
from src.utils.chat import chat
from src.utils.config import config
from src.utils.content_check import content_check
from src.utils.db import db
from src.utils.log import logger

data_dir = os.path.realpath(__file__ + "/../../../../data/")


async def get_main_server(server: str) -> Optional[str]:
    '''获取主服务器'''
    params = {"name": server}
    url = "https://www.jx3api.com/app/server"
    async with AsyncClient() as client:
        try:
            req = await client.get(url=url, params=params)
            req_json = req.json()
            if req_json['code'] == 200:
                return req_json['data']['server']
            return None
        except Exception:
            return None


async def bind_server(group_id: int, server: str):
    '''绑定服务器'''
    db.group_conf.update_one({'_id': group_id}, {'$set': {
        "server": server
    }}, True)


async def set_activity(group_id: int, activity: int):
    '''设置活跃值'''
    db.group_conf.update_one({'_id': group_id},
                             {'$set': {
                                 "robot_active": activity
                             }}, True)


async def set_status(group_id: int, status: bool):
    '''设置机器人开关'''
    db.group_conf.update_one({'_id': group_id},
                             {'$set': {
                                 "group_switch": status
                             }}, True)


async def get_meau_data(group_id: int) -> dict:
    '''获取菜单数据'''
    req_data = {}
    _con = db.group_conf.find_one({'_id': group_id})
    if _con:
        req_data['group'] = _con
    else:
        req_data['group'] = {}
    _con = db.plugins_info.find_one({'_id': group_id})
    if _con:
        req_data['plugin'] = []
        for v in _con.values():
            if isinstance(v, dict):
                req_data['plugin'].append(v)
    else:
        req_data['plugin'] = []
    return req_data


async def get_notice_status(
    group_id: int, notice_type: Literal["welcome_status", "goodnight_status",
                                        "someoneleft_status"]
) -> bool:
    '''获取通知状态'''

    _con = db.group_conf.find_one({'_id': group_id})
    if _con:
        return _con.get(notice_type, False)


async def message_decoder(bot: Bot, event: GroupIncreaseNoticeEvent,
                          notice_type: Literal["离群通知", "进群通知"]) -> Message:
    '''设置通知消息'''
    try:
        group_id = event.group_id
        user_id = event.user_id

        group_info = await bot.get_group_info(group_id=group_id)
        group_name = group_info["group_name"]
        member_count = group_info["member_count"] + 1
        max_member_count = group_info["max_member_count"]
        group_level = group_info["group_level"]

        content_data = {
            "群号": group_id,
            "群名": group_name,
            "群人数": member_count,
            "最大人数": max_member_count,
            "群等级": group_level,
        }
        if notice_type == "进群通知":
            user_info = await bot.get_group_member_info(group_id=group_id,
                                                        user_id=user_id)
            join_time = datetime.fromtimestamp(
                user_info["join_time"]).strftime("%Y-%m-%d %H:%M:%S")
            level = user_info["level"]
            nickname = user_info["nickname"]
            sex = "女" if user_info["sex"] == "female" else "男"
            age = user_info["age"]
            content_data.update({
                "QQ": user_id,
                "进群时间": join_time,
                "用户名": nickname,
                "等级": level,
                "性别": sex,
                "年龄": age,
                "@QQ": "@QQ"
            })

        msg = ""
        _con = db.group_conf.find_one({'_id': group_id})
        if _con:
            content = _con.get(notice_type, "")
        content = content.replace("&#91;", "{")
        content = content.replace("&#93;", "}")
        content = content.format_map(content_data)
        msg = None
        if "@QQ" in content:
            for i in content.split("@QQ"):
                if not i:
                    continue
                msg += i + MessageSegment.at(user_id)
            msg = msg[:-1]
            if content.startswith("@QQ"):
                msg = MessageSegment.at(user_id) + msg
            if content.endswith("@QQ"):
                msg = msg + MessageSegment.at(user_id)
        else:
            msg = content
        return msg
    except:
        return f"{notice_type}通知内容写的不太对，管理员们重新设置一下吧！"


async def handle_data_notice(group_id: int, notice_type: Literal["离群通知",
                                                                 "进群通知"],
                             message: str):
    '''处理通知内容'''
    content = message.split(" ", 1)[-1]
    result, _ = content_check(content)
    if not result:
        return False
    db.group_conf.update_one({"_id": group_id},
                             {"$set": {
                                 notice_type: content
                             }}, True)
    return True


async def check_add_bot_to_group(bot: Bot, user_id: int,
                                 group_id: int) -> tuple:
    '''检查加群条件'''
    bot_id = int(bot.self_id)
    bot_info = db.bot_info.find_one({"_id": bot_id})
    if bot_info.get("master") == user_id:
        return True, None
    result, _ = check_black_list(user_id, "QQ")
    if result:
        return False, f"{user_id}太烦人被我拉黑了, 下次注意点!"
    result, _ = check_black_list(group_id, "群号")
    if result:
        return False, "群已被拉黑"
    group_conf = db.group_conf.find_one_and_update(
        filter={"_id": group_id},
        update={"$inc": {
            "add_group_num": 1
        }},
        upsert=True)
    if group_conf:
        add_group_num = group_conf.get("add_group_num", 0)
        if add_group_num >= 5:
            add_black_list(user_id, "QQ", 2592000, f"加群{group_id}单日超过5次")
            return False, "单日拉机器人超过5次, 用户拉黑30天"
    manage_group = config.bot_conf.get("manage_group", [])
    access_group_num = bot_info.get("access_group_num", 50)
    bot_group_num = db.group_conf.count_documents({"bot_id": bot_id})
    # 若群id不在管理群列表, 则需要进行加群条件过滤
    if group_id not in manage_group:
        if not bot_info.get("work_stat"):
            return False, "老子放假了，你拉别的机器人去！"
        elif bot_group_num >= access_group_num:
            return False, f"老子最多只能加{access_group_num}个群，现在都加了{bot_group_num}个群，机器人不用休息的吗？你赶紧拉别的机器人去，别拉我了！"
    return True, None


async def add_bot_to_group(group_id: int, bot_id: int) -> None:
    '''加群动作'''
    db.group_conf.update_one(
        {'_id': group_id},
        {'$set': {
            "group_switch": True,
            "robot_active": 0,
            "bot_id": bot_id
        }}, True)
    # 注册所有插件
    plugins = list(get_loaded_plugins())
    for one_plugin in plugins:
        export = one_plugin.export
        plugin_name = export.get("plugin_name")
        if plugin_name is None:
            continue
        db.plugins_info.update_one({'_id': group_id}, {
            '$set': {
                one_plugin.name: {
                    "module_name": one_plugin.name,
                    "plugin_name": plugin_name,
                    "command": export.get("plugin_command"),
                    "usage": export.get("plugin_usage"),
                    "status": export.get("default_status")
                },
            }
        }, True)


async def del_bot_to_group(bot: Bot, group_id, msg=None, exit_group=True):
    '''退群动作'''
    try:
        bot_id = int(bot.self_id)
        if exit_group:
            if msg:
                # 退群前发送消息
                await bot.send_group_msg(group_id=group_id, message=msg)
                time.sleep(0.5)
            # 退群
            await bot.set_group_leave(group_id=group_id, is_dismiss=False)
        # 删除数据库中的机器人记录
        db.group_conf.update_one({
            '_id': group_id,
            'bot_id': bot_id
        }, {'$set': {
            "bot_id": 0
        }})
        ret_msg = f"成功退群 {group_id}"
    except:
        ret_msg = f"退群 {group_id} 失败"
    return ret_msg


async def tianjianhongfu(bot: Bot, group_id, user_id, nickname):
    # 天降鸿福事件
    # 个人获得奖励概率递减
    con = db.user_info.find_one({"_id": user_id})
    user_lucky = 1.0
    if con:
        user_lucky = con.get("user_lucky", 1.0)
    if user_lucky >= random.uniform(0, 50):
        db.user_info.update_one({"_id": user_id},
                                {"$set": {
                                    "user_lucky": user_lucky * 0.7
                                }}, True)
        con = db.group_conf.find_one({"_id": group_id})
        lucky = 0
        if con:
            lucky = con.get("lucky", 0)
        add_gold = random.randint(1, (lucky + 1) * 30)
        gold = 0
        _con = db.user_info.find_one({'_id': user_id})
        if _con:
            gold = _con.get("gold", 0)
        gold += add_gold
        db.user_info.update_one({"_id": user_id}, {"$set": {
            "gold": gold
        }}, True)
        msg = f"{nickname}天降鸿福，银两 +{add_gold}"
        logger.debug(
            f"<y>群{group_id}</y> | <g>{nickname}</g> | 天降鸿福 +{add_gold}")
        await bot.send_group_msg(group_id=group_id, message=msg)
        return True
    return False


async def play_picture(bot: Bot, event: GroupMessageEvent, group_id):
    _con = db.group_conf.find_one({'_id': group_id})
    if _con:
        robot_active = _con.get("robot_active", 0)
    else:
        robot_active = 0
    if robot_active >= random.randint(0, 500):
        if random.choice((True, False)):
            content = ""
            for i in event.message:
                if i.type == "text":
                    content += i.data.get("text", "")
            if not content:
                return
            msg = await chat(content)
            logger.debug(f"<y>群({group_id})</y> | 搭话 | {msg}")
        else:
            memes = db.memes.aggregate([{"$sample": {"size": 1}}])
            for meme in memes:
                url = meme.get("url")
                async with AsyncClient() as client:
                    req = await client.get(url=url)
                    msg = MessageSegment.image(req.content)
        await bot.send_group_msg(group_id=group_id, message=msg)
