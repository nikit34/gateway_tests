import os
from pathlib import Path
import xml.etree.ElementTree as ET
from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication


script_dir = os.path.dirname(os.path.abspath(__file__))


class AzureTests(object):
    def __init__(self, repository_path, settings):
        self.repository_path = repository_path
        self.user_home_dir = str(Path(self.repository_path).parent.absolute())
        if "REQUESTS_CA_BUNDLE" not in os.environ:
            os.environ["REQUESTS_CA_BUNDLE"] = script_dir + "/Kaspersky_Root_CA_G3.crt"
        self.settings = settings
        self.testpaths = self.settings["testpaths"]
        self.personal_access_token = self.settings["pat"]
        self.organization_url = self.settings["org_url"]
        self.project = self.settings["project"]
        self.test_plan_id = self.settings["test_plan_id"]
        self.credentials = BasicAuthentication("", self.personal_access_token)
        self.connection = Connection(base_url=self.organization_url, creds=self.credentials)

    def _get_autotest_name(self, wid):
        work_item_tracking_client = self.connection.clients_v6_0.get_work_item_tracking_client()
        work_item = work_item_tracking_client.get_work_item(wid)
        return work_item.fields.get("KL.AutotestName", "")

    def get_results_xml(self):
        results_map = []
        if self.testpaths == "*":
            results_path = self.user_home_dir
        else:
            results_path = self.testpaths
        for path in Path(results_path).rglob("test-results-*.xml"):
            tests_results = {}
            tree = ET.parse(str(path))
            root = tree.getroot()
            for testsuites in root:
                for testcase in testsuites:
                    test_name = testcase.attrib["name"]
                    tests_results["name"] = test_name
                    if testcase.find("failure") is not None:
                        tests_results["result"] = "Failed"
                    else:
                        tests_results["result"] = "Passed"
            results_map.append(tests_results)
        return results_map

    def get_suites(self):
        suites = []
        test_suites_map = {"test_plan_id": self.test_plan_id}
        test_plan_client = self.connection.clients_v6_0.get_test_plan_client()
        test_suites = test_plan_client.get_test_suites_for_plan(self.project, self.test_plan_id)
        for s in test_suites:
            ts = {"name": s.name, "id": s.id}
            suites.append(ts)
            test_suites_map["test_suites"] = suites
        return test_suites_map

    def get_cases(self, test_suite_map):
        cases = []
        test_plan_client = self.connection.clients_v6_0.get_test_plan_client()
        for s in test_suite_map["test_suites"]:
            test_cases = test_plan_client.get_test_case_list(self.project, self.test_plan_id, s.get("id"))
            for c in test_cases:
                test_point = test_plan_client.get_points_list(self.project, self.test_plan_id, s.get("id"),
                                                              test_case_id=c.work_item.id)
                points = []
                for tp in test_point:
                    points.append(tp.id)
                tc = {"name": c.work_item.name, "id": c.work_item.id, "test_point_ids": points,
                      "autotest_name": self._get_autotest_name(c.work_item.id)}
                cases.append(tc)
        return cases

    def create_run_map(self, test_cases_map, results):
        run_map = []
        test_points = {}
        for tc in test_cases_map:
            for res in results:
                if tc["autotest_name"] == res["name"]:
                    test_points["id"] = tc["test_point_ids"]
                    test_points["name"] = res["name"]
                    test_points["result"] = res["result"]
        run_map.append(test_points)
        return run_map

    def create_test_run(self, test_name, test_point):
        test_client = self.connection.clients_v6_0.get_test_client()
        model = {"name": test_name + "_run", "plan": {"id": int(self.test_plan_id)}, "pointIds": test_point}
        test_run_id = test_client.create_test_run(model, self.project)
        return test_run_id.id

    def get_test_result_id(self, test_run_id):
        test_client = self.connection.clients_v6_0.get_test_client()
        test_result_id = test_client.get_test_results(self.project, test_run_id)
        for res in test_result_id:
            tr_id = res.id
        return tr_id

    def update_test_result(self, run_id, res_id, result):
        test_client = self.connection.clients_v6_0.get_test_client()
        payload = [{"id": res_id, "state": "Completed", "outcome": result}]
        test_client.update_test_results(payload, self.project, run_id)
