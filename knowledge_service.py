"""Private, deliberately narrow KPI lookup over the approved workbooks."""

from pathlib import Path
from difflib import SequenceMatcher
import csv
import re
import xml.etree.ElementTree as ET
import zipfile


NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
GENERAL_FILE = "Diamond KPI Definition V2024.xlsx"
MAPPING_FILE = "报表类型_知识包名称mapping.xlsx"
ALIAS_FILE = "指标别名mapping.csv"
REPORT_KEYS = ("customer_type", "product", "member_tier", "binding", "nps")
NO_ANSWER = "当前知识包中未找到足够明确的口径或数据，暂时无法可靠回答。请补充具体指标和统计场景，或联系报表负责人维护知识包。"
FIELD_NAMES = {"sales": "销售额", "orders": "订单数", "customers": "客数", "qty": "件数"}


def read_rows(path):
    """Read the first worksheet using only the Python standard library."""
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in item.findall(".//m:t", NS))
                      for item in root.findall("m:si", NS)]
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in root.findall(".//m:sheetData/m:row", NS):
            values = {}
            for cell in row.findall("m:c", NS):
                column = re.match(r"[A-Z]+", cell.attrib["r"]).group()
                value = cell.find("m:v", NS)
                inline = cell.find("m:is", NS)
                if value is not None:
                    text = shared[int(value.text)] if cell.attrib.get("t") == "s" else value.text
                elif inline is not None:
                    text = "".join(t.text or "" for t in inline.findall(".//m:t", NS))
                else:
                    text = ""
                values[column] = (text or "").strip()
            rows.append(values)
        return rows


def clean(text):
    return re.sub(r"\s+", "", text or "").lower()


def query_focus(question):
    """Remove question phrasing, retaining KPI meaning for short-name checks."""
    focus = clean(question)
    focus = re.sub(r"请问|如何|怎么算|怎么|计算|定义|是什么意思|是什么|指什么|解释|口径|指标|kpi|"
                   r"今年|去年|ytd|mtd|r12|的|呢|啊|[?？!！。,.，]", "", focus)
    return focus


def valid_short_match(name, question):
    n = clean(name)
    return len(n) > 2 or query_focus(question) == n


def content_match(rows, question):
    """Match distinctive wording from an answerable explanation or definition."""
    ranked = []
    q = clean(question).replace("除以", "/").replace("÷", "/").replace("／", "/")
    has_year = bool(re.search(r"今年|去年|同比", question))
    for row in rows:
        if row.get("primary") is False:
            continue
        if not has_year and re.search(r"去年|同比$", row["name"]):
            continue
        evidence = row.get("explanation") or row.get("definition") or ""
        evidences = []
        if not re.search(r"\b(?:DIVIDE|CALCULATE|VAR|RETURN)\b|\[|\]", evidence, re.I):
            evidences.append(evidence.split("=", 1)[1] if "=" in evidence and plain_ratio(evidence) else evidence)
        divided = divide_parts(row.get("logic"))
        if divided:
            evidences.append("/".join(re.sub(r"(?:今年|去年)$", "", part) for part in divided))
        best = None
        for item in evidences:
            e = clean(item).replace("除以", "/").replace("÷", "/").replace("／", "/")
            if len(e) < 6:
                continue
            longest = SequenceMatcher(None, e, q).find_longest_match().size
            score = longest / len(e)
            if longest >= 6 and score >= 0.8:
                candidate = (score, longest)
                if best is None or candidate > best:
                    best = candidate
        if best:
            ranked.append((*best, row))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    if not ranked:
        return None
    if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < 0.1:
        return None
    return ranked[0][2]


def report_key(value):
    return re.sub(r"[\s-]+", "_", (value or "").strip().lower())


def safe_package_name(value):
    path = Path(value)
    return bool(value and path.name == value and value not in (".", "..")
                and path.suffix.lower() == ".xlsx" and not path.is_absolute())


def question_topic(question):
    match = re.search(r"(?:跟|与|和|关于)([\u4e00-\u9fffA-Za-z0-9]+?)相关", question)
    if match:
        return match.group(1)
    tail = question.split("报表")[-1]
    match = re.search(r"([\u4e00-\u9fffA-Za-z0-9]+?)相关", tail)
    return match.group(1).lstrip("在中有的") if match else None


def similarity(name, question):
    """Conservative name similarity; exact containment dominates fuzzy matching."""
    n, q = clean(name), clean(question)
    if len(n) < 2 or not valid_short_match(name, question):
        return 0.0
    if n in q:
        return 1.0 + len(n) / 1000
    # Compare nearby text windows so a one-character typo can still match.
    # Three shared consecutive characters are required before fuzzy scoring.
    longest = SequenceMatcher(None, n, q).find_longest_match().size
    if longest < 3:
        return 0.0
    windows = (q[start:start + size] for size in range(max(2, len(n) - 1), len(n) + 3)
               for start in range(max(0, len(q) - size + 1)))
    best_ratio = max((SequenceMatcher(None, n, window).ratio() for window in windows), default=0.0)
    return best_ratio * 0.7 + min(longest / len(n), 1) * 0.3


def plain_ratio(text):
    """Extract only a human-readable A/B expression, never raw DAX."""
    if not text or re.search(r"\b(?:DIVIDE|CALCULATE|VAR|RETURN)\b|\[|\]", text, re.I):
        return None
    expression = text.split("=", 1)[-1].strip()
    parts = [part.strip(" 。；;()（）") for part in expression.split("/")]
    if len(parts) != 2 or not all(parts) or any(len(part) > 80 for part in parts):
        return None
    return tuple(parts)


def divide_parts(logic):
    """Read a simple DIVIDE expression without forwarding raw DAX."""
    match = re.fullmatch(r"DIVIDE\(\s*([^(),\[\]]+?)\s*,\s*([^(),\[\]]+?)\s*\)",
                         (logic or "").strip(), re.I)
    return (match.group(1).strip(), match.group(2).strip()) if match else None


def readable_calculation(row):
    logic = (row.get("logic") or "").strip()
    divided = divide_parts(logic)
    if divided:
        return f"{divided[0]} ÷ {divided[1]}"
    ratio = plain_ratio(logic) or plain_ratio(row.get("explanation"))
    if ratio:
        return f"{ratio[0]} ÷ {ratio[1]}"
    difference = re.fullmatch(r"([^()\[\],=]+?)\s+-\s+([^()\[\],=]+)", logic)
    if difference:
        return f"{difference.group(1).strip()} − {difference.group(2).strip()}"
    field = re.fullmatch(r'CALCULATE\(sum\((\w+)\),\s*year_type="(TY|LY)"\)', logic, re.I)
    if field and field.group(1).lower() in FIELD_NAMES:
        period = "今年" if field.group(2).upper() == "TY" else "去年"
        return f"按{period}口径汇总{FIELD_NAMES[field.group(1).lower()]}"
    return None


def matched_rows(rows, question):
    q = clean(question)
    names = {clean(row["name"]) for row in rows
             if clean(row["name"]) in q and len(clean(row["name"])) >= 2
             and valid_short_match(row["name"], question)}
    # Two unrelated KPIs in one question require interpretation beyond a single definition.
    maximal = {name for name in names if not any(name != other and name in other for other in names)}
    if len(maximal) != 1:
        return []
    name = maximal.pop()
    return [row for row in rows if clean(row["name"]) == name]


def select_period(rows, question):
    """Resolve workbook rows that give separate MTD and YTD/R12 definitions."""
    if len(rows) < 2:
        return rows
    periods = re.findall(r"(?<![A-Z0-9])(?:MTD|YTD|R12)(?![A-Z0-9])", question.upper())
    if len(periods) != 1:
        return rows
    selected = [row for row in rows if periods[0] in row.get("period", "").upper()]
    return selected or rows


class KnowledgeService:
    def __init__(self, package_dir):
        package_dir = Path(package_dir).resolve()
        self.general = self._load_general(package_dir / GENERAL_FILE)
        self.mapping = self._load_mapping(package_dir / MAPPING_FILE)
        self.aliases = self._load_aliases(package_dir / ALIAS_FILE)
        self.package_counts = {}
        self.specialized = {}
        for key in REPORT_KEYS:
            entries, loaded = [], 0
            for filename in self.mapping.get(key, []):
                path = package_dir / filename
                if not safe_package_name(filename) or path.is_symlink() or not path.resolve().is_relative_to(package_dir):
                    continue
                rows = self._load_specialized(path)
                if rows:
                    loaded += 1
                    entries.extend(rows)
            self.specialized[key] = entries
            self.package_counts[key] = loaded

    @staticmethod
    def _load_mapping(path):
        result = {key: [] for key in REPORT_KEYS}
        if not path.is_file():
            return result
        try:
            rows = read_rows(path)
        except (zipfile.BadZipFile, ET.ParseError, KeyError, IndexError, ValueError):
            return result
        if not rows or rows[0].get("A") != "报表类型" or rows[0].get("B") != "专属知识包名称":
            return result
        for row in rows[1:]:
            key, filename = report_key(row.get("A")), row.get("B", "").strip()
            if key in result and filename and filename not in result[key]:
                result[key].append(filename)
        return result

    @staticmethod
    def _load_aliases(path):
        aliases = {key: {} for key in (*REPORT_KEYS, "general")}
        if not path.is_file() or path.is_symlink():
            return aliases
        try:
            with path.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                if reader.fieldnames != ["报表类型", "别名", "标准指标"]:
                    return aliases
                for row in reader:
                    scope = report_key(row.get("报表类型"))
                    alias, canonical = (row.get("别名") or "").strip(), (row.get("标准指标") or "").strip()
                    if scope in aliases and 2 <= len(clean(alias)) <= 100 and 2 <= len(clean(canonical)) <= 100:
                        aliases[scope].setdefault(clean(alias), canonical)
        except (OSError, UnicodeError, csv.Error):
            return {key: {} for key in (*REPORT_KEYS, "general")}
        return aliases

    def _expand_aliases(self, report_key, question):
        aliases = {**self.aliases["general"], **self.aliases[report_key]}
        normalized = re.sub(r"\s+", "", question)
        if not aliases:
            return normalized
        pattern = re.compile("|".join(re.escape(alias) for alias in sorted(aliases, key=len, reverse=True)), re.I)
        return pattern.sub(lambda match: aliases[match.group().lower()], normalized)

    @staticmethod
    def _load_general(path):
        if not path.is_file():
            return []
        try:
            rows = read_rows(path)
        except (zipfile.BadZipFile, ET.ParseError, KeyError, IndexError, ValueError):
            return []
        entries = []
        for row in rows[1:]:
            if not row.get("A") or not row.get("E"):
                continue
            for name in (row.get("A"), row.get("B")):
                if name:
                    entries.append({"name": name, "definition": row["E"],
                                    "period": row.get("D", ""), "primary": name == row.get("A"),
                                    "fields": dict(row)})
        return entries

    @staticmethod
    def _load_specialized(path):
        if not path.is_file():
            return []
        try:
            rows = read_rows(path)
        except (zipfile.BadZipFile, ET.ParseError, KeyError, IndexError, ValueError):
            return []
        if not rows:
            return []
        if rows[0].get("C") == "字段展示名" and rows[0].get("G") == "计算逻辑":
            return [{"name": row.get("C", ""), "logic": row.get("G", ""),
                     "explanation": row.get("H", ""), "technical": row.get("I", ""),
                     "cds_source": row.get("J", ""), "business_logic": row.get("K", ""),
                     "category": row.get("B", ""), "measure": row.get("D", ""),
                     "source_table": row.get("E", ""), "source_field": row.get("F", ""),
                     "sequence": row.get("A", ""),
                     "fields": {column: row.get(column, "") for column in rows[0]}}
                    for row in rows[1:] if row.get("C") and (row.get("G") or row.get("H"))]
        if rows[0].get("A") == "KPI_CN" and rows[0].get("E") == "Definition":
            return [{"name": row.get("A", ""), "logic": "", "explanation": row.get("E", ""),
                     "technical": "", "cds_source": "", "business_logic": "",
                     "fields": {column: row.get(column, "") for column in rows[0]}}
                    for row in rows[1:] if row.get("A") and row.get("E")]
        return []

    def statuses(self):
        result = {}
        for key in REPORT_KEYS:
            total, loaded = len(self.mapping.get(key, [])), self.package_counts[key]
            result[key] = "ready" if total and loaded == total else "partial" if loaded else "pending"
        return result

    @staticmethod
    def _technical_note(row):
        technical = row.get("technical", "")
        notes = []
        if "YTD/R12" in technical:
            notes.append("适用周期为 YTD/R12")
        if "MTD不显示" in technical:
            notes.append("MTD 不显示")
        if "差值而非比率" in technical:
            notes.append("这是差值而非比率")
        if "百分点" in technical and "差值" in technical:
            notes.append("差值单位为百分点")
        return "；".join(notes)

    def _specialized_answer(self, row, question, content_lookup=False):
        explanation = (row.get("explanation") or "").strip()
        if explanation.startswith("适用于") or re.search(
                r"\b(?:CALCULATE|DIVIDE|SUM|VAR|RETURN)\b|\[|\]", explanation, re.I):
            explanation = ""
        calculation = readable_calculation(row)
        if not explanation and not calculation:
            return None
        name = row["name"]
        asks_calculation = bool(re.search(r"如何计算|怎么算|计算方式|公式|口径", question))
        if calculation and asks_calculation:
            conclusion = f"{name}按{calculation}计算。"
            if explanation and clean(explanation) not in clean(conclusion):
                conclusion += f"{explanation}。"
        elif explanation:
            lead = "这个口径对应" if content_lookup else ""
            conclusion = f"{lead}“{name}”：{explanation}。" if lead else f"{name}：{explanation}。"
            if calculation and clean(calculation) not in clean(explanation):
                conclusion += f"计算口径为{calculation}。"
        else:
            conclusion = f"{name}按{calculation}计算。"
        note = self._technical_note(row)
        if note:
            conclusion += f"{note}。"
        return conclusion[:500]

    def _family_answer(self, report_key, question):
        focus = query_focus(question)
        if len(focus) < 4 or re.search(r"今年|去年|同比", question):
            return None
        variants = [row for row in self.specialized.get(report_key, [])
                    if clean(row["name"]).startswith(focus) and row["name"].endswith("今年")]
        if len(variants) < 2 or len(variants) > 5:
            return None
        if "MTD" in question.upper() and all("YTD/R12" in row.get("technical", "") for row in variants):
            detail = "；MTD 需按知识包说明通过 YTD 口径推导" if any(
                "MTD不直接计算" in row.get("business_logic", "") for row in variants) else ""
            return {"status": "no-answer", "conclusion":
                    f"当前报表的这些专属指标只标明适用 YTD/R12，不能直接给出 MTD 的计算口径{detail}。请指定要看的维度和周期。"}
        parts = []
        for row in variants:
            formula = readable_calculation(row)
            meaning = (row.get("explanation") or "").strip()
            if not meaning or not formula:
                return None
            parts.append(f"{row['name']}：{meaning}，按{formula}计算")
        note = "这两种口径的适用周期为 YTD/R12。" if all(
            "YTD/R12" in row.get("technical", "") for row in variants) else ""
        return {"status": "ok", "scope": "specialized", "conclusion":
                ("当前报表有不同的专属口径：" + "；".join(parts) + "。" + note)[:500]}

    def _new_repeat_overview(self):
        records = [row for row in self.general if row["name"] == "全渠道新客二回人数"]
        yearly = select_period(records, "YTD")
        monthly = select_period(records, "MTD")
        if len(yearly) != 1 or len(monthly) != 1:
            return None
        return ("“新客二回”有维度和周期之分。以全渠道为例："
                f"YTD/R12 口径为{yearly[0]['definition']}；"
                f"MTD 口径为{monthly[0]['definition']}。"
                "BA、柜台、渠道口径另有区别，请指定分析维度与周期。")

    def _new_repeat_period_overview(self, period):
        records = [row for row in self.general if row["name"] == "全渠道新客二回人数"]
        selected = select_period(records, period)
        if len(selected) != 1:
            return None
        return (f"“{period} 新客二回”需要区分统计维度。以全渠道新客二回人数为例，"
                f"{period} 口径为{selected[0]['definition']}。"
                "BA、柜台和单渠道另有对应口径；如果你指的是其中一种，请补充维度。")

    def _ratio_candidates(self, report_key, question):
        found = {}
        year_requested = bool(re.search(r"今年|去年", question))
        for scope, rows in (("specialized", self.specialized.get(report_key, [])),
                            ("general", self.general)):
            for row in rows:
                name = row["name"]
                if scope == "specialized" and not year_requested and name.endswith("去年"):
                    continue
                base = re.sub(r"(?:今年|去年)$", "", name)
                if len(clean(base)) < 2 or clean(base) not in clean(question):
                    continue
                definition = row.get("explanation") if scope == "specialized" else row.get("definition")
                ratio = plain_ratio(definition) or (divide_parts(row.get("logic")) if scope == "specialized" else None)
                if ratio and base not in found:
                    found[base] = (scope, base, ratio)
        return list(found.values())

    def _reasoned_answer(self, report_key, question):
        if "新客二回" in question and re.search(r"MTD|YTD", question, re.I) and re.search(r"区别|差别|不同|对比", question):
            overview = self._new_repeat_overview()
            if overview:
                return {"status": "ok", "scope": "general", "conclusion":
                        "这两个周期的统计条件不同。" + overview}
        if re.search(r"区别|差别|不同|对比", question):
            candidates = self._ratio_candidates(report_key, question)
            if len(candidates) == 2:
                first, second = candidates
                first_name, first_parts = first[1], first[2]
                second_name, second_parts = second[1], second[2]
                scope = "specialized" if first[0] == second[0] == "specialized" else "general"
                return {"status": "ok", "scope": scope, "conclusion":
                        f"两者都是比值，但计算的对象不同：{first_name}是{first_parts[0]} ÷ {first_parts[1]}；"
                        f"{second_name}是{second_parts[0]} ÷ {second_parts[1]}。比较时要先确认统计周期和客群一致。"}
        relation = re.search(r"关系|联系|影响", question)
        movement = re.search(r"下降|上升|降低|提高", question)
        if not relation and not movement:
            return None
        candidates = self._ratio_candidates(report_key, question)
        if relation and len(candidates) == 2:
            if "今年" in question and "去年" in question:
                return {"status": "no-answer", "conclusion":
                        "这两个指标指向不同年份，不能直接约去共同项。请先指定一致的统计周期，再比较它们的关系。"}
            first, second = candidates
            left, right = first[2], second[2]
            outer = (left[0], right[1]) if clean(left[1]) == clean(right[0]) else (
                (right[0], left[1]) if clean(right[1]) == clean(left[0]) else None)
            if outer:
                scope = "specialized" if first[0] == second[0] == "specialized" else "general"
                return {"status": "ok", "scope": scope, "conclusion":
                        f"按知识口径，{first[1]}={left[0]} ÷ {left[1]}，{second[1]}={right[0]} ÷ {right[1]}。"
                        f"两者相乘时，共同的{left[1] if clean(left[1]) == clean(right[0]) else right[1]}约掉，"
                        f"得到{outer[0]} ÷ {outer[1]}。这个推导要求统计周期、客群一致，且分母不为零。"}
        if relation and not candidates:
            for scope, rows in (("specialized", self.specialized.get(report_key, [])),
                                ("general", self.general)):
                for row in rows:
                    ratio = plain_ratio(row.get("explanation") if scope == "specialized" else row.get("definition"))
                    if not ratio and scope == "specialized":
                        ratio = divide_parts(row.get("logic"))
                    if scope == "specialized" and row["name"].endswith("去年") and "去年" not in question:
                        continue
                    if ratio and all(clean(re.sub(r"(?:今年|去年)$", "", part)) in clean(question)
                                     for part in ratio):
                        return {"status": "ok", "scope": scope, "conclusion":
                                f"这两个量在“{row['name']}”的口径中相连：{row['name']}={ratio[0]} ÷ {ratio[1]}。"
                                "仅凭口径无法判断当前数值或变化原因，还需要相同周期的数据。"}
        if not candidates:
            return None
        scope, name, (numerator, denominator) = candidates[0]
        formula = f"{name}按“{numerator} ÷ {denominator}”计算。"
        if movement:
            direction = "下降" if re.search(r"下降|降低", question) else "上升"
            relative = "变小" if direction == "下降" else "变大"
            return {"status": "ok", "scope": scope, "conclusion":
                    f"{formula}如果它{direction}，只能从口径推知分子相对分母{relative}；具体是哪项数据变化、为何变化，无法仅凭定义判断，需要核对同周期的{numerator}和{denominator}。"[:500]}
        other = next((item for item in (numerator, denominator)
                      if clean(item) in clean(question) and clean(item) != clean(name)), None)
        if other:
            position = "分子" if other == numerator else "分母"
            return {"status": "ok", "scope": scope, "conclusion":
                    f"{formula}{other}是这个比率的{position}。只看{other}的变化还不能确定比率如何变化，还要同时看另一项数据。"}
        return {"status": "ok", "scope": scope, "conclusion":
                f"{formula}当前知识口径没有给出它与问题中另一指标的直接计算关系，无法仅凭定义推断两者如何联动；需要同一周期的实际数据进一步分析。"}

    def answer(self, report_key, question, previous_question=None):
        if report_key not in REPORT_KEYS or not isinstance(question, str) or not question.strip() or len(question) > 500:
            raise ValueError("invalid question or report")
        if previous_question is not None and (not isinstance(previous_question, str) or len(previous_question) > 500):
            raise ValueError("invalid previous question")
        question = self._expand_aliases(report_key, question)
        if previous_question:
            previous_question = self._expand_aliases(report_key, previous_question)
        if re.search(r"预测|趋势|具体数据", question):
            return {"status": "no-answer", "conclusion": NO_ANSWER}
        if ("二回" in question and "新客" not in question
                and re.search(r"定义|是什么|指什么", question)
                and previous_question and "新客二回" in previous_question):
            question = "新客二回的定义是什么"
        specialized = self.specialized.get(report_key, [])
        if re.search(r"多少个|几个|哪些|列出|分别是什么", question) and re.search(r"相关|指标|KPI", question, re.I):
            topic = question_topic(question)
            full_inventory = not topic and re.search(r"所有|总共|共有|一共", question)
            if (topic or full_inventory) and specialized and self.statuses()[report_key] == "ready":
                names = sorted({row["name"] for row in specialized
                                if not topic or clean(topic) in clean(row["name"])})
                if names:
                    if full_inventory and not re.search(r"哪些|列出|分别是什么", question):
                        return {"status": "ok", "scope": "specialized", "conclusion":
                                f"按当前报表专属知识中的字段展示名去重，共有 {len(names)} 个 KPI 条目。"}
                    label = f"跟“{topic}”相关的 KPI" if topic else "KPI"
                    listed = "、".join(names[:10])
                    remainder = f"等（这里只列出前 10 个）" if len(names) > 10 else ""
                    return {"status": "ok", "scope": "specialized", "conclusion":
                            f"在当前报表已接入的专属知识中，{label} 共 {len(names)} 个：{listed}{remainder}。"[:500]}
            return {"status": "no-answer", "conclusion":
                    "暂时无法可靠统计这类 KPI：请说明要统计的指标主题，并确认当前报表的专属知识包已完整接入。"}
        if re.search(r"是多少|有多少", question):
            return {"status": "no-answer", "conclusion": NO_ANSWER}
        reasoned = self._reasoned_answer(report_key, question)
        if reasoned:
            return reasoned
        if re.search(r"为什么|原因|下降|上升", question):
            return {"status": "no-answer", "conclusion": NO_ANSWER}
        periods = re.findall(r"(?<![A-Z0-9])(?:MTD|YTD|R12)(?![A-Z0-9])", question.upper())
        if ("新客二回" in question and len(periods) == 1
                and not re.search(r"率|基数|BA|柜台|渠道|产品|会员等级|会员层级|绑定|NPS", question, re.I)):
            overview = self._new_repeat_period_overview(periods[0])
            if overview:
                return {"status": "ok", "scope": "general", "conclusion": overview[:500]}
        if "新客二回" in question and not re.search(
                r"率|基数|人数|BA|柜台|渠道|MTD|YTD|R12|产品|会员等级|会员层级|绑定|NPS", question, re.I):
            overview = self._new_repeat_overview()
            if overview:
                return {"status": "ok", "scope": "general", "conclusion": overview[:500]}
        family = self._family_answer(report_key, question)
        if family:
            return family
        content_intent = bool(re.search(r"哪个指标|什么指标|对应哪个KPI", question, re.I))
        formula_lookup = content_intent and ("/" in question or "除以" in question)
        content_row = content_match(specialized, question) if content_intent else None
        exact = [content_row] if content_row else ([] if formula_lookup else matched_rows(specialized, question))
        specialized_content = bool(content_row)
        if not exact and not formula_lookup:
            ranked = sorted(((similarity(row["name"], question), row) for row in specialized),
                            key=lambda pair: pair[0], reverse=True)
            if ranked and ranked[0][0] >= 0.72 and (len(ranked) == 1 or ranked[0][0] - ranked[1][0] >= 0.06):
                exact = [ranked[0][1]]
        if not exact and specialized and not formula_lookup:
            # Questions without a year may refer to the current-year field.
            base = [row for row in specialized if row["name"].endswith("今年")]
            exact = [row for row in base if query_focus(question) == clean(row["name"][:-2])]
        if not exact:
            content_row = content_match(specialized, question)
            if content_row:
                exact = [content_row]
                specialized_content = True
        if len(exact) == 1:
            if "MTD" in question.upper() and "YTD/R12" in exact[0].get("technical", ""):
                return {"status": "no-answer", "conclusion":
                        "当前专属知识将这个指标标为仅适用 YTD/R12，未给出可直接采用的 MTD 口径。请确认统计周期。"}
            conclusion = self._specialized_answer(exact[0], question, specialized_content)
            if conclusion:
                return {"status": "ok", "scope": "specialized", "conclusion": conclusion}
        content_row = content_match(self.general, question) if content_intent else None
        general = [content_row] if content_row else ([] if formula_lookup else matched_rows(self.general, question))
        general_content = bool(content_row)
        if not general and not formula_lookup:
            ranked = sorted(((similarity(row["name"], question), row) for row in self.general),
                            key=lambda pair: pair[0], reverse=True)
            if ranked and ranked[0][0] >= 0.72:
                best = ranked[0][0]
                candidate_names = {row["name"] for score, row in ranked if best - score < 0.06}
                if len(candidate_names) == 1:
                    general = [row for row in self.general if row["name"] in candidate_names]
        if not general:
            content_row = content_match(self.general, question)
            if content_row:
                general = [content_row]
                general_content = True
        general = select_period(general, question)
        if "新客二回" in question and len(general) == 1 and general[0]["name"] == "新客":
            general = []
        if len(general) == 1 and any(
            qualifier.lower() in question.lower() and qualifier.lower() not in general[0]["name"].lower()
            for qualifier in ("产品", "会员等级", "会员层级", "绑定", "NPS")
        ):
            general = []
        if len(general) == 1 and ("同比" not in question or "同比" in general[0]["name"]):
            conclusion = (f"这个口径对应“{general[0]['name']}”：{general[0]['definition']}"
                          if general_content else general[0]["definition"])
            return {"status": "ok", "scope": "general", "conclusion": conclusion[:500]}
        return {"status": "no-answer", "conclusion": NO_ANSWER}
