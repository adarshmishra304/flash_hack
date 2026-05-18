"""
Agentic Review Layer — provider-agnostic via LangChain.

Auto-detects the LLM provider from whichever API key is set:
  ANTHROPIC_API_KEY  → Claude  (claude-sonnet-4-6)
  OPENAI_API_KEY     → GPT-4o  (gpt-4o)
  GOOGLE_API_KEY     → Gemini  (gemini-1.5-pro)

Uses LangChain's bind_tools + agentic loop so the same code works
across all providers without any changes.
"""

import os
import sys
from typing import Literal, List

from pydantic import BaseModel, Field

# ── Provider detection ────────────────────────────────────────────────────────

_PROVIDERS = [
    ("GROQ_API_KEY",      "groq",      "llama-3.3-70b-versatile", "Llama 3.3 70B (Groq)"),
    ("ANTHROPIC_API_KEY", "anthropic", "claude-sonnet-4-6",       "Claude (Anthropic)"),
    ("OPENAI_API_KEY",    "openai",    "gpt-4o",                  "GPT-4o (OpenAI)"),
    ("GOOGLE_API_KEY",    "google",    "gemini-1.5-pro",          "Gemini (Google)"),
]


def _load_llm():
    """Return (llm, label) for the first provider whose API key is set."""
    for env_var, provider, model, label in _PROVIDERS:
        if not os.environ.get(env_var):
            continue
        try:
            if provider == "groq":
                from langchain_groq import ChatGroq
                return ChatGroq(model=model), label

            elif provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                return ChatAnthropic(model=model), label

            elif provider == "openai":
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(model=model), label

            elif provider == "google":
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(model=model), label

        except ImportError as e:
            print("  WARNING: {} key found but package missing — {}".format(label, e))
            continue

    print("ERROR: No API key found. Set one of:")
    for env_var, _, _, label in _PROVIDERS:
        print("  export {}=<your-key>   # {}".format(env_var, label))
    sys.exit(1)


# ── Structured output schema (Pydantic) ──────────────────────────────────────

class Violation(BaseModel):
    """Assessment of a single pattern violation."""
    line:     int   = Field(description="Line number of the violation")
    pattern:  str   = Field(description="The matched pattern string")
    severity: Literal["critical", "high", "medium", "low", "info"] = Field(
        description=(
            "critical=immediate security risk, high=significant risk in likely "
            "code path, medium=risk under some conditions, low=style concern, "
            "info=no immediate risk"
        )
    )
    risk: str = Field(description="1-2 sentences on the specific risk in this context")
    fix:  str = Field(description="Concrete, specific safer alternative or fix")


class ReviewOutput(BaseModel):
    """Complete review result returned in one structured response."""
    violations:         List[Violation] = Field(description="Assessment of every violation found")
    overall_assessment: str             = Field(description="2-4 sentence security and quality summary")
    quality_score:      int             = Field(ge=0, le=10, description="Code quality score 0-10")
    priority_action:    str             = Field(description="Single most important thing to fix first")


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM = (
    "You are a senior security-focused code reviewer. A static analysis tool has "
    "scanned a source file and found pattern matches. You receive the results with "
    "each violation's matched line and +-2 lines of context.\n\n"
    "Your task:\n"
    "1. Call flag_violation for EVERY violation — do not skip any.\n"
    "2. Assess severity from CONTEXT, not just the pattern. An eval() behind a "
    "strict regex guard is lower risk than a raw eval(user_input).\n"
    "3. Give a specific fix — not 'avoid eval' but what to replace it with.\n"
    "4. Call summarize_review exactly once at the end.\n\n"
    "If there are NO violations: skip flag_violation and just call summarize_review "
    "with a clean assessment.\n\n"
    "Be direct, brief, and reference actual line numbers."
)


# ── Formatting helpers ────────────────────────────────────────────────────────

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_SEP            = "=" * 62
_THIN           = "-" * 62
_BAR_WIDTH      = 20


def _score_bar(score):
    filled = int(score / 10 * _BAR_WIDTH)
    return "[" + "█" * filled + "░" * (_BAR_WIDTH - filled) + "] {}/10".format(score)


def _build_prompt(violations, filepath):
    if not violations:
        return (
            "The static scanner found NO violations in: {}\n\n"
            "Skip flag_violation entirely. Just call summarize_review "
            "with a clean assessment."
        ).format(filepath)

    parts = [
        "Static scan results for: {}\n".format(filepath),
        "{} violation(s):\n".format(len(violations)),
    ]
    for v in violations:
        parts.append("─" * 40)
        parts.append("LINE {}  |  pattern: {!r}".format(v["line"], v["pattern"]))
        parts.append("Matched : {}".format(v["context"].rstrip()))
        parts.append("Context :")
        for ctx_ln, ctx_text in v["surrounding"]:
            marker = ">>>" if ctx_ln == v["line"] else "   "
            parts.append("  {} {:>4} | {}".format(marker, ctx_ln, ctx_text.rstrip()))
        parts.append("")
    return "\n".join(parts)


def _print_flagged(flagged):
    for f in sorted(flagged, key=lambda x: (_SEVERITY_ORDER.get(x["severity"], 5), x["line"])):
        print("\n  ┌─[ {} ]─ Line {}  ·  {!r}".format(
            f["severity"].upper(), f["line"], f["pattern"]))
        print("  ├─ Risk : {}".format(f["risk"]))
        print("  └─ Fix  : {}".format(f["fix"]))


def _print_summary(summary):
    print("\n" + _SEP)
    print("  OVERALL ASSESSMENT")
    print(_SEP)
    print()
    print("  Quality Score : {}".format(_score_bar(summary["quality_score"])))
    print()
    buf, col = "  ", 2
    for word in summary["overall_assessment"].split():
        if col + len(word) + 1 > 58:
            print(buf)
            buf, col = "  ", 2
        buf += word + " "
        col += len(word) + 1
    if buf.strip():
        print(buf)
    print()
    print("  Priority action:")
    print("    → {}".format(summary["priority_action"]))
    print()
    print(_SEP)


def _write_agent_section(flagged, summary, filepath, label):
    from datetime import datetime
    lines = [
        "", _SEP,
        "  AGENT REVIEW  ·  {}".format(label),
        "  File      : {}".format(filepath),
        "  Generated : {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        _SEP,
    ]
    for f in sorted(flagged, key=lambda x: (_SEVERITY_ORDER.get(x["severity"], 5), x["line"])):
        lines += [
            "",
            "  [ {} ]  Line {}  ·  {!r}".format(f["severity"].upper(), f["line"], f["pattern"]),
            "  Risk : {}".format(f["risk"]),
            "  Fix  : {}".format(f["fix"]),
        ]
    if summary:
        lines += [
            "", _SEP,
            "  OVERALL ASSESSMENT",
            "  Quality Score : {}/10".format(summary["quality_score"]),
            "  {}".format(summary["overall_assessment"]),
            "  Priority      : {}".format(summary["priority_action"]),
            _SEP,
        ]
    return "\n".join(lines)


# ── Agent class ───────────────────────────────────────────────────────────────

class AgentReviewer:
    """
    Provider-agnostic agentic code reviewer.
    Auto-detects Claude / GPT-4o / Gemini from environment variables.
    Uses LangChain bind_tools + agentic loop — same code, any provider.
    """

    def __init__(self):
        self.llm, self.label = _load_llm()

        # Force structured output — more reliable than multi-tool calling
        self.llm_structured = self.llm.with_structured_output(ReviewOutput)

    def run(self, violations, filepath, report_path):
        from langchain_core.messages import SystemMessage, HumanMessage

        print("\n" + _SEP)
        print("  AGENT REVIEW  ·  {}".format(self.label))
        print("  File : {}".format(filepath))
        print(_SEP)

        count = len(violations)
        if count:
            print("\n  {} violation(s) — sending to agent...\n".format(count))
        else:
            print("\n  No violations — requesting clean-bill review...\n")

        messages = [
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=_build_prompt(violations, filepath)),
        ]

        flagged = []
        summary = None

        # ── Single structured call — all violations + summary in one response ─
        try:
            result = self.llm_structured.invoke(messages)

            for v in result.violations:
                entry = v.model_dump() if hasattr(v, "model_dump") else dict(v)
                flagged.append(entry)
                print("  [ {:<8} ]  Line {:>4}  ·  {}".format(
                    entry.get("severity", "?").upper(),
                    entry.get("line", "?"),
                    entry.get("pattern", "?"),
                ))

            summary = {
                "overall_assessment": result.overall_assessment,
                "quality_score":      result.quality_score,
                "priority_action":    result.priority_action,
            }
            print("  [ SUMMARY  ]  score={}/10".format(result.quality_score))

        except Exception as exc:
            print("\n  ERROR: Agent call failed — {}".format(exc))
            print("  Showing partial results below.\n")

        # ── Render ────────────────────────────────────────────────────────────
        print("\n" + _THIN)
        print("  VIOLATIONS — Agent Assessment")
        print(_THIN)

        if not flagged:
            print("\n  Agent found no issues to flag.\n")
        else:
            _print_flagged(flagged)

        if summary:
            _print_summary(summary)

        # ── Persist ───────────────────────────────────────────────────────────
        agent_text = _write_agent_section(flagged, summary, filepath, self.label)
        with open(report_path, "a", encoding="utf-8") as fh:
            fh.write(agent_text + "\n")
        print("  Agent review appended to: {}\n".format(report_path))
