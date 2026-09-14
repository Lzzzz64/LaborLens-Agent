# 劳动法智能分析 Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 2 至 3 周内交付一个可运行、可追溯、可评测的劳动合同与用工经历分析 Demo，完整跑通合同审查和试用期辞退两条演示流程。

**Architecture:** 使用 Docker Compose 编排 React、FastAPI、MySQL 和 Chroma。后端以单个 LangGraph 状态机串联输入解析、事实抽取、紧急筛查、动态追问、混合检索、规则判断、模型判断、引用校验和报告生成；所有模型、OCR、检索器与规则实现均通过接口解耦，以便测试替身、失败降级和供应商替换。

**Tech Stack:** React、TypeScript、Vite、FastAPI、Pydantic、SQLAlchemy、Alembic、LangGraph、Chroma、MySQL、PyMuPDF、PaddleOCR 或兼容 OCR 适配器、OpenAI 兼容模型接口、pytest、Vitest、Playwright、Docker Compose

**Spec:** `劳动法智能分析Agent项目需求文档.docx`

## Global Constraints

- 项目周期：2 至 3 周。
- 服务对象：中国大陆普通劳动者；杭州仅作为地方规则试点，不承诺覆盖全国地方政策。
- 第一版只使用一个 LangGraph 工作流，不采用多 Agent。
- 动态追问最多三轮，每轮不超过三个最影响结论的问题；用户跳过后仍生成有限结论。
- 输入支持文本型 PDF、扫描 PDF、常见合同图片和自然语言经历描述。
- OCR 对金额、日期和否定词保留置信度，并允许用户看到解析状态。
- 每项法律判断必须回溯到规则版本、检索记录或法律来源片段。
- 模型不得引用检索结果中不存在的法条；无依据、来源状态不明或规则与模型冲突时输出“待核实”或“无法判断”。
- 报告必须明确区分规则判断与模型判断，并包含事实、推断、限制、证据缺口和行动建议。
- 模型、OCR 或检索失败时自动重试；仍失败则明确报错、保留用户输入且不生成伪造结果。
- 原始上传文件只存临时目录，在成功、失败终止或超时清理后删除，不写入 MySQL。
- 固定知识库、测试集、模型配置、提示词和规则版本，确保评测可复现。
- Docker 环境下一条命令启动 React、FastAPI、MySQL 和 Chroma；耗时流程必须显示进度。
- 第一版不提供律师服务、不生成正式法律文书、不解析聊天记录/录音/银行流水、不实现账户支付后台，也不自动联系外部主体。
- 每次开发、修改、修复、优化、调整配置、修改测试或文档后，必须在完成必要验证之后向项目根目录的 `WORKLOG.md` 追加一条独立工作记录；未更新工作日志时，该任务不得视为完成。

## Local Python Environment

- 本地开发统一使用 Anaconda 环境 `labor_lens`，Python 版本固定为 3.12；不得在 Anaconda `base` 环境中安装项目依赖。
- 首次创建和安装：

```powershell
conda create -n labor_lens python=3.12 pip -y
conda activate labor_lens
python -m pip install -e backend
```

- 本地运行后端测试：

```powershell
conda activate labor_lens
Set-Location backend
python -m pytest -q
```

- Docker 容器仍是迁移、服务集成和最终验收的标准环境；本地环境用于快速开发与单元测试。

## Mandatory Work Log

以下规则适用于本计划中的每个任务和所有临时追加任务，无论改动规模大小：

1. 完成用户要求所对应的文件修改。
2. 执行与改动风险相匹配的测试、构建、运行或静态检查。
3. 获取执行当时的本地时间，格式为 `YYYY-MM-DD HH:mm`。
4. 在项目根目录的 `WORKLOG.md` 末尾追加一条新记录，不得覆盖、修改或删除已有记录。
5. 工作记录至少包含用户要求、实际工作内容、主要涉及文件、验证结果和备注。
6. 如果未执行某类验证，必须在“验证结果”中明确写明未执行及原因。
7. 如果只是分析、解释或回答问题，没有修改任何项目文件，则不写工作日志。
8. 每个任务的提交步骤必须同时包含该任务修改的文件和 `WORKLOG.md`。

每次追加使用以下格式：

```markdown
### YYYY-MM-DD HH:mm

- **用户要求**：简要记录本次用户提出的需求。
- **工作内容**：记录本次实际完成的修改。
- **涉及文件**：列出主要新增或修改的文件。
- **验证结果**：记录测试、构建、运行或检查结果；若未执行验证，明确说明原因。
- **备注**：记录未解决问题、后续事项或重要技术决策；没有则填写“无”。
```

因此，每项任务的完整结束顺序固定为：

```text
完成用户要求 → 完成必要验证 → 追加 WORKLOG.md → 提交本次改动
```

---

## File Structure

```text
.
├── .env.example                         # 所有服务的非敏感配置样例
├── compose.yaml                         # 四项服务、健康检查、数据卷与初始化顺序
├── Makefile                             # up、test、eval、seed、demo-check 统一命令
├── README.md                            # 问题、边界、架构、运行、评测、限制和演示
├── WORKLOG.md                           # 按任务追加的修改内容、涉及文件与验证记录
├── docs/
│   ├── architecture.md                  # 组件、时序、数据流和失败降级图
│   └── demo-script.md                   # 两条三分钟演示脚本
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── migrations/                      # MySQL 模式版本
│   ├── app/
│   │   ├── main.py                      # FastAPI 装配与生命周期
│   │   ├── config.py                    # 类型化环境配置
│   │   ├── api/cases.py                 # 案件、文档、消息、分析和报告接口
│   │   ├── api/evaluations.py           # 评测启动与结果接口
│   │   ├── domain/models.py             # Pydantic 事实、风险、引用和报告契约
│   │   ├── db/models.py                 # SQLAlchemy 持久化模型
│   │   ├── db/repositories.py           # 案件与评测仓储
│   │   ├── services/documents.py        # PDF/图片解析、OCR 与临时文件清理
│   │   ├── services/facts.py            # 事实抽取、合并和缺口分析
│   │   ├── services/urgent_rules.py      # 时效、通知、离职、签字紧急规则
│   │   ├── services/retrieval.py         # 关键词+向量召回、过滤、重排和轨迹
│   │   ├── services/risk_rules.py        # 期限、比例、必备项确定性规则
│   │   ├── services/model_client.py      # OpenAI 兼容模型适配、重试与结构化输出
│   │   ├── services/citation_guard.py    # 引用白名单、有效性和支持关系校验
│   │   ├── services/reporting.py         # 固定报告结构与 PDF 导出
│   │   ├── workflow/state.py             # LangGraph 状态契约
│   │   └── workflow/graph.py             # 节点、条件边和失败状态
│   ├── scripts/build_knowledge.py        # 法律材料切分、嵌入和 Chroma 入库
│   ├── scripts/run_evaluation.py         # 固定数据集批量评测
│   └── tests/                            # 单元、契约、集成和 API 测试
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── src/api/client.ts                 # 与后端契约一致的 API 客户端
│   ├── src/pages/HomePage.tsx            # 两个任务入口与能力边界
│   ├── src/pages/CaseWorkspace.tsx       # 上传、描述、追问、解析与进度
│   ├── src/pages/ReportPage.tsx           # 风险、引用、证据、话术和导出
│   ├── src/pages/EvaluationPage.tsx       # 指标、版本和失败样本
│   └── src/**/*.test.tsx                 # 组件与页面行为测试
├── knowledge/
│   ├── sources/                          # 人工确认的官方资料原文
│   ├── manifest.json                     # 来源元数据和知识库版本
│   └── fixtures/retrieval_queries.json   # 冻结前召回验证查询
└── evaluations/
    ├── dataset.v1.jsonl                  # 20 至 30 个虚构标注案例
    ├── schema.json                       # 样本格式约束
    └── expected_metrics.json             # 指标名称、计算口径和最低门槛
```

### Task 1: 建立可启动的项目骨架

**Files:**
- Create: `compose.yaml`, `.env.example`, `Makefile`, `backend/Dockerfile`, `backend/pyproject.toml`, `backend/app/main.py`, `backend/app/config.py`, `frontend/Dockerfile`, `frontend/package.json`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Consumes: 无。
- Produces: `GET /health -> {"status":"ok","mysql":"ok","chroma":"ok"}`；Compose 服务名固定为 `frontend`、`backend`、`mysql`、`chroma`。

- [ ] **Step 1: 写失败的健康检查测试**

```python
from fastapi.testclient import TestClient
from app.main import app

def test_health_reports_dependencies(monkeypatch):
    monkeypatch.setattr("app.main.check_mysql", lambda: True)
    monkeypatch.setattr("app.main.check_chroma", lambda: True)
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mysql": "ok", "chroma": "ok"}
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `docker compose run --rm backend pytest tests/test_health.py -q`

Expected: FAIL，提示 `app.main` 或 `/health` 尚不存在。

- [ ] **Step 3: 实现最小 FastAPI 应用与四服务编排**

```python
from fastapi import FastAPI

app = FastAPI(title="Labor Law Analysis Agent")

def check_mysql() -> bool:
    return True

def check_chroma() -> bool:
    return True

@app.get("/health")
def health() -> dict[str, str]:
    mysql_ok, chroma_ok = check_mysql(), check_chroma()
    return {
        "status": "ok" if mysql_ok and chroma_ok else "degraded",
        "mysql": "ok" if mysql_ok else "error",
        "chroma": "ok" if chroma_ok else "error",
    }
```

在 `compose.yaml` 中固定健康检查和依赖顺序；`.env.example` 只保留 `DATABASE_URL`、`CHROMA_URL`、`MODEL_BASE_URL`、`MODEL_NAME`、`MODEL_API_KEY`、`UPLOAD_TTL_MINUTES=30`。

- [ ] **Step 4: 验证测试和服务启动**

Run: `docker compose up -d --build`

Run: `docker compose run --rm backend pytest tests/test_health.py -q`

Expected: 四个容器健康，测试 PASS。

- [ ] **Step 5: 提交骨架**

```bash
git add compose.yaml .env.example Makefile backend frontend
git commit -m "build: scaffold labor law analysis services"
```

### Task 2: 定义领域契约和 MySQL 持久化

**Files:**
- Create: `backend/app/domain/models.py`, `backend/app/db/models.py`, `backend/app/db/repositories.py`, `backend/migrations/versions/001_initial.py`
- Test: `backend/tests/domain/test_models.py`, `backend/tests/db/test_case_repository.py`

**Interfaces:**
- Consumes: `DATABASE_URL`。
- Produces: `CaseFacts`、`QuestionRound`、`UrgentFlag`、`Citation`、`RiskFinding`、`FinalReport`；`CaseRepository.create(kind, goal) -> CaseRecord` 与 `CaseRepository.save_analysis(case_id, state) -> None`。

- [ ] **Step 1: 写领域约束测试**

```python
import pytest
from pydantic import ValidationError
from app.domain.models import QuestionRound, RiskFinding

def test_question_round_rejects_more_than_three_questions():
    with pytest.raises(ValidationError):
        QuestionRound(round_no=1, questions=["a", "b", "c", "d"])

def test_high_risk_requires_support_or_becomes_unverified():
    finding = RiskFinding.model_validate({
        "title": "试用期解除风险", "level": "high", "decision_type": "model",
        "conclusion": "可能违法", "confidence": 0.7, "citation_ids": []
    })
    assert finding.level == "unverified"
```

- [ ] **Step 2: 运行领域测试并确认失败**

Run: `docker compose run --rm backend pytest tests/domain/test_models.py -q`

Expected: FAIL，提示领域模型不存在。

- [ ] **Step 3: 实现严格枚举和字段模型**

```python
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class QuestionRound(BaseModel):
    round_no: int = Field(ge=1, le=3)
    questions: list[str] = Field(max_length=3)
    answers: list[str | None] = []

class RiskFinding(BaseModel):
    title: str
    level: Literal["high", "medium", "low", "unverified"]
    decision_type: Literal["rule", "model"]
    conclusion: str
    confidence: float = Field(ge=0, le=1)
    citation_ids: list[str]
    limitations: list[str] = []

    @model_validator(mode="after")
    def prevent_unsupported_high_risk(self):
        if self.level == "high" and not self.citation_ids:
            self.level = "unverified"
            self.limitations.append("缺少可核验法律依据")
        return self
```

补齐需求表中的全部字段，并将 `cases`、`case_facts`、`question_rounds`、`risk_findings`、`citations`、`reports`、`evaluation_runs` 映射为 SQLAlchemy 模型；JSON 字段保留原始结构化输出与版本号。

- [ ] **Step 4: 迁移并验证仓储往返**

Run: `docker compose run --rm backend alembic upgrade head`

Run: `docker compose run --rm backend pytest tests/domain tests/db -q`

Expected: 迁移成功，领域与仓储测试 PASS。

- [ ] **Step 5: 提交数据契约**

```bash
git add backend/app/domain backend/app/db backend/migrations backend/tests/domain backend/tests/db
git commit -m "feat: add case domain models and persistence"
```

### Task 3: 实现案件创建、文档解析和临时文件生命周期

**Files:**
- Create: `backend/app/api/cases.py`, `backend/app/services/documents.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/api/test_case_documents.py`, `backend/tests/services/test_documents.py`
- Create: `backend/tests/fixtures/text-contract.pdf`, `backend/tests/fixtures/scanned-contract.pdf`, `backend/tests/fixtures/contract.png`

**Interfaces:**
- Consumes: `CaseRepository`、`UPLOAD_TTL_MINUTES`。
- Produces: `POST /cases`、`POST /cases/{id}/documents`；`DocumentParser.parse(path) -> ParsedDocument(text, page_count, spans, warnings)`；`spans` 含 `text`、`page`、`confidence`、`critical_kind`。

- [ ] **Step 1: 写三种输入和清理行为测试**

```python
def test_upload_scanned_pdf_returns_ocr_confidence(client, case_id):
    with open("tests/fixtures/scanned-contract.pdf", "rb") as stream:
        response = client.post(f"/cases/{case_id}/documents", files={"file": stream})
    assert response.status_code == 200
    body = response.json()
    assert body["page_count"] == 1
    assert any(span["critical_kind"] == "date" for span in body["spans"])
    assert all(0 <= span["confidence"] <= 1 for span in body["spans"])
```

- [ ] **Step 2: 运行解析测试并确认失败**

Run: `docker compose run --rm backend pytest tests/services/test_documents.py tests/api/test_case_documents.py -q`

Expected: FAIL，提示解析服务和上传接口不存在。

- [ ] **Step 3: 实现 MIME 校验、文本 PDF 优先与 OCR 回退**

```python
class DocumentParser:
    async def parse(self, path: Path) -> ParsedDocument:
        if path.suffix.lower() == ".pdf":
            text_result = self.pdf_reader.extract(path)
            if text_result.non_whitespace_chars >= 40:
                return text_result
            return self.ocr.read_pdf(path)
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            return self.ocr.read_image(path)
        raise UnsupportedDocumentError(path.suffix)
```

对日期、金额、否定词二次标注；解析函数用 `try/finally` 删除临时文件，并增加定时清理超过 `UPLOAD_TTL_MINUTES` 的孤儿文件。失败响应保留案件与用户输入，状态设为 `parse_failed`。

- [ ] **Step 4: 运行解析与 API 测试**

Run: `docker compose run --rm backend pytest tests/services/test_documents.py tests/api/test_case_documents.py -q`

Expected: 文本 PDF、扫描 PDF、图片、错误类型、重试和清理测试全部 PASS。

- [ ] **Step 5: 提交输入链路**

```bash
git add backend/app/api backend/app/services/documents.py backend/app/main.py backend/tests
git commit -m "feat: add case creation and document parsing"
```

### Task 4: 实现事实抽取、紧急筛查和有限动态追问

**Files:**
- Create: `backend/app/services/facts.py`, `backend/app/services/urgent_rules.py`, `backend/app/services/model_client.py`, `backend/app/workflow/state.py`, `backend/app/workflow/graph.py`
- Test: `backend/tests/workflow/test_fact_question_flow.py`, `backend/tests/services/test_urgent_rules.py`

**Interfaces:**
- Consumes: 标准化文本、经历描述、已有 `CaseFacts`。
- Produces: `extract_facts(text, goal) -> CaseFacts`；`find_urgent_flags(facts) -> list[UrgentFlag]`；`select_questions(facts, asked) -> list[Question]`；`run_until_user_input(state) -> AgentState`。

- [ ] **Step 1: 写追问上限、跳过和紧急提醒测试**

```python
def test_questioning_stops_after_three_rounds(graph, incomplete_state):
    state = incomplete_state
    for _ in range(3):
        state = graph.invoke({**state, "answers": ["跳过"]})
    assert state["question_round"] == 3
    assert state["next_action"] == "analyze_with_limits"
    assert state["missing_facts"]

def test_signature_deadline_flag_is_immediate(rule_engine):
    flags = rule_engine.evaluate({"settlement_signature_due": "2026-09-14"}, today="2026-09-13")
    assert flags[0].priority == "high"
```

- [ ] **Step 2: 运行工作流测试并确认失败**

Run: `docker compose run --rm backend pytest tests/workflow/test_fact_question_flow.py tests/services/test_urgent_rules.py -q`

Expected: FAIL，提示工作流节点不存在。

- [ ] **Step 3: 实现单职责节点和问题价值排序**

```python
def select_questions(facts: CaseFacts, asked: set[str]) -> list[Question]:
    candidates = [q for q in QUESTION_CATALOG if q.field not in asked and facts.is_missing(q.field)]
    candidates.sort(key=lambda q: (-q.decision_impact, -q.urgency, q.field))
    return candidates[:3]

def route_after_gap_analysis(state: AgentState) -> str:
    if state["urgent_flags"] and not state["urgent_acknowledged"]:
        return "show_urgent_warning"
    if state["missing_facts"] and state["question_round"] < 3 and not state["skip_questions"]:
        return "ask_questions"
    return "retrieve"
```

模型输出必须通过 Pydantic 校验；结构化解析失败最多重试两次，仍失败进入 `model_failed`，不生成风险结论。

- [ ] **Step 4: 运行完整状态转换测试**

Run: `docker compose run --rm backend pytest tests/workflow tests/services/test_urgent_rules.py -q`

Expected: 每轮最多三问、总共最多三轮、跳过可继续、紧急提醒优先、失败状态明确，全部 PASS。

- [ ] **Step 5: 提交事实工作流**

```bash
git add backend/app/services/facts.py backend/app/services/urgent_rules.py backend/app/services/model_client.py backend/app/workflow backend/tests
git commit -m "feat: add fact extraction and bounded questioning workflow"
```

### Task 5: 构建版本化法律知识库和混合检索

**Files:**
- Create: `knowledge/manifest.json`, `knowledge/fixtures/retrieval_queries.json`, `backend/scripts/build_knowledge.py`, `backend/app/services/retrieval.py`
- Test: `backend/tests/services/test_retrieval.py`, `backend/tests/integration/test_knowledge_build.py`

**Interfaces:**
- Consumes: `KnowledgeRecord(source_id, title, authority, jurisdiction, document_type, article_no, content, effective_from, effective_to, status, source_url, verified_at, parent_id, neighbor_ids)`。
- Produces: `HybridRetriever.search(query, jurisdiction, as_of, limit=8) -> RetrievalTrace`；轨迹包含查询、关键词候选、向量候选、过滤原因、重排分和最终来源。

- [ ] **Step 1: 写地域、时间、状态过滤和可追溯测试**

```python
def test_retrieval_filters_expired_and_wrong_region(retriever):
    trace = retriever.search("试用期解除条件", jurisdiction="杭州", as_of="2026-09-13")
    assert trace.selected
    assert all(item.status == "现行" for item in trace.selected)
    assert all(item.jurisdiction in {"国家", "浙江", "杭州"} for item in trace.selected)
    assert all(item.source_url.startswith("https://") for item in trace.selected)
```

- [ ] **Step 2: 运行检索测试并确认失败**

Run: `docker compose run --rm backend pytest tests/services/test_retrieval.py -q`

Expected: FAIL，提示 `HybridRetriever` 不存在。

- [ ] **Step 3: 实现切分、版本清单、RRF 融合和过滤**

```python
def reciprocal_rank_fusion(keyword_ids: list[str], vector_ids: list[str], k: int = 60) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in (keyword_ids, vector_ids):
        for rank, source_id in enumerate(ranking, start=1):
            scores[source_id] = scores.get(source_id, 0.0) + 1.0 / (k + rank)
    return scores
```

构建脚本按条文或语义完整段落切分，写入 Chroma 时保留全部元数据和邻接关系；`manifest.json` 固定 `knowledge_version`、文件 SHA-256、核验日期和官方 URL。非官方材料不得进入可引用集合。

- [ ] **Step 4: 构建并验证冻结知识库**

Run: `docker compose run --rm backend python scripts/build_knowledge.py --manifest /app/knowledge/manifest.json --reset`

Run: `docker compose run --rm backend pytest tests/services/test_retrieval.py tests/integration/test_knowledge_build.py -q`

Expected: 所有预设查询均返回可定位来源，过期与错误地域记录被过滤，测试 PASS。

- [ ] **Step 5: 提交知识库链路**

```bash
git add knowledge backend/scripts/build_knowledge.py backend/app/services/retrieval.py backend/tests
git commit -m "feat: add versioned legal knowledge retrieval"
```

### Task 6: 实现确定性规则、模型风险判断和引用防护

**Files:**
- Create: `backend/app/services/risk_rules.py`, `backend/app/services/citation_guard.py`
- Modify: `backend/app/workflow/graph.py`
- Test: `backend/tests/services/test_risk_rules.py`, `backend/tests/services/test_citation_guard.py`, `backend/tests/workflow/test_risk_analysis.py`

**Interfaces:**
- Consumes: `CaseFacts`、`RetrievalTrace`、版本化规则集。
- Produces: `RuleEngine.evaluate(facts) -> list[RiskFinding]`；`CitationGuard.validate(findings, trace) -> CitationValidationResult`；最终风险只保留通过白名单和支持性校验的引用。

- [ ] **Step 1: 写法条编造、规则/模型区分和冲突降级测试**

```python
def test_unknown_citation_downgrades_finding(guard, retrieval_trace):
    finding = RiskFinding(title="欠薪", level="high", decision_type="model",
                          conclusion="违法", confidence=0.9, citation_ids=["invented-42"])
    result = guard.validate([finding], retrieval_trace)
    assert result.findings[0].level == "unverified"
    assert "引用不在本次检索结果中" in result.findings[0].limitations

def test_rule_finding_is_labeled(rule_engine, probation_facts):
    finding = rule_engine.evaluate(probation_facts)[0]
    assert finding.decision_type == "rule"
    assert finding.rule_version
```

- [ ] **Step 2: 运行风险测试并确认失败**

Run: `docker compose run --rm backend pytest tests/services/test_risk_rules.py tests/services/test_citation_guard.py -q`

Expected: FAIL，提示规则或引用校验器不存在。

- [ ] **Step 3: 实现白名单引用与四级风险策略**

```python
def validate(self, findings: list[RiskFinding], trace: RetrievalTrace) -> CitationValidationResult:
    allowed = {item.source_id: item for item in trace.selected}
    for finding in findings:
        invalid = [cid for cid in finding.citation_ids if cid not in allowed]
        if invalid or (finding.level == "high" and not finding.citation_ids):
            finding.level = "unverified"
            finding.confidence = min(finding.confidence, 0.49)
            finding.limitations.append("引用不在本次检索结果中")
    return CitationValidationResult(findings=findings)
```

第一版规则只覆盖需求明确的高价值确定项：试用期期限与工资比例、合同必备信息、关键日期/通知/签字提醒。模型只处理复杂事实解释，输出必须携带选自检索上下文的 `source_id`。

- [ ] **Step 4: 运行规则、引用与工作流集成测试**

Run: `docker compose run --rm backend pytest tests/services/test_risk_rules.py tests/services/test_citation_guard.py tests/workflow/test_risk_analysis.py -q`

Expected: 编造引用被拦截，冲突与无依据结果降级，规则/模型标签清晰，全部 PASS。

- [ ] **Step 5: 提交风险判断链路**

```bash
git add backend/app/services/risk_rules.py backend/app/services/citation_guard.py backend/app/workflow/graph.py backend/tests
git commit -m "feat: add guarded legal risk analysis"
```

### Task 7: 生成固定结构报告并导出一致 PDF

**Files:**
- Create: `backend/app/services/reporting.py`, `backend/app/templates/report.html`
- Modify: `backend/app/api/cases.py`
- Test: `backend/tests/services/test_reporting.py`, `backend/tests/api/test_report_api.py`

**Interfaces:**
- Consumes: 完整 `AgentState`、已校验 `RiskFinding` 和 `Citation`。
- Produces: `build_report(state) -> FinalReport`；`render_report_pdf(report) -> bytes`；`GET /cases/{id}/report` 与 `GET /cases/{id}/report.pdf`。

- [ ] **Step 1: 写固定章节和网页/PDF一致性测试**

```python
def test_report_contains_required_sections(report_service, analyzed_state):
    report = report_service.build_report(analyzed_state)
    assert len(report.priority_actions) <= 3
    assert report.fact_summary
    assert report.unknown_facts
    assert report.risks
    assert report.capability_boundary
    assert all(r.decision_type in {"rule", "model"} for r in report.risks)
```

- [ ] **Step 2: 运行报告测试并确认失败**

Run: `docker compose run --rm backend pytest tests/services/test_reporting.py tests/api/test_report_api.py -q`

Expected: FAIL，提示报告服务或接口不存在。

- [ ] **Step 3: 实现八段式报告与安全输出**

```python
def priority_score(item: RiskFinding) -> float:
    urgency = {"high": 4, "medium": 2, "low": 1, "unverified": 1}[item.level]
    evidence = item.confidence
    action_cost = getattr(item, "action_cost", 1.0)
    return urgency * 2 + evidence - action_cost

def build_report(state: AgentState) -> FinalReport:
    risks = sorted(state["risk_findings"], key=priority_score, reverse=True)
    return FinalReport(
        summary=limited_summary(risks), priority_actions=actions_for(risks[:3]),
        fact_summary=state["case_facts"], unknown_facts=state["missing_facts"],
        risks=risks, evidence_plan=build_evidence_plan(risks),
        communication_scripts=build_scripts(risks, state["user_goal"]),
        capability_boundary=LEGAL_SAFETY_BOUNDARY,
    )
```

PDF 直接从同一 `FinalReport` 和 HTML 模板生成，禁止另起一套内容逻辑；来源名称、条文、状态、URL、适用理由和限制必须同时出现。

- [ ] **Step 4: 验证 JSON、PDF和缺失依据场景**

Run: `docker compose run --rm backend pytest tests/services/test_reporting.py tests/api/test_report_api.py -q`

Expected: JSON 与 PDF 章节一致，待核实结果无确定性措辞，全部 PASS。

- [ ] **Step 5: 提交报告能力**

```bash
git add backend/app/services/reporting.py backend/app/templates backend/app/api/cases.py backend/tests
git commit -m "feat: add traceable report and pdf export"
```

### Task 8: 完成前端四个页面和进度反馈

**Files:**
- Create: `frontend/src/api/client.ts`, `frontend/src/pages/HomePage.tsx`, `frontend/src/pages/CaseWorkspace.tsx`, `frontend/src/pages/ReportPage.tsx`, `frontend/src/pages/EvaluationPage.tsx`, `frontend/src/components/SourceDrawer.tsx`, `frontend/src/components/ProgressTimeline.tsx`
- Test: `frontend/src/pages/*.test.tsx`, `frontend/e2e/core-flows.spec.ts`

**Interfaces:**
- Consumes: Task 3、4、7、9 的 HTTP 接口与 JSON 契约。
- Produces: `/`、`/cases/:id`、`/cases/:id/report`、`/evaluation`；用户能看到状态 `created/parsing/questioning/retrieving/analyzing/report_ready/failed`。

- [ ] **Step 1: 写两个入口、追问上限、来源抽屉和失败保留测试**

```tsx
it("keeps entered experience when analysis fails", async () => {
  server.use(http.post("*/cases/:id/analyze", () => HttpResponse.json({message:"模型暂不可用"}, {status:503})));
  render(<CaseWorkspace />);
  await userEvent.type(screen.getByLabelText("工作经历"), "入职后被通知试用期解除");
  await userEvent.click(screen.getByRole("button", {name:"开始分析"}));
  expect(await screen.findByText("模型暂不可用")).toBeVisible();
  expect(screen.getByLabelText("工作经历")).toHaveValue("入职后被通知试用期解除");
});
```

- [ ] **Step 2: 运行页面测试并确认失败**

Run: `docker compose run --rm frontend npm test -- --run`

Expected: FAIL，提示页面与组件不存在。

- [ ] **Step 3: 实现统一案件工作区和报告展示**

```tsx
export function ProgressTimeline({status}: {status: CaseStatus}) {
  const labels: Record<CaseStatus, string> = {
    created: "案件已创建", parsing: "正在解析材料", questioning: "等待补充信息",
    retrieving: "正在检索法律资料", analyzing: "正在分析风险",
    report_ready: "报告已生成", failed: "处理失败，可重试"
  };
  return <p role="status" aria-live="polite">{labels[status]}</p>;
}
```

首页明确展示能力边界；工作区保留表单状态并允许跳过；报告页把事实与推断、规则与模型、来源与限制分别标示；来源抽屉展示官方 URL、有效状态和适用理由。

- [ ] **Step 4: 运行单元与两条端到端流程**

Run: `docker compose run --rm frontend npm test -- --run`

Run: `docker compose run --rm frontend npm run test:e2e`

Expected: 合同审查和经历分析均从入口运行到报告，失败时可重试且输入不丢失。

- [ ] **Step 5: 提交前端闭环**

```bash
git add frontend/src frontend/e2e
git commit -m "feat: add case workspace and traceable report UI"
```

### Task 9: 建立 20 至 30 例固定评测与指标页面

**Files:**
- Create: `evaluations/schema.json`, `evaluations/dataset.v1.jsonl`, `evaluations/expected_metrics.json`, `backend/scripts/run_evaluation.py`, `backend/app/api/evaluations.py`
- Modify: `frontend/src/pages/EvaluationPage.tsx`
- Test: `backend/tests/evaluation/test_metrics.py`, `backend/tests/api/test_evaluations.py`

**Interfaces:**
- Consumes: 冻结知识库版本、提示词版本、规则版本和模型配置。
- Produces: `POST /evaluations/run -> {evaluation_id, status}`；`GET /evaluations/{id}` 返回风险召回率、风险准确率、引用正确率、幻觉率、追问完整率、结构化成功率、端到端成功率和失败样本。

- [ ] **Step 1: 写指标公式和失败样本保留测试**

```python
def test_metrics_include_failures():
    result = compute_metrics([
        EvaluationOutcome(expected={"A", "B"}, predicted={"A", "C"}, citations_valid=False, hallucinated=True)
    ])
    assert result.risk_recall == 0.5
    assert result.risk_precision == 0.5
    assert result.citation_accuracy == 0.0
    assert result.hallucination_rate == 1.0
    assert len(result.failures) == 1
```

- [ ] **Step 2: 运行指标测试并确认失败**

Run: `docker compose run --rm backend pytest tests/evaluation/test_metrics.py tests/api/test_evaluations.py -q`

Expected: FAIL，提示评测模型与计算函数不存在。

- [ ] **Step 3: 实现分层数据集和可重复运行器**

```python
def safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0

def compute_metrics(outcomes: list[EvaluationOutcome]) -> EvaluationMetrics:
    tp = sum(len(o.expected & o.predicted) for o in outcomes)
    expected = sum(len(o.expected) for o in outcomes)
    predicted = sum(len(o.predicted) for o in outcomes)
    return EvaluationMetrics(
        risk_recall=safe_ratio(tp, expected), risk_precision=safe_ratio(tp, predicted),
        citation_accuracy=safe_ratio(sum(o.citations_valid for o in outcomes), len(outcomes)),
        hallucination_rate=safe_ratio(sum(o.hallucinated for o in outcomes), len(outcomes)),
        failures=[o.to_failure() for o in outcomes if not o.passed],
    )
```

数据集包含正常合同、边界合同、高风险合同、试用期/欠薪/调岗降薪/离职补偿经历和对抗样本；每例明确输入、期望风险、关键缺口、允许引用、禁止断言和预期终态。

- [ ] **Step 4: 运行固定评测并检查版本记录**

Run: `docker compose run --rm backend python scripts/run_evaluation.py --dataset /app/evaluations/dataset.v1.jsonl`

Run: `docker compose run --rm backend pytest tests/evaluation tests/api/test_evaluations.py -q`

Expected: 生成一次带数据集、知识库、模型、提示词和规则版本的运行记录；页面展示所有指标及失败样本。

- [ ] **Step 5: 提交评测系统**

```bash
git add evaluations backend/scripts/run_evaluation.py backend/app/api/evaluations.py backend/tests frontend/src/pages/EvaluationPage.tsx
git commit -m "feat: add reproducible evaluation suite"
```

### Task 10: 加固重试、超时、隐私和端到端验收

**Files:**
- Create: `backend/app/services/resilience.py`, `backend/tests/integration/test_failure_degradation.py`, `frontend/e2e/acceptance.spec.ts`, `scripts/demo_check.ps1`
- Modify: `backend/app/services/model_client.py`, `backend/app/services/documents.py`, `backend/app/services/retrieval.py`, `compose.yaml`, `Makefile`

**Interfaces:**
- Consumes: 所有外部依赖适配器。
- Produces: `retry_async(operation, attempts=3, timeout_seconds=30)`；统一错误码 `OCR_FAILED`、`MODEL_FAILED`、`RETRIEVAL_FAILED`、`REPORT_FAILED`；`make demo-check` 验收入口。

- [ ] **Step 1: 写依赖失败、超时和文件删除测试**

```python
async def test_model_failure_preserves_case_and_emits_no_report(client, model_stub, case_id):
    model_stub.fail_all_calls()
    response = await client.post(f"/cases/{case_id}/analyze")
    assert response.status_code == 503
    assert response.json()["code"] == "MODEL_FAILED"
    assert await case_exists(case_id)
    assert await report_count(case_id) == 0
```

- [ ] **Step 2: 运行降级测试并确认失败**

Run: `docker compose run --rm backend pytest tests/integration/test_failure_degradation.py -q`

Expected: FAIL，提示统一重试和错误契约不存在。

- [ ] **Step 3: 实现有界重试、健康检查和演示自检**

```python
async def retry_async(operation, attempts: int = 3, timeout_seconds: int = 30):
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return await asyncio.wait_for(operation(), timeout_seconds)
        except (TimeoutError, ConnectionError) as error:
            last_error = error
            if attempt + 1 < attempts:
                await asyncio.sleep(2 ** attempt)
    raise DependencyUnavailableError(str(last_error))
```

Compose 为后端、MySQL、Chroma 添加健康检查；演示自检依次验证健康接口、知识库版本、两套固定夹具、PDF 导出和评测数据集，不打印密钥或用户原文。

- [ ] **Step 4: 运行全量验收**

Run: `make test`

Run: `make demo-check`

Expected: 后端、前端和端到端测试全部 PASS；两条核心流程完成；临时文件无残留；三类依赖失败均显示可重试状态且不产生伪结果。

- [ ] **Step 5: 提交可靠性加固**

```bash
git add backend frontend compose.yaml Makefile scripts
git commit -m "test: enforce failure degradation and acceptance flows"
```

### Task 11: 完成交付文档、架构图和三分钟演示材料

**Files:**
- Create: `README.md`, `docs/architecture.md`, `docs/demo-script.md`, `docs/known-limitations.md`, `demo/contract-review/`, `demo/probation-dismissal/`
- Test: `backend/tests/docs/test_documentation.py`

**Interfaces:**
- Consumes: 已通过 Task 10 验收的命令、接口、版本和截图。
- Produces: 一页即可找到的启动命令、架构说明、两条演示脚本、已知限制、固定虚构材料及录屏检查清单。

- [ ] **Step 1: 写交付物完整性测试**

```python
from pathlib import Path

def test_delivery_files_and_readme_sections_exist():
    required = ["README.md", "docs/architecture.md", "docs/demo-script.md",
                "docs/known-limitations.md", "demo/contract-review", "demo/probation-dismissal"]
    assert all(Path(path).exists() for path in required)
    readme = Path("README.md").read_text(encoding="utf-8")
    for heading in ["## 能力边界", "## 架构", "## 启动", "## 评测结果", "## 已知限制"]:
        assert heading in readme
```

- [ ] **Step 2: 运行文档检查并确认失败**

Run: `docker compose run --rm backend pytest tests/docs/test_documentation.py -q`

Expected: FAIL，列出尚未创建的交付文件。

- [ ] **Step 3: 编写与真实实现一致的材料**

README 使用 `docker compose up --build` 作为唯一启动主路径，列出环境变量但不包含密钥；架构文档绘制服务图和 LangGraph 节点时序；演示脚本严格控制为合同审查与试用期辞退两条流程，每条包含一次追问、一次有限结论、一次来源展开和一次失败/评测展示。

- [ ] **Step 4: 执行交付前检查并录制演示**

Run: `make demo-check`

Run: `docker compose run --rm backend pytest tests/docs/test_documentation.py -q`

Expected: 检查 PASS；按 `docs/demo-script.md` 在约三分钟内完成演示；画面不出现真实个人信息、API 密钥或不受支持的法律承诺。

- [ ] **Step 5: 提交最终交付材料**

```bash
git add README.md docs demo backend/tests/docs
git commit -m "docs: add architecture evaluation and demo materials"
```

## Implementation Sequence and Milestones

- 第 1 至 2 天：Task 1–2，得到可启动骨架和稳定数据契约。
- 第 3 至 5 天：Task 3 与 Task 5，得到输入解析和可追溯知识库。
- 第 6 至 8 天：Task 4，得到事实抽取、紧急筛查和有限追问闭环。
- 第 9 至 11 天：Task 6–7，得到受引用约束的风险判断与可导出报告。
- 第 12 至 14 天：Task 8，完成可演示的前端全流程。
- 第 15 至 17 天：Task 9–10，完成可重复评测和失败降级。
- 第 18 至 21 天：Task 11，修复验收问题并完成 README、架构图和演示视频。

## Requirement Traceability

| 需求范围 | 对应任务 |
|---|---|
| FR 01–04 输入与案件创建 | Task 1、3、8 |
| FR 05–08 事实、紧急筛查和追问 | Task 2、4、8 |
| FR 09–12 检索、规则、模型和引用限制 | Task 5、6 |
| FR 13–17 报告、证据、话术和 PDF | Task 7、8 |
| LangGraph 单工作流和关键状态 | Task 2、4、6、7 |
| 法律知识记录、构建与冻结 | Task 5 |
| MySQL 数据表和接口边界 | Task 2、3、7、9 |
| 可靠性、隐私、可复现和部署 | Task 1、3、9、10 |
| 四个页面 | Task 8、9 |
| 20 至 30 个分层测试案例和七项指标 | Task 9 |
| 两条演示流程与最终交付清单 | Task 10、11 |

## Definition of Done

- `make test` 和 `make demo-check` 均通过。
- 合同审查和试用期辞退从输入到网页报告与 PDF 全链路成功。
- 追问轮次与每轮问题数符合上限，跳过后生成带缺口的有限结论。
- 每项法律风险能定位到冻结知识库来源，任何越权引用都会被阻断或降级。
- 页面明确区分事实/推断、规则/模型、确定/待核实，并展示处理进度。
- OCR、模型、检索失败均能重试、保留输入、显示明确状态且不生成伪结果。
- 临时上传文件按成功、失败或超时路径删除。
- 固定评测可重复运行，保存七项指标、版本信息和失败样本。
- README、架构图、自动化测试、两套虚构演示材料和约三分钟演示视频齐全。
