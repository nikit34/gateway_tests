from datetime import datetime, timedelta
import base64
import json
import os
import requests


class AzureTestRest:
    def __init__(self, fixture_obj):
        self.fixture_obj = fixture_obj
        _proxy_obj = fixture_obj['proxy']
        _proxy_url = f"http://{_proxy_obj['username']}:{_proxy_obj['password']}@{_proxy_obj['host']}:{_proxy_obj['port']}"
        self.proxy_lk = {
            "http": _proxy_url,
            "https": _proxy_url
        }
        self.headers = {
            "Authorization": "Basic " + fixture_obj["pat"]
        }

    def get_test_point(self, plan_id, suite_id, test_point_id):
        response = requests.get(
            url=f"{self.fixture_obj['org_url']}{self.fixture_obj['project']}/_apis/test/Plans/{plan_id}/Suites/{suite_id}/points/{test_point_id}?api-version=6.0",
            proxies=self.proxy_lk,
            headers=self.headers,
            verify=False,
        )
        return response.json()

    def get_test_point_name(self, plan_id, suite_id, test_point_id):
        response = self.get_test_point(plan_id, suite_id, test_point_id)
        return response["testCase"]["name"]

    def post_test_runs(self, data):
        headers = self.headers
        headers["Content-Type"] = "application/json"
        response = requests.post(
            url=f"{self.fixture_obj['org_url']}{self.fixture_obj['project']}/_apis/test/runs?api-version=6.0",
            proxies=self.proxy_lk,
            headers=headers,
            verify=False,
            data=json.dumps(data)
        )
        return response

    def create_get_test_run(self, name):
        completed_date = (datetime.now() - timedelta(hours=3)).strftime("%m/%d/%Y %H:%M:%S")
        data = {
            "name": name,
            "automated": True,
            "completeDate": completed_date,
            "owner": {
                "displayName": "Nikita Permyakov"
            },
            "type": "NoConfigRun"
        }
        response = self.post_test_runs(data)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_test_run_id(test_run):
        return test_run["id"]

    def post_test_run_attachment(self, test_run_id, data):
        headers = self.headers
        headers["Content-Type"] = "application/json"
        response = requests.post(
            url=f"{self.fixture_obj['org_url']}{self.fixture_obj['project']}/_apis/test/Runs/{test_run_id}/attachments?api-version=6.0-preview.1",
            proxies=self.proxy_lk,
            headers=headers,
            verify=False,
            data=json.dumps(data)
        )
        return response

    def create_test_run_attachment(self, test_run_id):
        file_name = "monitor_kos.log"
        file_path = "logs/"
        with open(file_path + file_name, "rb") as file:
            data = file.read()
        byte_arr = base64.b64encode(data).decode("utf-8")
        data = {
            "comment": "Log file of TGW",
            "fileName": file_name,
            "stream": byte_arr
        }
        response = self.post_test_run_attachment(test_run_id, data)
        response.raise_for_status()

    def post_test_results(self, test_run_id, data):
        headers = self.headers
        headers["Content-Type"] = "application/json"
        response = requests.post(
            url=f"{self.fixture_obj['org_url']}{self.fixture_obj['project']}/_apis/test/Runs/{test_run_id}/results?api-version=6.0",
            proxies=self.proxy_lk,
            headers=headers,
            verify=False,
            data=json.dumps(data)
        )
        return response

    def add_get_test_result(self, test_run_id, outcome, test_point_name, duration):
        outcome = outcome.replace("skipped", "Paused")
        seconds, milliseconds = str(duration).split(".")
        duration = seconds + "," + milliseconds[:3]
        data = [{
            "outcome": outcome,
            "testCaseTitle": test_point_name,
            "computerName": os.uname()[1],
            "automatedTestName": test_point_name,
            "durationInMs": duration,
            "owner": {
                "displayName": "Nikita Permyakov"
            },
            "runBy": {
                "displayName": "Nikita Permyakov"
            }
        }]
        response = self.post_test_results(test_run_id, data)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_test_result_id(test_result):
        return test_result["value"][0]["id"]

    def post_test_result_attachment(self, test_run_id, test_result_id, data):
        headers = self.headers
        headers["Content-Type"] = "application/json"
        response = requests.post(
            url=f"{self.fixture_obj['org_url']}{self.fixture_obj['project']}/_apis/test/Runs/{test_run_id}/Results/{test_result_id}/attachments?api-version=6.0-preview.1",
            proxies=self.proxy_lk,
            headers=headers,
            verify=False,
            data=json.dumps(data)
        )
        return response

    def create_test_result_attachment(self, test_run_id, test_result_id):
        file_name = "monitor_kos.log"
        file_path = "logs/"
        with open(file_path + file_name, "rb") as file:
            data = file.read()
        byte_arr = base64.b64encode(data).decode("utf-8")
        data = {
            "comment": "Log file of TGW",
            "fileName": file_name,
            "stream": byte_arr
        }
        response = self.post_test_result_attachment(test_run_id, test_result_id, data)
        response.raise_for_status()

    def patch_test_runs(self, test_run_id, data):
        headers = self.headers
        headers["Content-Type"] = "application/json"
        response = requests.patch(
            url=f"{self.fixture_obj['org_url']}{self.fixture_obj['project']}/_apis/test/runs/{test_run_id}?api-version=6.0",
            proxies=self.proxy_lk,
            headers=headers,
            verify=False,
            data=json.dumps(data)
        )
        return response

    def update_test_run_state(self, test_run_id, outcome):
        data = {
            "runSummary": [{
                "resultCount": 1,
                "testOutcome": outcome
            }]
        }
        if outcome == "passed":
            data["state"] = "Completed"
        elif outcome == "failed":
            data["state"] = "Aborted"
        else:
            data["state"] = "NotStarted"
        response = self.patch_test_runs(test_run_id, data)
        response.raise_for_status()
