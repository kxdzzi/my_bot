import math
import re
from datetime import datetime, timedelta
from enum import Enum
from copy import deepcopy

from nonebot import export, on_regex
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebot.adapters.onebot.v11.permission import GROUP
from src.utils.browser import browser
from src.utils.content_check import content_check
from src.utils.db import db
from src.utils.jx3_search import (JX3PROFESSION, JX3PROFESSION_ROLE,
                                  jx3_searcher)

Export = export()
Export.plugin_name = "剑三开团"
Export.plugin_command = "开团"
Export.plugin_usage = "相当于是线下招募了"
Export.default_status = True

conf_list = {
    "人数": "人数",
    "输出": "输出",
    "治疗": "治疗",
    "坦克": "坦克",
    "老板": "老板",
    "D": "输出",
    "H": "治疗",
    "T": "坦克",
    "B": "老板"
}


class REGEX(Enum):
    '''正则枚举'''
    角色管理 = r"^(角色管理|绑定角色)( -{0,1}[!！]{0,1}[\u4e00-\u9fa5]{2,8}){0,3}$"
    开团 = r"^开团 .+$"
    团队信息 = r"^(团队信息|查看团队)( *\d+){0,1}"
    调整团队 = r"^(调整团队|团队管理)( *\d+){0,1} .+$"
    搜索团队 = r"^搜索团队\d*( .+)*$"
    报名 = r"^报名 ([\u4e00-\u9fa5]{2,8} ){0,1}\d+$"
    解散团队 = r"^解散团队 \d+$"
    确认解散 = r"^确认解散 \d+$"
    转让团队 = r"^转让团队 [1-5]{2}$"
    确认转让 = r"^确认转让 \d+$"
    退出团队 = r"^退出团队 ([\u4e00-\u9fa5]{2,8} ){0,1}\d+$"


user_manage = on_regex(pattern=REGEX.角色管理.value,
                       permission=GROUP,
                       priority=5,
                       block=True)
create_team = on_regex(pattern=REGEX.开团.value,
                       permission=GROUP,
                       priority=5,
                       block=True)
search_team = on_regex(pattern=REGEX.搜索团队.value,
                       permission=GROUP,
                       priority=5,
                       block=True)
register = on_regex(pattern=REGEX.报名.value,
                    permission=GROUP,
                    priority=5,
                    block=True)
view_team = on_regex(pattern=REGEX.团队信息.value,
                     permission=GROUP,
                     priority=5,
                     block=True)
set_team = on_regex(pattern=REGEX.调整团队.value,
                    permission=GROUP,
                    priority=5,
                    block=True)
disband_team = on_regex(pattern=REGEX.解散团队.value,
                        permission=GROUP,
                        priority=5,
                        block=True)
confirm_disband_team = on_regex(pattern=REGEX.确认解散.value,
                                permission=GROUP,
                                priority=5,
                                block=True)

transfer_team = on_regex(pattern=REGEX.转让团队.value,
                         permission=GROUP,
                         priority=5,
                         block=True)
confirm_transfer_team = on_regex(pattern=REGEX.确认转让.value,
                                 permission=GROUP,
                                 priority=5,
                                 block=True)
exit_team = on_regex(pattern=REGEX.退出团队.value,
                     permission=GROUP,
                     priority=5,
                     block=True)


@exit_team.handle()
async def _(event: GroupMessageEvent):
    """退出团队"""
    user_id = int(event.user_id)
    user_info = db.user_info.find_one({"_id": user_id})
    default_user = user_info["default_user"]
    if not default_user:
        await exit_team.finish(
            "你还没有绑定过角色，哪来的团队？请发送以下命令进行绑定:\n角色管理 角色名称 心法 服务器(选填)")
    text = event.get_plaintext()
    text_list = text.split()
    if len(text_list) == 3:
        user_name = text_list[1]
        team_id = int(text_list[2])
    else:
        user_name = default_user
        team_id = int(text_list[1])
    if team_id not in user_info["teams"][user_name]:
        await exit_team.finish("你没有加入过该团队")
    team_info = db.j3_teams.find_one({"_id": team_id})
    if team_info["user_id"] == user_id and team_info[
            "team_leader_name"] == user_name:
        await exit_team.finish("团长不能退团，如果要解散团队请发送“调整团队 !解散”")
    flag = False
    team_members = team_info["team_members"]
    for x, members in enumerate(team_members):
        for y, member in enumerate(members):
            if member.get("user_id") == user_id and member.get(
                    "user_name") == user_name:
                team_members[x][y] = {}
                break
        if flag:
            break
    db.j3_teams.update_one({"_id": team_id},
                           {"$set": {
                               "team_members": team_members
                           }})
    del_user_team(user_id, user_name, team_id)
    await exit_team.finish("退团成功")


def disband(user_id, team_id):
    "解散"
    team_info = db.j3_teams.find_one({"_id": team_id})
    if not team_info:
        return False, "团队不存在，请发送“团队信息”进行查看"
    user_info = db.user_info.find_one({"_id": user_id})
    team_leader_name = team_info.get("team_leader_name")
    if team_info.get(
            "user_id"
    ) != user_id or team_leader_name not in user_info["teams"]:
        return False, "你不是团长，不能调整团队"
    db.j3_teams.update_one({"_id": team_id}, {"$set": {"is_disband": True}})
    return True, f"解散团队行为不可逆，确定解散请发送“确认解散 {team_id}”"


def transfer(user_id, team_id, index_str):
    """转让"""
    team_info = db.j3_teams.find_one({"_id": team_id})
    team_members = team_info["team_members"]
    res, index_x, index_y = index_in_list(index_str, team_members)
    if not res:
        return False, "位置不存在"
    user = team_members[index_x][index_y]
    if not user:
        return False, "该位置上没有人"
    transfer_user_id = user["user_id"]
    transfer_user_name = user["user_name"]
    if transfer_user_id == user_id:
        return False, "不可以转让给自己"
    db.j3_teams.update_one({"_id": team_id},
                           {"$set": {
                               "transfer_user_id": transfer_user_id
                           }})
    return True, f"是否要将团队转让给[{transfer_user_name}]？" \
                 f"确定转让请发送“确认转让 {transfer_user_id}”"


@disband_team.handle()
async def _(event: GroupMessageEvent):
    """解散团队"""
    user_id = int(event.user_id)
    text = event.get_plaintext()
    team_id = re.findall(r" (\d+)", text)
    if not team_id:
        await disband_team.finish("正确格式为：“解散团队 团队序号”")
    _, msg = disband(user_id, int(team_id[0]))
    await disband_team.finish(msg)


@confirm_disband_team.handle()
async def _(event: GroupMessageEvent):
    """确认解散"""
    user_id = int(event.user_id)
    text = event.get_plaintext()
    text_list = text.split()
    team_id = int(text_list[1])
    team_info = db.j3_teams.find_one({"_id": team_id})
    if not team_info:
        await disband_team.finish("找不到该团队")
    if team_info.get("user_id") != user_id:
        await disband_team.finish("这个团队的团长不是你！")
    if not team_info.get("is_disband"):
        await disband_team.finish("如果想要解散团队请先发送“调整团队 !解散”")
    for members in team_info["team_members"]:
        for member in members:
            if member:
                del_user_team(member["user_id"], member["user_name"], team_id)
    db.j3_teams.delete_one({"_id": team_id})
    await disband_team.finish("成功解散团队")


@transfer_team.handle()
async def _(event: GroupMessageEvent):
    user_id = int(event.user_id)
    text = event.get_plaintext()
    content = re.findall(r" (\d+)", text)
    if len(content) == 2:
        await disband_team.finish("正确格式为：“转让团队 团队序号 接收人坐标”")
    team_id, index_str = content
    _, msg = transfer(user_id, int(team_id), index_str)
    await disband_team.finish(msg)


@confirm_transfer_team.handle()
async def _(event: GroupMessageEvent):
    user_id = int(event.user_id)
    text = event.get_plaintext()
    text_list = text.split()
    transfer_id = int(text_list[1])
    team_info = db.j3_teams.find_one({"user_id": user_id})
    if not team_info:
        await transfer_team.finish("你没有创建过任何团队")
    if team_info["transfer_user_id"] != transfer_id:
        await transfer_team.finish("待转让人的QQ有误，请重新输入")
    flag = False
    for members in team_info["team_members"]:
        for member in members:
            if member and member["user_id"] == transfer_id:
                transfer_name = member["user_name"]
                flag = True
    if not flag:
        await transfer_team.finish("待转让人不在团队里了，换个人吧")
    db.j3_teams.update_one(
        {"_id": team_info["_id"]},
        {"$set": {
            "user_id": transfer_id,
            "team_leader_name": transfer_name
        }})
    await transfer_team.finish("团队转让成功")


@user_manage.handle()
async def _(event: GroupMessageEvent):
    # 角色名称 心法 服务器(选填)
    user_id = int(event.user_id)
    text = event.get_plaintext()
    user_info = db.user_info.find_one({"_id": user_id})
    if text == "角色管理":
        # 返回当前所有角色
        if not user_info.get("user_data"):
            await user_manage.finish(
                "你还没有绑定过任何角色, 请发送以下命令进行绑定:\n角色管理 角色名称 心法 服务器(选填)")
        msg = "\n".join([
            f"{'[默认] ' if k == user_info['default_user']  else ''}{k} {v['profession']} {v['server']}"
            for k, v in user_info.get("user_data").items()
        ])
        await user_manage.finish(msg)
    del_user = re.findall(r" -([\u4e00-\u9fa5]{2,8})", text)
    if del_user:
        for user in del_user:
            if user not in user_info.get("user_data", {}):
                await user_manage.finish(f"{user}不存在，无法删除")
            # 团队中的角色无法删除
            if user_info.get("teams").get(user):
                continue
            del user_info.get("user_data")[user]
            del user_info.get("teams")[user]
            db.user_info.update_one({"_id": user_id}, {"$set": user_info})
        await user_manage.finish("删除角色成功")

    default_user = re.findall(r" [！!]([\u4e00-\u9fa5]{2,8})", text)
    if default_user:
        default_user_name = default_user[-1]
        if default_user_name not in user_info.get("user_data", {}):
            await user_manage.finish(f"{default_user_name}不存在，无法设为默认角色")
        db.user_info.update_one({"_id": user_id},
                                {"$set": {
                                    "default_user": default_user_name
                                }})
        await user_manage.finish(f"默认角色变更为: {default_user_name}")
    # 添加或修改角色
    text_list = text.split()
    text_len = len(text_list)
    if text_len < 3:
        await user_manage.finish("正确的命令格式：“角色管理 角色名称 心法 服务器(选填)”")
    user_name = text_list[1]
    if not content_check(user_name)[0]:
        await user_manage.finish("这个名字能过审?我不信！你快改一下吧")
    profession = JX3PROFESSION.get_profession(text_list[2])
    if not profession:
        await user_manage.finish("找不到你写的心法，换个写法再来一次吧")

    if not user_info.get("user_data"):
        user_info["user_data"] = {}
        user_info["teams"] = {}
        user_info["default_user"] = user_name
    if user_name not in user_info["user_data"]:
        user_info["user_data"][user_name] = {}
        user_info["teams"][user_name] = []
    if text_len > 3:
        server = await jx3_searcher.get_server(text_list[3])
        if not server:
            await user_manage.finish("你的服务器写错了吧，我只认全称！黑话我听不懂！")
    else:
        group_id = int(event.group_id)
        server = db.group_conf.find_one({"_id": group_id}).get("server")
        if not server:
            await user_manage.finish("本群未绑定服务器, 请自己写上服务器全称")

    user_info["user_data"][user_name] = {
        "profession": profession,
        "server": server
    }
    db.user_info.update_one({"_id": user_id}, {"$set": user_info}, True)
    msg = "设置成功!"
    await user_manage.finish(msg)


@create_team.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    # 开团 集合时间(默认2小时后) 服务器(首选角色服务器, 次选群服务器) 团队公告(必填) 成员配置(选填)
    user_id = int(event.user_id)
    group_id = int(event.group_id)
    bot_id = int(bot.self_id)
    text = event.get_plaintext()

    user_info = db.user_info.find_one({"_id": user_id})
    team_leader_name = user_info.get("default_user")
    if not team_leader_name:
        await create_team.finish(
            "你都没绑定过角色，还想开团？赶紧绑定角色吧\n发送“角色管理 角色名称 心法 服务器(选填)”")
    user_data = user_info["user_data"][team_leader_name]

    create_time = datetime.now()
    meeting_time_str = re.findall(
        r"[0-1]{0,1}\d-[0-3]{0,1}\d [0-6]{0,1}\d[:：][0-6]{0,1}\d", text)
    # 获取集合时间
    if meeting_time_str:
        now_year = create_time.year
        meeting_time = datetime.strptime(
            f"{now_year}-" + meeting_time_str[0].replace("：", ":"),
            "%Y-%m-%d %H:%M")
        time_difference = meeting_time - create_time
        if time_difference.days < 0:
            await create_team.finish("不可以用过去的时间")
        if time_difference.seconds < 1800:
            await create_team.finish("至少预留30分钟准备时间吧")
        if time_difference.days > 10:
            await create_team.finish("集合时间只能预约10天以内")
    else:
        meeting_time = create_time + timedelta(hours=2)

    # 获取开团服务器
    server = re.findall(r" ([\u4e00-\u9fa5]{2,4}) ", text)
    if server:
        server = server[0]
    else:
        server = user_data.get("server")
    if not server:
        server = db.group_conf.find_one({"_id": group_id}).get("server")
    if not server:
        await create_team.finish("获取不到团队所在服务器, 请手动指定服务器, 或绑定群服务器, 或个人绑定角色")
    server = await jx3_searcher.get_server(server)
    if not server:
        await create_team.finish("你的服务器写错了吧，我只认全称！黑话我听不懂！")

    # 获取团队公告
    team_announcements = text.split(" ")[-1]
    if len(team_announcements) >= 50:
        await create_team.finish("团队公告不能超过50字")
    if not content_check(team_announcements)[0]:
        await create_team.finish("团队公告内容不太健康，改一下吧")

    # 获取成员配置
    team_conf = re.findall(r" [\[【](.+?)[】\]]", text)
    team_configuration = {"人数": 25}
    if team_conf:
        team_conf_list = re.findall(r"([\u4e00-\u9fa5]{2,5}|[DTHB])(\d{1,2})",
                                    team_conf[0])
        for k, v in team_conf_list:
            if k in conf_list:
                team_configuration[conf_list[k]] = int(v)
            else:
                profession = JX3PROFESSION.get_profession(k)
                if profession:
                    team_configuration[profession] = int(v)

    if user_data['profession'] in JX3PROFESSION_ROLE.坦克.value:
        user_data['role'] = "坦克"
    elif user_data['profession'] in JX3PROFESSION_ROLE.治疗.value:
        user_data['role'] = "治疗"
    else:
        user_data['role'] = "输出"
    team_leader_info = {
        "user_name": team_leader_name,
        "user_id": user_info['_id'],
        "group_id": group_id,
        "bot_id": bot_id,
        "profession": user_data['profession'],
        "role": user_data["role"]
    }
    team_members = [
        [team_leader_info, {}, {}, {}, {}],
        [{}, {}, {}, {}, {}],
        [{}, {}, {}, {}, {}],
        [{}, {}, {}, {}, {}],
        [{}, {}, {}, {}, {}],
    ]
    insert_data = {
        "user_id": user_id,
        "group_id": group_id,
        "bot_id": bot_id,
        "server": server,
        "team_leader_name": team_leader_name,
        "team_members": team_members,
        "create_time": create_time,
        "meeting_time": meeting_time,
        "team_announcements": team_announcements,
        "team_configuration": team_configuration,
        "registration_switch": True,
        "public_switch": True,
        "need_notice": True
    }
    team_id = db.insert_auto_increment("j3_teams", insert_data)
    user_teams = user_info.get("teams", {})
    if team_leader_name not in user_teams:
        user_teams[team_leader_name] = []
    user_teams[team_leader_name].append(team_id)
    db.user_info.update_one({"_id": user_id}, {"$set": {"teams": user_teams}})

    msg = f"开团成功\n团队编号：{team_id}\n团长：{team_leader_name}\n" \
          f"开团时间：{create_time.strftime('%Y-%m-%d %H:%M:%S')}\n服务器：{server}\n"\
          f"集合时间：{meeting_time.strftime('%Y-%m-%d %H:%M:%S')}\n团队公告：{team_announcements}\n"\
          f"团队限制：{' '.join([f'{k}{v}' for k, v in team_configuration.items()])}"
    await create_team.finish(msg)


def index_in_list(index, team_announcements):
    index_x = int(index[0]) - 1
    index_y = int(index[1]) - 1
    if len(team_announcements) <= index_x:
        return False, 0, 0
    if len(team_announcements[index_x]) <= index_y:
        return False, 0, 0
    return True, index_x, index_y


def del_user_team(user_id, user_name, team_id):
    """删除用户信息表中的对应的团队"""
    user_info = db.user_info.find_one({"_id": user_id})
    user_teams = user_info["teams"]
    if team_id in user_teams[user_name]:
        user_teams[user_name].remove(team_id)
        db.user_info.update_one({"_id": user_id},
                                {"$set": {
                                    "teams": user_teams
                                }})


@set_team.handle()
async def _(event: GroupMessageEvent):
    """
    调整团队
      解散团队: !解散
      转让团长: !转让[坐标]
      关闭报名: !关
      开启报名: !开
      转为私有: !私有
      转为公开: !公开

      标记成员: 标记=坐标
      踢出成员: -坐标
      更改位置: 坐标1>坐标2

      修改公告: "公告内容"
      修改区服：(服务器)
      修改限制: [团队限制]
      集合时间: 月-日 时:分
    """
    user_id = int(event.user_id)
    text = event.get_plaintext()
    team_id = re.findall(r" (\d+) ", text)
    if not team_id:
        await set_team.finish("输入的格式不对，需要指定团队序号。")
    team_id = int(team_id[0])
    team_info = db.j3_teams.find_one({"_id": team_id})
    if not team_info:
        await set_team.finish("团队不存在，请发送“团队信息”进行查看")
    user_info = db.user_info.find_one({"_id": user_id})
    team_leader_name = team_info.get("team_leader_name")
    if team_info.get(
            "user_id"
    ) != user_id or team_leader_name not in user_info["teams"]:
        await set_team.finish("你不是团长，不能调整团队")
    team_members = team_info["team_members"]
    disband_the_team = re.findall(r" ([!！]解散)", text)
    if disband_the_team:
        _, msg = disband(user_id, team_id)
        await disband_team.finish(msg)
    transfer_team = re.findall(r" [!！]转让([1-5]{2})", text)
    if transfer_team:
        transfer_index = transfer_team[-1]
        _, msg = transfer(user_id, team_id, transfer_index)
        await disband_team.finish(msg)

    msg = ""

    registration_switch = re.findall(r" [!！](开|关)", text)
    if registration_switch:
        msg += f"\n团队报名开关：{registration_switch[-1]}"
        team_info["registration_switch"] = True if registration_switch[
            -1] == "开" else False

    public_switch = re.findall(r" [!！](私有|公开)", text)
    if public_switch:
        msg += f"\n团队状态：{public_switch[-1]}"
        team_info[
            "public_switch"] = True if public_switch[-1] == "公开" else False

    set_user_role = re.findall(r" (输出|治疗|坦克|老板|[DTHB])=([1-5]{2})", text)
    if set_user_role:
        for role, user_index in set_user_role:
            res, index_x, index_y = index_in_list(user_index, team_members)
            if not res:
                continue
            team_members[index_x][index_y]["role"] = conf_list[role]
        team_info["team_members"] = team_members
    remove_user = re.findall(r" -([1-5]{2})", text)
    if remove_user:
        for user_index in remove_user:
            res, index_x, index_y = index_in_list(user_index, team_members)
            if not res:
                continue
            member_id = team_members[index_x][index_y]["user_id"]
            member_name = team_members[index_x][index_y]["user_name"]
            if member_id == user_id and member_name == team_leader_name:
                msg += "\n不可以踢自己的团长角色，如果想要解散团队请发送“调整团队 !解散”"
                continue
            del_user_team(user_id, member_name, team_id)
            team_members[index_x][index_y] = {}
            db.user_info.update_one({"_id": member_id}, {"$set": {"team": 0}})

        team_info["team_members"] = team_members
    swap_locations = re.findall(r" ([1-5]{2})[>》]([1-5]{2})", text)
    if swap_locations:
        for user_index1, user_index2 in swap_locations:
            res, index_x1, index_y1 = index_in_list(user_index1, team_members)
            if not res:
                continue
            res, index_x2, index_y2 = index_in_list(user_index2, team_members)
            if not res:
                continue
            team_members[index_x1][index_y1], team_members[index_x2][index_y2] = \
            team_members[index_x2][index_y2], team_members[index_x1][index_y1]
        team_info["team_members"] = team_members
    team_announcements = re.findall(r" [\"“”](.+?)[\"“”]", text)
    if team_announcements:
        team_announcements = team_announcements[-1]
        if len(team_announcements) >= 50:
            msg += "团队公告不能超过50字"
        elif not content_check(team_announcements)[0]:
            msg += "团队公告内容不太健康，改一下吧"
        else:
            team_info["team_announcements"] = team_announcements
    server_re = re.findall(r" [\(（]([\u4e00-\u9fa5]{2,5})[\)）]", text)
    if server_re:
        server = server_re[-1]
        server = await jx3_searcher.get_server(server)
        if server:
            team_info["server"] = server
        else:
            msg = "\n服务器写的不对"
    team_conf = re.findall(r" [\[【](.+?)[】\]]", text)
    if team_conf:
        team_conf_list = re.findall(r"([\u4e00-\u9fa5]{2,5}|[DTHB])(\d{1,2})",
                                    team_conf[0])
        for k, v in team_conf_list:
            if k in conf_list:
                team_info["team_configuration"][conf_list[k]] = int(v)
            else:
                profession = JX3PROFESSION.get_profession(k)
                if profession:
                    team_info["team_configuration"][profession] = int(v)
    meeting_time_str = re.findall(
        r"[0-1]{0,1}\d-[0-3]{0,1}\d [0-6]{0,1}\d[:：][0-6]{0,1}\d", text)
    if meeting_time_str:
        create_time = datetime.utcnow()
        now_year = create_time.year
        meeting_time = datetime.strptime(
            f"{now_year}-" + meeting_time_str[-1].replace("：", ":"),
            "%Y-%m-%d %H:%M")
        time_difference = meeting_time - create_time
        if time_difference.days < 0:
            msg += "不可以用过去的时间"
        elif time_difference.seconds < 1800:
            msg += "至少预留30分钟准备时间吧"
        elif time_difference.days > 10:
            msg += "集合时间只能预约10天以内"
        else:
            team_info["meeting_time"] = meeting_time
    db.j3_teams.update_one({"_id": team_id}, {"$set": team_info})
    msg = "修改完成!" + msg
    await set_team.finish(msg)


def get_time_conf(team_info):
    data = {}
    team_configuration = team_info["team_configuration"]
    team_members_sum = 0
    for i in team_info["team_members"]:
        for j in i:
            if not j:
                continue
            profession = j["profession"]
            role = j["role"]
            team_members_sum += 1
            if profession in team_configuration:
                if profession not in data:
                    data[profession] = {
                        "total": team_configuration[profession]
                    }
                    data[profession]["current"] = 0
                data[profession]["current"] += 1
            if role in team_configuration:
                if role not in data:
                    data[role] = {"total": team_configuration[role]}
                    data[role]["current"] = 0
                data[role]["current"] += 1
    data["人数"] = {
        "current": team_members_sum,
        "total": team_configuration["人数"]
    }
    return data


@view_team.handle()
async def _(event: GroupMessageEvent):
    """查看团队"""
    user_id = int(event.user_id)
    text = event.get_plaintext()
    text_list = text.split()
    if len(text_list) == 2:
        team_id = int(text_list[-1])
        team_info = db.j3_teams.find_one({"_id": team_id})
        if not team_info:
            await view_team.finish("你没加入任何团队")
        team_info["team_configuration"] = get_time_conf(team_info)
        datas = []
        for i, data in enumerate(zip(*team_info["team_members"])):
            datas.append({"index": i + 1, "data": data})
        team_info["team_members"] = datas
        team_info["meeting_time"] = team_info["meeting_time"].strftime(
            "%Y-%m-%d %H:%M")
        pagename = "view_team.html"
        img = await browser.template_to_image(pagename=pagename,
                                              team_info=team_info)
        await view_team.finish(MessageSegment.image(img))
    else:
        user_info = db.user_info.find_one({"_id": user_id})
        user_teams = user_info.get("teams", {})
        datas = []
        tmp_user_teams = deepcopy(user_teams)
        for user_name, teams in user_teams.items():
            for team_id in teams:
                team_info = db.j3_teams.find_one({"_id": team_id})
                if not team_info:
                    tmp_user_teams[user_name].remove(team_id)
                    db.user_info.update_one({"_id": user_id}, {"$set": {"teams": tmp_user_teams}})
                    continue
                datas.append({
                    "user_name": user_name,
                    "profession": user_info["user_data"][user_name]["profession"],
                    "team_id": team_id,
                    "server": team_info["server"],
                    "meeting_time": team_info["meeting_time"].strftime("%Y-%m-%d %H:%M"),
                    "team_announcements": team_info["team_announcements"][:8]
                })
        if not datas:
            await view_team.finish("你没有加入过任何团队")
        pagename = "view_team_list.html"
        img = await browser.template_to_image(pagename=pagename, datas=datas)
        await view_team.finish(MessageSegment.image(img))


@search_team.handle()
async def _(event: GroupMessageEvent):
    """搜索团队"""
    user_id = int(event.user_id)
    group_id = int(event.group_id)
    text = event.get_plaintext()
    user_info = db.user_info.find_one({"_id": user_id})
    text.replace("（", "(").replace("）", ")")
    server_re = re.findall(r" \(([\u4e00-\u9fa5]{2,5})\)", text)
    if server_re:
        server = server_re[0]
    else:
        server = user_info.get("server")
    if not server:
        server = db.group_conf.find_one({"_id": group_id}).get("server")
    if not server:
        await search_team.finish("获取不到团队所在服务器, 请手动指定服务器, 或绑定群服务器, 或个人绑定角色")
    server = await jx3_searcher.get_server(server)
    if not server:
        await search_team.finish("你的服务器写错了吧，我只认全称！黑话我听不懂！")
    current = 1
    if current_re := re.findall(r"^搜索团队(\d+)", text):
        current = int(current_re[0])
        current_tmp = current
    else:
        current_tmp = ""
    condition = text.replace(f"({server})",
                             "").strip(f"搜索团队{current_tmp}").strip()

    filter = {
        "$or": [{
            "group_id": group_id
        }, {
            "server": server,
            "team_announcements": {
                "$regex": condition
            },
            "registration_switch": True,
            "public_switch": True
        }]
    }
    sort = list({'meeting_time': -1}.items())
    total = db.j3_teams.count_documents(filter)
    limit = 10
    skip = (current - 1) * limit
    page_num = math.ceil(total / limit)
    if current > page_num:
        await search_team.finish(f"只能查到{page_num}页")
    j3_teams = db.j3_teams.find(filter=filter,
                                sort=sort,
                                limit=limit,
                                skip=skip)
    datas = []
    for j3_team in j3_teams:
        j3_team["meeting_time"] = j3_team["meeting_time"].strftime(
            "%m-%d %H:%M")
        j3_team["team_configuration"] = get_time_conf(j3_team)
        datas.append(j3_team)
    pagename = "search_team.html"
    img = await browser.template_to_image(pagename=pagename,
                                          datas=list(datas),
                                          current=current,
                                          total=total)
    await search_team.finish(MessageSegment.image(img))


def check_team_leader_name(user_info, j3_teams):
    team_members = j3_teams["team_members"]
    team_configuration = j3_teams["team_configuration"]
    flag = False
    for team_i, team in enumerate(team_members):
        for mem_i, mem in enumerate(team):
            if not mem:
                team_members[team_i][mem_i] = {
                    "user_name": user_info['user_name'],
                    "user_id": user_info['_id'],
                    "profession": user_info['profession'],
                    "role": user_info["role"],
                    "group_id": user_info["group_id"],
                    "bot_id": user_info["bot_id"],
                }
                flag = True
                break
        if flag:
            break
    sum_team_members = sum(team_members, [])
    if not flag:
        return False, "人数已到上限"

    profession_number = 0
    role_number = 0
    for i in sum_team_members:
        if not i:
            continue
        if i["profession"] == user_info['profession']:
            profession_number += 1
        if i["role"] == user_info['role']:
            role_number += 1
    if user_info['profession'] in team_configuration:
        if profession_number > team_configuration[user_info['profession']]:
            return False, f"{user_info['profession']}已到上限"

    if user_info["role"] in team_configuration:
        if role_number > team_configuration[user_info['role']]:
            return False, f"{user_info['role']}已到上限"

    return True, team_members


@register.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    """报名"""
    user_id = int(event.user_id)
    group_id = int(event.group_id)
    bot_id = int(bot.self_id)
    user_info = db.user_info.find_one({"_id": user_id})
    text = event.get_plaintext()
    text_list = text.split()
    team_id = int(text_list[-1])
    default_user = user_info.get("default_user")
    if not default_user:
        await register.finish("你还没有绑定角色：\n发送“角色管理 角色名称 心法 服务器(选填)”")
    if len(text_list) == 3:
        user_name = text_list[1]
    else:
        user_name = default_user
    teams = user_info["teams"]
    if team_id in teams.get(user_name, []):
        await register.finish(f"你已经在该团队中了，可以发送“查看团队 {team_id}”进行查看")

    j3_teams = db.j3_teams.find_one({"_id": team_id})

    if not j3_teams:
        await register.finish("没有找到这个团队")
    if not j3_teams.get("registration_switch"):
        await register.finish("该团队已停止报名")
    if not (j3_teams.get("public_switch")
            or j3_teams.get("group_id") != group_id):
        await register.finish("该团队没有公开报名")
    user_data = user_info["user_data"][user_name]
    user_data["group_id"] = group_id
    user_data["bot_id"] = bot_id
    user_data["user_name"] = user_name
    user_data["_id"] = user_info["_id"]

    if user_data['profession'] in JX3PROFESSION_ROLE.坦克.value:
        user_data['role'] = "坦克"
    elif user_data['profession'] in JX3PROFESSION_ROLE.治疗.value:
        user_data['role'] = "治疗"
    else:
        user_data['role'] = "输出"

    res, data = check_team_leader_name(user_data, j3_teams)
    if res:
        db.j3_teams.update_one({"_id": j3_teams["_id"]},
                               {"$set": {
                                   "team_members": data
                               }})
        teams[user_name].append(j3_teams["_id"])
        db.user_info.update_one({"_id": user_id}, {"$set": {"teams": teams}})
        await register.finish("报名成功！")
    else:
        await register.finish(data)
