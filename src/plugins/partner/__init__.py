from nonebot import export, on_regex
import re
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import GroupMessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP, GROUP_ADMIN, GROUP_OWNER
from nonebot.permission import SUPERUSER
from src.utils.log import logger

from . import data_source as source

Export = export()
Export.plugin_name = "情缘功能"
Export.plugin_command = "情缘"
Export.plugin_usage = "慌什么，组织会给你分配情缘的"
Export.default_status = True

partner_menu = on_regex(r"^(情缘|情缘功能)$",
                          permission=GROUP,
                          priority=5,
                          block=True)

find_partner_cooldown_time = on_regex(r"^(分配情缘冷却 \d+)$",
                                      permission=SUPERUSER | GROUP_ADMIN
                                      | GROUP_OWNER,
                                      priority=4,
                                      block=True)
find_partner_do_not_disturb = on_regex(r"^(分配情缘免打扰 (开|关))$",
                                       permission=SUPERUSER | GROUP_ADMIN
                                       | GROUP_OWNER,
                                       priority=4,
                                       block=True)

find_partner = on_regex(r"^((找|分配|安排)(情缘|亲友))$",
                        permission=GROUP,
                        priority=5,
                        block=True)
partner_request = on_regex(r"^(求情缘 *\[CQ:at,qq=\d+\] *)$",
                           permission=GROUP,
                           priority=5,
                           block=True)
partner_agreed = on_regex(r"^(接受情缘 *\[CQ:at,qq=\d+\] *)$",
                          permission=GROUP,
                          priority=5,
                          block=True)
partner_request_list = on_regex(r"^(情缘申请列表|我的鱼塘)$",
                                permission=GROUP,
                                priority=5,
                                block=True)
clear_partner_request = on_regex(r"^(清空情缘列表|清空鱼塘|清空情缘申请列表)$",
                                 permission=GROUP,
                                 priority=5,
                                 block=True)
my_partner = on_regex(r"^(我的情缘)$", permission=GROUP, priority=5, block=True)
parted = on_regex(r"^(死情缘)$", permission=GROUP, priority=5, block=True)


@partner_menu.handle()
async def _():
    '''情缘菜单'''
    msg = "如何搞情缘？\n\n- 分配情缘\n- 求情缘@QQ\n- 接受情缘@QQ\n- 我的情缘\n- 死情缘\n- 情缘申请列表\n- 清空情缘申请列表\n\n管理设置\n- 分配情缘冷却 100\n- 分配情缘免打扰 开/关"
    await find_partner.finish(msg)


@find_partner_cooldown_time.handle()
async def _(event: GroupMessageEvent):
    '''分配情缘冷却时间设置'''
    try:
        group_id = event.group_id
        get_msg = event.get_plaintext().split()
        if len(get_msg) != 2:
            await find_partner_cooldown_time.finish("输入错误！")
        cooldown_time = int(get_msg[1])
        msg = await source.set_find_partner_cooldown_time(
            group_id, cooldown_time)
        await find_partner_cooldown_time.finish(msg)
    except TypeError as e:
        logger.warning(f"<y>群{group_id}</y> | 分配情缘冷却 | {str(e)}")
        await find_partner_cooldown_time.finish("输入错误！")


@find_partner_do_not_disturb.handle()
async def _(event: GroupMessageEvent):
    '''分配情缘免打扰开关'''
    try:
        group_id = event.group_id
        get_msg = event.get_plaintext().split()
        if len(get_msg) != 2:
            await find_partner_do_not_disturb.finish("输入错误！")
        do_not_disturb_switch = get_msg[1] == "开"
        msg = await source.set_find_partner_do_not_disturb(
            group_id, do_not_disturb_switch)
        await find_partner_do_not_disturb.finish(msg)
    except TypeError as e:
        logger.error(f"<y>群{group_id}</y> | 分配情缘冷却 | {str(e)}")
        await find_partner_do_not_disturb.finish("输入错误！")


@find_partner.handle()
async def _(bot: Bot, event: GroupMessageEvent):
    '''分配情缘'''
    user_id = event.user_id
    group_id = event.group_id
    end_str = event.raw_message[-2:]
    if end_str not in ["情缘", "亲友"]:
        return
    logger.info(f"<y>群{group_id}</y> | <g>{user_id}</g> | 分配{end_str}")
    group_member_list = await bot.get_group_member_list(group_id=group_id)
    msg = await source.get_find_partner_to_group(user_id, group_id, end_str,
                                                 group_member_list)
    await find_partner.finish(msg)


@partner_request.handle()
async def _(event: GroupMessageEvent):
    '''求情缘'''
    user_id = event.user_id
    user_name = event.sender.nickname
    at_member_obj = re.compile(r"^求情缘 *\[CQ:at,qq=(\d*)\] *$")
    at_member_list = at_member_obj.findall(event.raw_message)
    if not at_member_list:
        msg = "需要艾特"
        await find_partner.finish(msg)
    at_qq = int(at_member_list[0])
    if at_qq == user_id:
        msg = f"大家快来看啊，{user_name}要跟自己情缘啦！！"
        await find_partner.finish(msg)

    msg = await source.partner_request_to_group(user_id, user_name, at_qq)
    await find_partner.finish(msg)


@partner_agreed.handle()
async def _(event: GroupMessageEvent):
    '''接受情缘'''
    user_id = event.user_id
    user_name = event.sender.nickname
    at_member_obj = re.compile(r"^接受情缘 *\[CQ:at,qq=(\d*)\] *$")
    at_member_list = at_member_obj.findall(event.raw_message)
    if not at_member_list:
        msg = "需要艾特"
        await find_partner.finish(msg)
    at_qq = int(at_member_list[0])

    msg = await source.partner_agreed_to_group(user_id, user_name, at_qq)
    await find_partner.finish(msg)


@partner_request_list.handle()
async def _(event: GroupMessageEvent):
    user_id = event.user_id
    user_name = event.sender.nickname
    if event.raw_message == "我的鱼塘":
        title = f"{user_name}的鱼塘"
    else:
        title = f"{user_name}的情缘申请列表"
    msg = await source.get_partner_request_list(user_id, title)
    await find_partner.finish(msg)


@my_partner.handle()
async def _(event: GroupMessageEvent):
    user_id = event.user_id
    user_name = event.sender.nickname
    msg = await source.get_my_partner(user_id, user_name)
    await my_partner.finish(msg)


@parted.handle()
async def _(event: GroupMessageEvent):
    user_id = event.user_id
    msg = await source.parted_to_group(user_id)
    await parted.finish(msg)


@clear_partner_request.handle()
async def _(event: GroupMessageEvent):
    user_id = event.user_id
    msg = await source.clear_partner_request(user_id)
    await parted.finish(msg)