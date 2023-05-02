import json
import requests


class AzureTestPlanRest:
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

    def get_test_points(self, plan_id, suite_id):
        response = requests.get(
            url=f"{self.fixture_obj['org_url']}{self.fixture_obj['project']}/_apis/testplan/Plans/{plan_id}/Suites/{suite_id}/TestPoint?api-version=6.0-preview.2",
            proxies=self.proxy_lk,
            headers=self.headers,
            verify=False
        )
        return response.json()

    @staticmethod
    def filter_test_point_id_by_test_case_id(test_points, test_case_id):
        for value in test_points["value"]:
            if int(test_case_id) == value["testCaseReference"]["id"]:
                return value["id"]
        print("Test case ID is not present in selection of test points")

    def patch_test_points(self, plan_id, suite_id, data):
        headers = self.headers
        headers["Content-Type"] = "application/json"
        response = requests.patch(
            url=f"{self.fixture_obj['org_url']}{self.fixture_obj['project']}/_apis/testplan/Plans/{plan_id}/Suites/{suite_id}/TestPoint?api-version=6.0-preview.2",
            proxies=self.proxy_lk,
            headers=headers,
            verify=False,
            data=json.dumps(data)
        )
        return response

    def upload_test_result(self, plan_id, suite_id, test_point_id, outcome):
        outcome = outcome.replace("skipped", "paused")
        data = [{
            "id": test_point_id,
            "results": {
                "outcome": outcome
            },
            "tester": {
                "displayName": "Nikita Permyakov"
            }
        }]
        response = self.patch_test_points(plan_id, suite_id, data)
        response.raise_for_status()
