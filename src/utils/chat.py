import json
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.nlp.v20190408 import nlp_client, models
from src.utils.config import config
# from config import config

secretId = config.nlp.get("secretId")
secretKey = config.nlp.get("secretKey")


async def chat(msg):
    try:
        cred = credential.Credential(secretId, secretKey)
        httpProfile = HttpProfile()
        httpProfile.endpoint = "nlp.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        client = nlp_client.NlpClient(cred, "ap-guangzhou", clientProfile)
        msg = msg.replace("二猫子", "腾讯小龙女")
        req = models.ChatBotRequest()
        params = {"Query": str(msg)}
        req.from_json_string(json.dumps(params))

        resp = client.ChatBot(req)
        reply = resp.Reply
        reply = reply.replace("腾讯小龙女", "二猫子").replace("小龙女", "二猫子").replace(
            "可爱小姐姐", "二猫子").replace("小仙女", "二猫子").replace("龙女", "二猫子")
        return reply
    except TencentCloudSDKException as err:
        print(err)

if __name__ == "__main__":
    print(chat("你是谁"))
