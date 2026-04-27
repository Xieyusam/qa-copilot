import base64
import json
import re

import requests


class FeishuDoc():
    def __init__(self, feishu_url):
        self.feishu_url = feishu_url
        res = requests.post(url='https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
                            headers={"Content-Type": "application/json; charset=utf-8"},
                            json={"app_id": "cli_a49f2a2b47bc500e", "app_secret": "0racruVqudetqL1QCE9JNbNRmdAK7BWn"})
        res.data = res.json()
        self.tat = res.data["tenant_access_token"]
        sheet_token_match = re.match("http[s]{0,1}://.*?/(wiki|sheets)/(.*$)", feishu_url)
        if sheet_token_match:
            s_type = sheet_token_match.group(1)
            s_token = sheet_token_match.group(2).split("?")[0]
            # get wiki sheet token, wiki is diff from sheets
            if s_type == "wiki":
                # print("Get sheet token")
                res_data = requests.get(
                    url="https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node",
                    headers={"Authorization": "Bearer %s" % self.tat},
                    params={"token": s_token, "obj_type": "wiki"}
                )
                res_data = res_data.json()
                s_token = res_data["data"]["node"]["obj_token"]
        else:
            raise ValueError("Feishu sheet url error!")

        self.sheet_token = s_token
        # self.sheet_id = sheet_id

    def fetchInitInfo(self):
        res = requests.post(url='https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
                            headers={"Content-Type": "application/json; charset=utf-8"},
                            json={"app_id": "cli_a49f2a2b47bc500e", "app_secret": "0racruVqudetqL1QCE9JNbNRmdAK7BWn"})
        res.data = res.json()
        self.tat = res.data["tenant_access_token"]
        sheet_token_match = re.match("http[s]{0,1}://.*?/(wiki|sheets)/(.*$)", self.feishu_url)
        if sheet_token_match:
            s_type = sheet_token_match.group(1)
            s_token = sheet_token_match.group(2).split("?")[0]
            # get wiki sheet token, wiki is diff from sheets
            if s_type == "wiki":
                # print("Get sheet token")
                res_data = requests.get(
                    url="https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node",
                    headers={"Authorization": "Bearer %s" % self.tat},
                    params={"token": s_token, "obj_type": "wiki"}
                )
                res_data = res_data.json()
                s_token = res_data["data"]["node"]["obj_token"]
        else:
            raise ValueError("Feishu sheet url error!")

        self.sheet_token = s_token

    def fs_request(self, method, **kwargs):
        """feishu open api request"""
        if not hasattr(self, "tenant_access_token"):
            res = requests.post(
                url="https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
                headers={"Content-Type": "application/json; charset=utf-8"},
                json={"app_id": "cli_a49f2a2b47bc500e", "app_secret": "0racruVqudetqL1QCE9JNbNRmdAK7BWn"}
            )
            print("Get feishu token")
            # print(res.text)
            res_data = res.json()
            if res_data.get("code") == 0:
                setattr(self, "tenant_access_token", res_data["tenant_access_token"])
            else:
                raise ValueError(res_data.get("msg", "Failed to obtain feishu token"))
        kwargs["headers"] = {
            "Authorization": "Bearer %s" % getattr(self, "tenant_access_token"),
            "Content-Type": "application/json; charset=utf-8"
        }
        res = getattr(requests, method)(**kwargs)
        # print(res.text)
        res_data = res.json()
        code = res_data.get("code")
        if code == 91403:
            raise PermissionError(
                "没有文档权限，打开对应的文档，在页面右上方「...」->「...更多」-> 「添加文档应用」，将云测平台助手添加到文档应用，并开启可编辑权限")
        if code != 0:
            raise ValueError(res_data.get("msg"))
        return res_data

    # def get_rowshasdata(self, range):
    #     res = requests.get(
    #         url=f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{self.sheet_id}/values/{range}",
    #         headers={"Authorization": "Bearer %s" % self.tat,
    #                  "Content-Type": "application/json; charset=utf-8"},
    #     )
    #     data = res.json()
    #     if data['code'] == 0 and 'values' in data['data']['valueRange']:
    #         rows = data['data']['valueRange']['values']
    #         row_count = len(rows)  # 有数据的行数
    #         print(f"有数据的行数：{row_count}")
    #     else:
    #         print("获取数据失败或数据中无值")
    def getTotalRows(self, sheet_id):
        res = requests.get(
            url='https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/%s/sheets/%s' % (self.sheet_token, sheet_id),
            headers={"Authorization": "Bearer %s" % self.tat,
                     "Content-Type": "application/json; charset=utf-8"},
        )
        res.data = res.json()
        # print(res.data)
        return res.data['data']['sheet']["grid_properties"]["row_count"]

    def insertEmptyRows(self, rownum, sheet_id):
        res = requests.post(
            url='https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/%s/dimension_range' % self.sheet_token,
            headers={"Authorization": "Bearer %s" % self.tat,
                     "Content-Type": "application/json; charset=utf-8"},
            json={
                "dimension": {
                    "sheetId": sheet_id,
                    "majorDimension": "ROWS",
                    "length": rownum
                }
            }
        )

    # 可以往单个单元格中写入字符串
    def insertValue(self, info, scope, sheet_id):
        info1 = []
        info1.append(info)
        newinfo = [[i] for i in info1]
        res = requests.put(
            url='https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/%s/values' % self.sheet_token,
            headers={"Authorization": "Bearer %s" % self.tat,
                     "Content-Type": "application/json; charset=utf-8"},
            json={
                "valueRange":
                    {
                        "range": sheet_id + "!" + scope,
                        "values": newinfo
                    }}
        )
        print(res.json())

    def updateColumns(self, info, scope, sheet_id):

        newinfo = [[i] for i in info]
        res4 = requests.post(
            url="https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/%s/values_batch_update" % self.sheet_token,
            headers={"Authorization": "Bearer %s" % self.tat,
                     "Content-Type": "application/json; charset=utf-8"},
            json={
                "valueRanges": [
                    {
                        "range": sheet_id + "!" + scope,
                        "values": newinfo
                    }]}
        )
        res4.data = res4.json()
        if res4.data['code'] != 0:
            # 重新获取一遍表格信息
            self.fetchInitInfo()
            print('重新获取一遍表格信息')
            res5 = requests.post(
                url="https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/%s/values_batch_update" % self.sheet_token,
                headers={"Authorization": "Bearer %s" % self.tat,
                         "Content-Type": "application/json; charset=utf-8"},
                json={
                    "valueRanges": [
                        {
                            "range": sheet_id + "!" + scope,
                            "values": newinfo
                        }]}
            )

    def getCellValue(self, scope, sheet_id):
        res = requests.get(
            url="https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/%s/values/%s" % (
            self.sheet_token, sheet_id + "!" + scope),
            headers={"Authorization": "Bearer %s" % self.tat,
                     "Content-Type": "application/json; charset=utf-8"},
        )
        res.data = res.json()
        celllist = res.data["data"]['valueRange']["values"]
        celllist = [i for x in celllist for i in x]
        new_celllist = []
        for i in celllist:
            if isinstance(i, str):
                new_celllist.append(i)
            if isinstance(i, float) or isinstance(i, int):
                new_celllist.append(float(format(i, ".1f")))
        return new_celllist

    def adjustSheetPos(self, sheet_id, pos=0):
        res = requests.post(
            url="https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/%s/sheets_batch_update" % self.sheet_token,
            headers={"Authorization": "Bearer %s" % self.tat,
                     "Content-Type": "application/json; charset=utf-8"},
            json={
                "requests": [
                    {
                        "updateSheet": {
                            "properties": {
                                "sheetId": sheet_id,
                                "index": pos
                            }
                        }
                    }
                ]
            }
        )

    def clearData(self, startRow, sheet_id):
        total_row_count = self.getTotalRows()
        res = requests.delete(
            url="https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/%s/dimension_range" % self.sheet_token,
            headers={"Authorization": "Bearer %s" % self.tat,
                     "Content-Type": "application/json; charset=utf-8"},
            json={
                "dimension": {
                    "sheetId": sheet_id,
                    "majorDimension": "ROWS",
                    "startIndex": startRow,
                    "endIndex": total_row_count
                }
            }
        )

    def setSelectlist(self, choices, colors, column, sheet_id):
        total_row_count = self.getTotalRows()
        res = requests.post(
            url="https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/%s/dataValidation" % self.sheet_token,
            headers={"Authorization": "Bearer %s" % self.tat,
                     "Content-Type": "application/json; charset=utf-8"},
            json={
                "range": "%s!%s2:%s%s" % (sheet_id, column, column, str(total_row_count)),
                "dataValidationType": "list",
                "dataValidation": {
                    "conditionValues": choices,
                    "options": {
                        "multipleValues": False,
                        "highlightValidData": True,
                        "colors": colors
                    }
                }
            }
        )

    def uploadImage(self, picdir, scope, sheet_id):
        with open(picdir, 'rb') as f:
            url = 'https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/%s/values_image' % self.sheet_token
            fb = f.read()
            misssing_padding = 4 - len(fb) % 4
            if misssing_padding:
                fb += b'=' * misssing_padding
            fb = base64.b64encode(fb).decode('utf-8')
            data = {
                "range": sheet_id + "!" + scope,
                "image": fb,
                "name": "a.png",
            }
            rsp = requests.post(url, data=json.dumps(data),
                                headers={"Authorization": "Bearer %s" % self.tat,
                                         "Content-Type": "application/json"})
            print(rsp.json())
            return rsp.json()
