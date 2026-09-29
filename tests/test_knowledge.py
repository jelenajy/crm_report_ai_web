import tempfile
import unittest
from pathlib import Path

from knowledge_service import KnowledgeService


ROOT = Path(__file__).resolve().parents[1]
CUSTOMER_FILE = "客质月报_KPI字段定义文档_完整版.xlsx"


class KnowledgeServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = KnowledgeService(ROOT)

    def test_specialized_definition_wins_for_customer_type(self):
        answer = self.service.answer("customer_type", "购买频次如何计算？")
        self.assertEqual(answer["status"], "ok")
        self.assertEqual(answer["scope"], "specialized")
        self.assertIn("订单数", answer["conclusion"])
        self.assertIn("客数", answer["conclusion"])
        self.assertIn("平均", answer["conclusion"])
        self.assertNotIn("02_Customer", str(answer))

    def test_complete_customer_workbook_keeps_all_columns_server_side(self):
        row = next(row for row in self.service.specialized["customer_type"]
                   if row["name"] == "购买频次今年")
        self.assertEqual(set(row["fields"]), set("ABCDEFGHIJK"))
        self.assertEqual(row["fields"]["C"], "购买频次今年")
        self.assertEqual(row["fields"]["D"], "购买频次今年")
        self.assertIn("02_Customer", row["fields"]["E"])
        self.assertIn("orders", row["fields"]["F"])
        self.assertIn("DIVIDE", row["fields"]["G"])
        self.assertIn("平均每个客户", row["fields"]["H"])
        self.assertIn("订单数除以客数", row["fields"]["I"])
        self.assertIn("【计算公式】", row["fields"]["J"])
        self.assertIn("【业务价值】", row["fields"]["K"])
        self.assertIn("【计算逻辑】", next(x for x in self.service.specialized["customer_type"]
                                        if x["name"].startswith("新客二回率(Channel to Brand)"))["fields"]["J"])
        answer = self.service.answer("customer_type", "购买频次今年怎么算？")
        self.assertNotIn("fields", answer)
        self.assertNotIn("DIVIDE", str(answer))

    def test_generic_fallback_does_not_mark_unconnected_package_ready(self):
        answer = self.service.answer("member_tier", "购买频次如何计算？")
        self.assertEqual(answer["status"], "ok")
        self.assertEqual(answer["scope"], "general")
        self.assertEqual(self.service.statuses()["member_tier"], "pending")

    def test_common_english_alias_can_match(self):
        answer = self.service.answer("member_tier", "FRQ 如何计算？")
        self.assertEqual(answer["status"], "ok")
        self.assertEqual(answer["scope"], "general")
        self.assertIn("总订单数", answer["conclusion"])

    def test_new_repeat_broad_question_explains_scope_and_period(self):
        answer = self.service.answer("customer_type", "新客二回的定义是什么？")
        self.assertEqual(answer["status"], "ok")
        self.assertEqual(answer["scope"], "general")
        for term in ("全渠道", "YTD", "MTD", "两次及以上", "首次二回"):
            self.assertIn(term, answer["conclusion"])
        self.assertNotIn("品牌第一笔订单", answer["conclusion"])

    def test_new_repeat_follow_up_uses_only_relevant_previous_question(self):
        answer = self.service.answer(
            "customer_type", "不对吧，我问的是二回的定义",
            previous_question="新客二回定义是什么")
        self.assertEqual(answer["status"], "ok")
        self.assertIn("两次及以上", answer["conclusion"])
        unrelated = self.service.answer(
            "customer_type", "二回的定义", previous_question="购买频次如何计算")
        self.assertEqual(unrelated["status"], "no-answer")

    def test_new_repeat_rate_uses_formula_instead_of_applicability_note(self):
        answer = self.service.answer("customer_type", "新客二回率如何计算？")
        self.assertEqual(answer["status"], "ok")
        self.assertEqual(answer["scope"], "specialized")
        self.assertIn("Channel to Brand", answer["conclusion"])
        self.assertIn("Channel to Channel", answer["conclusion"])
        self.assertIn("新客数", answer["conclusion"])
        self.assertNotIn("customer_type_code", answer["conclusion"])

    def test_new_customer_package_applicability_is_respected(self):
        answer = self.service.answer("customer_type", "MTD新客二回率如何计算？")
        self.assertEqual(answer["status"], "no-answer")
        self.assertIn("YTD/R12", answer["conclusion"])
        self.assertIn("MTD", answer["conclusion"])

    def test_new_repeat_period_selects_only_corresponding_definition(self):
        monthly = self.service.answer("customer_type", "全渠道新客二回人数 MTD 如何定义？")
        yearly = self.service.answer("customer_type", "全渠道新客二回人数 YTD 如何定义？")
        self.assertIn("首次二回", monthly["conclusion"])
        self.assertIn("两次及以上", yearly["conclusion"])
        compact = self.service.answer("customer_type", "全渠道新客二回人数MTD定义")
        self.assertIn("首次二回", compact["conclusion"])

    def test_short_new_repeat_period_question_gets_bounded_overview(self):
        yearly = self.service.answer("customer_type", "ytd新客二回")
        self.assertEqual(yearly["status"], "ok")
        self.assertEqual(yearly["scope"], "general")
        self.assertIn("全渠道", yearly["conclusion"])
        self.assertIn("两次及以上", yearly["conclusion"])
        self.assertIn("维度", yearly["conclusion"])
        self.assertNotIn("首次二回", yearly["conclusion"])
        monthly = self.service.answer("customer_type", "MTD 新客二回")
        self.assertIn("首次二回", monthly["conclusion"])
        self.assertNotIn("两次及以上", monthly["conclusion"])

    def test_kpi_paraphrases_use_same_grounded_retrieval(self):
        broad = self.service.answer("customer_type", "新客第二次购买是什么意思？")
        self.assertEqual(broad["status"], "ok")
        self.assertEqual(broad["scope"], "general")
        self.assertIn("两次及以上", broad["conclusion"])
        self.assertNotIn("品牌第一笔订单", broad["conclusion"])
        rate = self.service.answer("customer_type", "新客第二次购买率怎么算？")
        self.assertEqual(rate["status"], "ok")
        self.assertEqual(rate["scope"], "specialized")
        self.assertIn("Channel to Brand", rate["conclusion"])
        period = self.service.answer("customer_type", "YTD 新客第二次购买")
        self.assertIn("两次及以上", period["conclusion"])
        self.assertNotIn("首次二回", period["conclusion"])
        unknown = self.service.answer("customer_type", "新客第三次购买是什么意思？")
        self.assertEqual(unknown["status"], "no-answer")
        qualified = self.service.answer("product", "产品新客第二次购买如何定义？")
        self.assertEqual(qualified["status"], "no-answer")

    def test_description_evidence_can_identify_kpi_without_name(self):
        answer = self.service.answer("member_tier", "统计时间内活跃客人产生的总订单数/总客数是什么指标？")
        self.assertEqual(answer["status"], "ok")
        self.assertEqual(answer["scope"], "general")
        self.assertIn("总订单数/总客数", answer["conclusion"])
        customer = self.service.answer("customer_type", "统计时间内活跃客人产生的总订单数/总客数是什么指标？")
        self.assertEqual(customer["status"], "ok")
        self.assertEqual(customer["scope"], "general")
        self.assertIn("购买频次", customer["conclusion"])
        specialized = self.service.answer("customer_type", "订单数/客数对应哪个指标？")
        self.assertEqual(specialized["status"], "ok")
        self.assertEqual(specialized["scope"], "specialized")
        self.assertIn("购买频次", specialized["conclusion"])
        spoken = self.service.answer("customer_type", "订单数除以客数对应哪个指标？")
        self.assertEqual(spoken["scope"], "specialized")
        self.assertIn("购买频次", spoken["conclusion"])

    def test_no_cross_specialized_search(self):
        self.service.specialized["member_tier"] = [{"name": "购买频次今年", "logic": "", "explanation": "会员等级专属定义"}]
        answer = self.service.answer("member_tier", "购买频次今年如何计算？")
        self.assertIn("会员等级专属定义", answer["conclusion"])
        other = self.service.answer("product", "购买频次今年如何计算？")
        self.assertNotEqual(other.get("conclusion"), "会员等级专属定义")
        customer = self.service.answer("customer_type", "购买频次今年如何计算？")
        self.assertNotEqual(customer.get("conclusion"), "会员等级专属定义")

    def test_unknown_or_ambiguous_question_does_not_invent_answer(self):
        self.assertEqual(self.service.answer("customer_type", "退款订单如何处理？")["status"], "no-answer")
        self.assertEqual(self.service.answer("customer_type", "销售额和订单数的关系？")["status"], "ok")
        movement = self.service.answer("customer_type", "为什么购买频次下降？")
        self.assertEqual(movement["status"], "ok")
        self.assertIn("订单数", movement["conclusion"])
        self.assertIn("客数", movement["conclusion"])
        self.assertIn("无法", movement["conclusion"])
        self.assertEqual(self.service.answer("product", "产品新客如何定义？")["status"], "no-answer")
        self.assertEqual(self.service.answer("product", "产品销售额如何计算？")["status"], "no-answer")

    def test_grounded_relation_and_period_comparison(self):
        relation = self.service.answer("customer_type", "新客二回率和新客二回人数有什么关系？")
        self.assertEqual(relation["status"], "ok")
        self.assertIn("新客二回人数", relation["conclusion"])
        self.assertIn("新客二回基数", relation["conclusion"])
        self.assertIn("分子", relation["conclusion"])
        comparison = self.service.answer("customer_type", "MTD 和 YTD 的新客二回人数有什么区别？")
        self.assertEqual(comparison["status"], "ok")
        self.assertIn("首次二回", comparison["conclusion"])
        self.assertIn("两次及以上", comparison["conclusion"])
        contrast = self.service.answer("customer_type", "客单价和购买频次有什么区别？")
        self.assertEqual(contrast["status"], "ok")
        self.assertIn("销售额", contrast["conclusion"])
        self.assertIn("订单数", contrast["conclusion"])
        self.assertIn("客数", contrast["conclusion"])
        composed = self.service.answer("customer_type", "客单价和购买频次有什么关系？")
        self.assertEqual(composed["status"], "ok")
        self.assertIn("相乘", composed["conclusion"])
        self.assertIn("销售额今年 ÷ 客数今年", composed["conclusion"])
        direct = self.service.answer("customer_type", "销售额和订单数是什么关系？")
        self.assertEqual(direct["status"], "ok")
        self.assertIn("客单价", direct["conclusion"])
        mixed_years = self.service.answer("customer_type", "客单价今年和购买频次去年有什么关系？")
        self.assertEqual(mixed_years["status"], "no-answer")

    def test_missing_specialized_file_keeps_pending_and_uses_general_only(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "Diamond KPI Definition V2024.xlsx").write_bytes(
                (ROOT / "Diamond KPI Definition V2024.xlsx").read_bytes()
            )
            Path(directory, "报表类型_知识包名称mapping.xlsx").write_bytes(
                (ROOT / "报表类型_知识包名称mapping.xlsx").read_bytes()
            )
            service = KnowledgeService(Path(directory))
            self.assertEqual(service.statuses()["customer_type"], "pending")
            self.assertEqual(service.answer("customer_type", "购买频次如何计算？")["scope"], "general")

    def test_invalid_specialized_file_is_not_reported_as_connected(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "报表类型_知识包名称mapping.xlsx").write_bytes(
                (ROOT / "报表类型_知识包名称mapping.xlsx").read_bytes()
            )
            Path(directory, CUSTOMER_FILE).write_bytes(b"invalid")
            service = KnowledgeService(Path(directory))
            self.assertEqual(service.statuses()["customer_type"], "pending")
            self.assertEqual(service.answer("customer_type", "购买频次如何计算？")["status"], "no-answer")

    def test_no_source_document_or_raw_formula_in_public_response(self):
        answer = self.service.answer("customer_type", "销售额今年如何计算？")
        self.assertEqual(answer["status"], "ok")
        self.assertNotIn("filename", answer)
        self.assertNotIn("citation", answer)
        self.assertNotIn("CALCULATE", str(answer))

    def test_mapping_is_loaded_and_related_kpis_are_counted(self):
        self.assertEqual(self.service.mapping["customer_type"], [CUSTOMER_FILE])
        answer = self.service.answer("customer_type", "customer type 报表共有多少个跟新客二回相关的kpi？")
        self.assertEqual(answer["status"], "ok")
        self.assertEqual(answer["scope"], "specialized")
        self.assertIn("4", answer["conclusion"])
        self.assertIn("新客二回率(Channel to Brand)今年", answer["conclusion"])
        self.assertIn("新客二回率去年", answer["conclusion"])
        self.assertNotIn(".xlsx", str(answer))
        alternate = self.service.answer("customer_type", "新客二回相关的 KPI 有哪些？")
        self.assertEqual(alternate["scope"], "specialized")
        self.assertIn("4", alternate["conclusion"])
        total = self.service.answer("customer_type", "这个报表共有多少个 KPI？")
        self.assertEqual(total["scope"], "specialized")
        self.assertIn("共", total["conclusion"])

    def test_multi_package_mapping_and_missing_package_status(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for name in ("Diamond KPI Definition V2024.xlsx", CUSTOMER_FILE):
                (folder / name).write_bytes((ROOT / name).read_bytes())
            from tests.xlsx_fixture import write_mapping
            write_mapping(folder / "报表类型_知识包名称mapping.xlsx", [
                ("customer type", CUSTOMER_FILE),
                ("customer type", "missing.xlsx"),
                ("customer type", CUSTOMER_FILE),
                ("member tier", "../" + CUSTOMER_FILE),
            ])
            service = KnowledgeService(folder)
            self.assertEqual(service.statuses()["customer_type"], "partial")
            self.assertEqual(service.statuses()["member_tier"], "pending")
            self.assertEqual(len(service.mapping["customer_type"]), 2)

    def test_similar_name_and_uncertain_question(self):
        answer = self.service.answer("customer_type", "购买频次今年怎么算")
        self.assertEqual(answer["scope"], "specialized")
        typo = self.service.answer("member_tier", "购买频数如何计算？")
        self.assertEqual(typo["scope"], "general")
        self.assertIn("总订单数", typo["conclusion"])
        self.assertEqual(self.service.answer("customer_type", "一个毫无关联的神秘指标是什么")["status"], "no-answer")

    def test_multiple_mapped_packages_search_only_selected_report(self):
        from tests.xlsx_fixture import write_definition, write_mapping
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            write_mapping(folder / "报表类型_知识包名称mapping.xlsx", [
                ("customer type", "first.xlsx"), ("customer type", "second.xlsx"),
                ("member tier", "other.xlsx")])
            write_definition(folder / "first.xlsx", [("复购率", "首包的口径")])
            write_definition(folder / "second.xlsx", [("新客二回人数", "第二包的口径")])
            write_definition(folder / "other.xlsx", [("新客二回人数", "其他报表的口径")])
            service = KnowledgeService(folder)
            self.assertEqual(service.statuses()["customer_type"], "ready")
            answer = service.answer("customer_type", "新客二回人数的定义是什么？")
            self.assertIn("第二包的口径", answer["conclusion"])
            self.assertNotIn("其他报表", str(answer))
            self.assertNotIn(".xlsx", str(answer))

    def test_future_report_alias_is_data_driven_and_scope_limited(self):
        from tests.xlsx_fixture import write_definition, write_mapping
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            write_mapping(folder / "报表类型_知识包名称mapping.xlsx", [
                ("member tier", "tier.xlsx"), ("customer type", "customer.xlsx")])
            write_definition(folder / "tier.xlsx", [("回访占比", "会员等级回访口径")])
            write_definition(folder / "customer.xlsx", [("购买频次", "订单数/客数")])
            (folder / "指标别名mapping.csv").write_text(
                "报表类型,别名,标准指标\nmember tier,顾客回访比例,回访占比\n", encoding="utf-8")
            service = KnowledgeService(folder)
            member = service.answer("member_tier", "顾客回访比例是什么？")
            self.assertEqual(member["status"], "ok")
            self.assertIn("会员等级回访口径", member["conclusion"])
            customer = service.answer("customer_type", "顾客回访比例是什么？")
            self.assertEqual(customer["status"], "no-answer")


if __name__ == "__main__":
    unittest.main()
