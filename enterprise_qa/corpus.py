"""Safe raw source documents for local Clause-Bridge indexing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceDocument:
    document_id: str
    title: str
    version: str
    date: str
    body: str


DOCUMENTS = (
    SourceDocument(
        document_id="D01",
        title="Travel and Expense Policy",
        version="2026.1",
        date="2026-01-01",
        body=(
            "第一条 适用范围：本政策适用于普通国内差旅产生的合规费用。"
            "第二条 提交期限：普通国内差旅报销凭证须在费用发生后 30 个自然日内提交。"
            "第三条 例外：紧急项目费用适用单独的补充规定。"
        ),
    ),
    SourceDocument(
        document_id="D02",
        title="Urgent Project Expense Addendum",
        version="2026.2",
        date="2026-02-15",
        body=(
            "第一条 适用范围：本补充规定仅适用于已确认的紧急项目费用。"
            "第二条 提交期限：紧急项目报销凭证须在费用发生后 15 个自然日内提交。"
            "第三条 确认要求：适用前须确认该费用属于紧急项目。"
        ),
    ),
    SourceDocument(
        document_id="P01",
        title="Creator Hub Export Guide",
        version="2026.1",
        date="2026-01-10",
        body=(
            "第一条 导出视频：Creator Hub 支持导出已生成的视频片段。"
            "第二条 保留期限：导出的视频片段在 Creator Hub 中自生成起保留 30 天。"
        ),
    ),
)
