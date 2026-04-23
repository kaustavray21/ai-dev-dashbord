"""
log_parser.py — Log file analysis utilities.

Classes
-------
LogAnalyzer
    Pure-Python log processing.  No Django or OpenAI imports — fully
    unit-testable in isolation.

    Methods
    -------
    extract_errors(log_text)         → list[dict]
    summarize_for_ai(log_text)       → str
    build_analysis_prompt(log_text)  → list[dict]   (OpenAI messages array)
    analyze(log_text, openai_client) → dict          (structured result)
"""

from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.contracts import IOpenAIClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Context lines to include above/below each error line when summarising
_CONTEXT_LINES = 3

# Maximum characters sent to OpenAI in the summarised prompt
_MAX_CHARS = 8000


class LogAnalyzer:
    """
    Parses, summarises, and drives AI analysis of plain-text log files.

    Design principles
    -----------------
    • All regex/string work is pure Python — no I/O, no Django, no OpenAI.
    • analyze() is the single public orchestration method that ties the
      pipeline together and calls back into the injected IOpenAIClient.
    """

    # ------------------------------------------------------------------
    # 5.3 Task: 4 regex patterns from blueprint
    # ------------------------------------------------------------------
    ERROR_PATTERNS: list[tuple[str, re.Pattern]] = [
        (
            "EXCEPTION",
            re.compile(
                r"(?i)(exception|traceback\s+\(most\s+recent\s+call\s+last\)|"
                r"error:|critical:)",
            ),
        ),
        (
            "HTTP_ERROR",
            re.compile(
                r"\b(4\d{2}|5\d{2})\b",   # 4xx / 5xx HTTP status codes
            ),
        ),
        (
            "DB_ERROR",
            re.compile(
                r"(?i)(OperationalError|IntegrityError|ProgrammingError|"
                r"connection\s+refused|deadlock|timeout)",
            ),
        ),
        (
            "STACK_TRACE",
            re.compile(
                r'(?i)(File\s+"[^"]+",\s+line\s+\d+|'
                r'at\s+\w+\.\w+\([^)]+\))',   # Python / Java style traces
            ),
        ),
    ]

    # ------------------------------------------------------------------
    # extract_errors
    # ------------------------------------------------------------------

    def extract_errors(self, log_text: str) -> list[dict]:
        """
        Scan *log_text* line-by-line and return every line that matches
        at least one ERROR_PATTERN.

        Returns
        -------
        list[dict]
            Each entry:
            {
                "line_number": int,
                "pattern":     str,   # name of the first matching pattern
                "content":     str,   # the raw log line (stripped)
            }
        """
        results: list[dict] = []
        for line_no, line in enumerate(log_text.splitlines(), start=1):
            for pattern_name, pattern in self.ERROR_PATTERNS:
                if pattern.search(line):
                    results.append(
                        {
                            "line_number": line_no,
                            "pattern": pattern_name,
                            "content": line.strip(),
                        }
                    )
                    break  # only report the first matching pattern per line

        logger.debug("extract_errors: found %d matching lines", len(results))
        return results

    # ------------------------------------------------------------------
    # summarize_for_ai
    # ------------------------------------------------------------------

    def summarize_for_ai(
        self,
        log_text: str,
        max_chars: int = _MAX_CHARS,
    ) -> str:
        """
        Trim *log_text* to the most relevant portion so the AI prompt
        stays within a reasonable token budget.

        Strategy
        --------
        1. Collect all error lines (via extract_errors) and expand each
           by ±CONTEXT_LINES neighbours.
        2. Deduplicate / sort the selected line indices.
        3. Concatenate those lines, separated by "…" markers when there
           are gaps.
        4. If the result still exceeds *max_chars*, truncate from the
           end (keeping the beginning where errors usually start).
        5. If no error lines are found, return the last *max_chars*
           characters of the log (tail is usually most informative).

        Parameters
        ----------
        log_text : str
        max_chars : int
            Hard ceiling on the returned string length (default 8 000).

        Returns
        -------
        str
            The trimmed, most-relevant portion of the log.
        """
        lines = log_text.splitlines()
        total = len(lines)

        if total == 0:
            return ""

        error_matches = self.extract_errors(log_text)

        if not error_matches:
            # No errors found — return the tail (most recent entries)
            raw = "\n".join(lines[-300:])
            return raw[-max_chars:]

        # Build the set of line indices (0-based) to include
        selected: set[int] = set()
        for match in error_matches:
            idx = match["line_number"] - 1          # convert to 0-based
            start = max(0, idx - _CONTEXT_LINES)
            end = min(total, idx + _CONTEXT_LINES + 1)
            selected.update(range(start, end))

        sorted_indices = sorted(selected)

        # Build the output with gap markers
        chunks: list[str] = []
        prev: int | None = None
        for idx in sorted_indices:
            if prev is not None and idx > prev + 1:
                chunks.append("…")
            chunks.append(lines[idx])
            prev = idx

        result = "\n".join(chunks)

        # Hard-truncate if still over budget
        if len(result) > max_chars:
            result = result[:max_chars]

        return result

    # ------------------------------------------------------------------
    # build_analysis_prompt
    # ------------------------------------------------------------------

    def build_analysis_prompt(self, log_text: str) -> list[dict]:
        """
        Build the OpenAI messages array for log analysis.

        Returns
        -------
        list[dict]
            A two-element list:
            [
                { "role": "system",  "content": <system instruction> },
                { "role": "user",    "content": <summarised log snippet> },
            ]
        """
        summarised = self.summarize_for_ai(log_text)
        error_hits = self.extract_errors(log_text)

        # Compact error-line summary prepended to the snippet
        if error_hits:
            hit_lines = "\n".join(
                f"  Line {h['line_number']} [{h['pattern']}]: {h['content'][:120]}"
                for h in error_hits[:20]   # cap to avoid ballooning the prompt
            )
            preface = (
                f"The regex scanner found {len(error_hits)} error line(s):\n"
                f"{hit_lines}\n\n"
                "Full log excerpt (errors ± context):\n"
            )
        else:
            preface = "No regex errors detected. Full log excerpt (tail):\n"

        system_msg = (
            "You are an expert software engineer and DevOps specialist. "
            "Analyse the log excerpt provided by the user and respond with "
            "valid JSON containing exactly these keys:\n"
            '  "summary"         — a concise plain-text description (≤ 3 sentences)\n'
            '  "errors"          — array of objects: { "line": int|null, "description": str }\n'
            '  "recommendations" — array of actionable fix strings\n'
            "Do not include markdown fences or any text outside the JSON object."
        )

        user_msg = preface + summarised

        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

    # ------------------------------------------------------------------
    # analyze  (orchestrator)
    # ------------------------------------------------------------------

    def analyze(
        self,
        log_text: str,
        openai_client: "IOpenAIClient",
    ) -> dict:
        """
        Full pipeline: extract → summarise → prompt → call → return.

        Parameters
        ----------
        log_text : str
            Raw log file contents.
        openai_client : IOpenAIClient
            Any object satisfying the IOpenAIClient protocol.

        Returns
        -------
        dict
            {
                "summary":         str,
                "errors":          list[dict],   # from AI
                "recommendations": list[str],
                "raw_matches":     list[dict],   # from extract_errors (regex)
                "tokens_used":     int,
            }
        """
        import json as _json

        raw_matches = self.extract_errors(log_text)
        messages = self.build_analysis_prompt(log_text)

        result = openai_client.chat_completion(messages=messages)

        content = result.get("content", "{}")
        tokens_used = result.get("tokens_used", 0)

        # Parse JSON — be lenient in case the model wraps in a code fence
        try:
            # Strip markdown code fences if present
            clean = re.sub(r"^```[a-z]*\n?", "", content.strip(), flags=re.MULTILINE)
            clean = re.sub(r"```$", "", clean.strip(), flags=re.MULTILINE).strip()
            ai_data = _json.loads(clean)
        except (_json.JSONDecodeError, ValueError) as exc:
            logger.warning("LogAnalyzer.analyze: failed to parse AI JSON — %s", exc)
            ai_data = {
                "summary": content,
                "errors": [],
                "recommendations": ["Could not parse structured AI response."],
            }

        return {
            "summary": ai_data.get("summary", ""),
            "errors": ai_data.get("errors", []),
            "recommendations": ai_data.get("recommendations", []),
            "raw_matches": raw_matches,
            "tokens_used": tokens_used,
        }
