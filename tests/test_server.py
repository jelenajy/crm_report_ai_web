import json
from io import BytesIO
import unittest
from pathlib import Path

from server import make_handler


ROOT = Path(__file__).resolve().parents[1]


class ServerTests(unittest.TestCase):
    def request(self, path, payload=None):
        handler = object.__new__(make_handler(ROOT))
        handler.path = path
        handler.wfile = BytesIO()
        handler.rfile = BytesIO(payload or b"")
        handler.headers = {"Content-Length": str(len(payload or b"")), "Content-Type": "application/json"}
        handler.send_response = lambda status: setattr(handler, "status", status)
        handler.send_header = lambda *args: None
        handler.end_headers = lambda: None
        if payload is None:
            handler.do_GET()
        else:
            handler.do_POST()
        return handler.status, handler.wfile.getvalue()

    def test_status_and_answer_are_public_but_source_files_are_not(self):
        status, body = self.request("/api/reports")
        self.assertEqual(status, 200)
        statuses = json.loads(body)
        self.assertEqual(statuses["customer_type"], "ready")
        self.assertEqual(statuses["member_tier"], "pending")
        status, body = self.request("/api/answer", json.dumps(
            {"reportKey": "customer_type", "question": "购买频次如何计算？"}).encode())
        self.assertEqual(status, 200)
        answer = json.loads(body)
        self.assertEqual(answer["scope"], "specialized")
        self.assertNotIn("xlsx", str(answer).lower())
        status, body = self.request("/api/answer", json.dumps({
            "reportKey": "customer_type", "question": "二回的定义",
            "previousQuestion": "新客二回定义是什么"}).encode())
        self.assertEqual(status, 200)
        self.assertIn("两次及以上", json.loads(body)["conclusion"])
        for path in ("/客质月报_KPI字段定义文档_完整版.xlsx", "/指标别名mapping.csv",
                     "/README.md", "/.git/config"):
            self.assertEqual(self.request(path)[0], 404)

    def test_page_does_not_embed_knowledge_table_or_citations(self):
        status, body = self.request("/")
        self.assertEqual(status, 200)
        page = body.decode()
        self.assertNotIn("const knowledgeResponses", page)
        self.assertNotIn("查看知识依据", page)
        self.assertNotIn("routePatterns:", page)
        self.assertNotIn("citation-toggle", page)
        self.assertIn("/api/answer", page)
        self.assertIn("setKnowledgeIndicator(packageStatus !== 'ready', packageStatus)", page)
        self.assertIn("此指标的专属知识未接入", page)

    def test_file_opening_explains_why_answers_cannot_load(self):
        _, body = self.request("/")
        page = body.decode()
        self.assertIn("window.location.protocol === 'file:'", page)
        self.assertIn("请通过本地知识服务打开页面", page)


if __name__ == "__main__":
    unittest.main()
