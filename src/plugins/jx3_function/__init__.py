import re

from nonebot import on_regex
from src.utils.db import db

class REGEX(Enum):
    '''正则枚举'''
    绑定角色 = r"^绑定角色( [\u4e00-\u9fa5]+){0,3}( \w+@\w+\.[a-z]{2,8}){0,1}$"
    开团 = r"^开团 .+$"
    团队信息 = r""
    修改团队信息 = r""
    报名开关 = r"^开团 .+$"
    搜索团队 = r"^开团 .+$"
    报名 = r"^开团 .+$"
    标记老板 = r"^开团 .+$"
    关注团长 = r""
    我的关注 = r""
    拉黑团员 = r""
    拉黑团长 = r""
    准备就绪 = r"^准备就绪$"
    

bind_user = on_regex(pattern=REGEX.绑定角色.value, permission=GROUP, priority=5, block=True)
create_team = on_regex(pattern=REGEX.开团.value, permission=GROUP, priority=5, block=True)
search_team = on_regex(pattern=REGEX.搜索团队.value, permission=GROUP, priority=5, block=True)
register = on_regex(pattern=REGEX.报名.value, permission=GROUP, priority=5, block=True)

@bind_user.handle()
async def _(event: GroupMessageEvent):
    # 角色名称 心法 服务器(选填) 邮箱(选填)
    user_id = int(event.user_id)
    text = event.get_plaintext()
    help_msg = "绑定角色 角色名称 心法 服务器(选填) 邮箱(选填)"
    if text == "绑定角色":
        await bind_user.finish(help_msg)
    text_list = text.split(" ")
    text_len = len(text_list)
    if text_len < 3:
        await bind_user.finish(help_msg)
    data = {
        "user_name": text_list[1],
        "profession": text_list[2]
    }
    if text_len > 3:
        data["server"] = text_list[3]
    email = re.findall(r"\w+@\w+\.[a-z]{2,8}", text)
    if email:
        data["email"] = email[1]
    db.user_info.update_one({"_id": user_id}, {"$set": data}, True)
    await bind_user.finish("绑定成功!")



    
@create_team.hanle()
async def _(event: GroupMessageEvent):
    # 开团 集合时间(默认2小时后) 服务器(首选角色服务器, 次选群服务器) 团队名称(首次必填) 团队说明(首次必填)
    user_id = event.user_id

