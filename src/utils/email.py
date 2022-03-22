from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header

from aiosmtplib import SMTP, SMTPException
from src.utils.config import config
from src.utils.log import logger
from src.utils.db import db

import random


class MailClient(object):
    '''发送邮件class'''
    _host: str
    '''服务器地址'''
    _pord: int
    '''服务器端口'''
    _user: str
    '''用户名'''
    _pass: str
    '''授权码'''
    _sender: str
    '''发送者'''
    _receiver: str
    '''接受方'''

    def __new__(cls, *args, **kwargs):
        '''单例'''
        if not hasattr(cls, '_instance'):
            orig = super(MailClient, cls)
            cls._instance = orig.__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        '''初始化'''
        self._host = config.mail['host']
        self._pord = config.mail['pord']
        self._domain = config.mail['domain']
        self._user = config.mail['user']
        self._pass = config.mail['pass']
        self._sender = config.mail['sender']
        self._receiver = config.mail['receiver']

    async def send_mail(self, receiver: str, mail_title: str,
                        mail_content: str) -> None:
        n = random.randint(1, 15)
        self._mail = f"{self._user}{n}@{self._domain}"
        text = mail_content
        message = MIMEText(text)
        message['From'] = Header(f'{self._sender}<{self._mail}>', 'utf-8')

        message['To'] = receiver
        message["Subject"] = mail_title
        msg = f"{self._sender}[{self._mail}] -> {receiver}: {text}"
        logger.info(msg)

        try:
            async with SMTP(hostname=self._host, port=self._pord,
                            use_tls=True) as smtp:
                await smtp.login(self._mail, self._pass)
                await smtp.send_message(message)
        except SMTPException as e:
            log = f"发送邮件失败，原因：{str(e)}"
            logger.error(log)
        except Exception as e:
            logger.error(f"<r>发送邮件失败，可能是你的配置有问题：{str(e)}</r>")

    async def bot_offline(self, robot_id: int):
        db.bot_info.update_one({"_id": robot_id},
                               {"$set": {
                                   "online_status": False
                               }}, True)
        bot_name = db.bot_info.find_one({"_id": robot_id})["bot_name"]
        mail_title = f"机器人[{bot_name}]({robot_id})掉线"
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mail_content = f"你的机器人：[{bot_name}]({robot_id}) 在 {time_now} 掉线了！"
        await self.send_mail(self._receiver, mail_title, mail_content)

    async def bot_online(self, robot_id: int):
        bot_name = db.bot_info.find_one({"_id": robot_id})["bot_name"]
        mail_title = f"机器人[{bot_name}]({robot_id})上线"
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mail_content = f"你的机器人：[{bot_name}]({robot_id}) 在 {time_now} 上线了！"
        await self.send_mail(self._receiver, mail_title, mail_content)


mail_client = MailClient()
'''发送邮件客户端'''
