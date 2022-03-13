# coding: utf-8

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkmoderation.v2.region.moderation_region import ModerationRegion
from huaweicloudsdkcore.exceptions import exceptions
from huaweicloudsdkmoderation.v2 import *
from src.utils.config import config
import re

default_categories = [
    "politics", "porn", "ad", "abuse", "contraband", "flood", "emz_black_list"
]

ak = config.huaweicloudsdkcore.get("ak")
sk = config.huaweicloudsdkcore.get("sk")
region = config.huaweicloudsdkcore.get("region")


def content_check(content, categories=default_categories):
    if re.match(
            "(\w+\.)+[com|cn|net|xyz|org|gov|mil|edu|biz|info|pro|name|coop|travel|xxx|idv|aero|museum|mobi|asia|tel|int|post|jobs|cat]",
            content):
        return False, None
    credentials = BasicCredentials(ak, sk)

    client = ModerationClient.new_builder() \
        .with_credentials(credentials) \
        .with_region(ModerationRegion.value_of(region)) \
        .build()

    try:
        request = RunTextModerationRequest()
        listTextDetectionItemsReqItemsbody = [
            TextDetectionItemsReq(text=content, type="content")
        ]
        request.body = TextDetectionReq(
            items=listTextDetectionItemsReqItemsbody, categories=categories)
        response = client.run_text_moderation(request)
        if response.result.suggestion == "pass":
            return True, None
        return False, response.result.detail
    except exceptions.ClientRequestException as e:
        print(e.status_code)
        print(e.request_id)
        print(e.error_code)
        print(e.error_msg)


if __name__ == "__main__":
    print(content_check(""))
