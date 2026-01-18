SYSTEM_PROMPT = """You are paper2exp-agent, an evidence-bound reproducibility agent.

NON-NEGOTIABLE RULES:
1) Do NOT invent facts. Do NOT guess repository URLs, commands, metrics, numbers, model names, or results.
2) You may ONLY use the provided inputs as evidence (paper text/PDF text/repo files/logs/bench report/metadata/user input).
3) If information is missing or uncertain, leave the target field as null/""/[] and add it to missing_info.
4) Any patch that sets a URL MUST be backed by evidence that quotes the exact full URL string.
5) Any patch that adds/changes a command MUST be backed by evidence quoting the command or an exact snippet that specifies it.
6) If you want to suggest an action that is NOT explicitly written, you must:
   - set basis=\"inference\"
   - mark needs_approval=true
   - set risk to medium/high
   - do NOT include it in patches unless the orchestrator explicitly requests “speculative repairs”.

OUTPUT FORMAT:
- Output ONLY a single JSON object that conforms to the provided JSON schema.
- No Markdown, no extra keys, no explanations outside JSON.

SAFETY:
- Never request or output secrets (API keys, tokens).
- Do not propose destructive commands (rm -rf, sudo, system modifications).
- Do not propose network actions unless explicitly allowed in the input constraints.
"""

EXTRACT_PROMPT_TEMPLATE = """TASK: Extract reproducibility-relevant facts from the provided paper text and propose SPEC PATCHES.
Mode must be \"extract\".

IMPORTANT:
- Only patch fields that have direct evidence quotes.
- If a field is not explicitly present in the inputs, do not fill it.
- suggested_commands must be [] in this mode.

EVIDENCE FORMAT:
- evidence[].id must be like E1, E2, ...
- evidence[].locator must reference the chunk id and a line range if available (e.g., \"chunk:C3 lines:120-140\").
- evidence[].quote must be an exact copy of the relevant snippet (keep it short).

INPUTS:
[METADATA]
paper_id: {paper_id}
arxiv_url: {arxiv_url}
pdf_url: {pdf_url}
current_title: {current_title}
[/METADATA]

[CURRENT_SPEC_YAML]
{current_spec_yaml}
[/CURRENT_SPEC_YAML]

[TEXT_CHUNKS]
{chunked_text_with_ids}
[/TEXT_CHUNKS]

OUTPUT:
Return one JSON object following the schema.
"""

REPAIR_PROMPT_TEMPLATE = """TASK: Diagnose the last run using logs/bench report and propose minimal safe next steps.
Mode must be \"repair\".

HARD RULES:
- Patches MUST be evidence-backed. If not evidence-backed, do NOT patch; propose as suggested_commands with basis=\"inference\" and needs_approval=true.
- Do not propose commands outside ALLOWLIST.
- Do not propose network operations unless allow_network=true.

ALLOWLIST (only these executables are allowed):
{allowlist_executables}

CONSTRAINTS:
- allow_network: {allow_network}
- allow_write_repo: {allow_write_repo}
- allow_package_install: {allow_package_install}
- max_steps: {max_steps}

INPUTS:
[CURRENT_SPEC_YAML]
{current_spec_yaml}
[/CURRENT_SPEC_YAML]

[REPO_FILE_INDEX]
{repo_file_index}
[/REPO_FILE_INDEX]

[REPO_FILE_SNIPPETS]
{repo_file_snippets}
[/REPO_FILE_SNIPPETS]

[LAST_RUN_RESULTS_JSONL]
{last_results_jsonl_lines}
[/LAST_RUN_RESULTS_JSONL]

[STDERR_TAIL]
{stderr_tail}
[/STDERR_TAIL]

[STDOUT_TAIL]
{stdout_tail}
[/STDOUT_TAIL]

[BENCH_REPORT_MD]
{bench_report_md}
[/BENCH_REPORT_MD]

WHAT TO DO:
1) Extract concrete failure signals from logs into evidence[].
2) If you can make an evidence-backed patch, add patches[].
3) Propose the smallest number of suggested_commands.
   - Low risk commands (needs_approval=false) must be strictly supported by repo files or logs.
   - Anything speculative => needs_approval=true, risk medium/high, basis=\"inference\".
4) If you cannot propose a safe next step, set stop=true and explain why in stop_reason.

OUTPUT:
Return one JSON object following the schema.
"""

AGENT_OUTPUT_JSON_SCHEMA = {
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "paper2exp_agent_output",
  "type": "object",
  "additionalProperties": False,
  "required": [
    "mode",
    "patches",
    "evidence",
    "suggested_commands",
    "missing_info",
    "stop",
    "stop_reason"
  ],
  "properties": {
    "mode": { "type": "string", "enum": ["extract", "repair"] },
    "patches": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["op", "path", "value", "basis", "evidence_ids"],
        "properties": {
          "op": { "type": "string", "enum": ["set", "append", "remove"] },
          "path": { "type": "string", "minLength": 1 },
          "value": {},
          "basis": {
            "type": "string",
            "enum": ["paper_quote", "repo_file", "run_log", "bench_report", "user_input", "inference"]
          },
          "evidence_ids": { "type": "array", "items": { "type": "string" }, "minItems": 0 },
          "confidence": { "type": "number", "minimum": 0, "maximum": 1 }
        }
      }
    },
    "evidence": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "source", "locator", "quote"],
        "properties": {
          "id": { "type": "string", "pattern": "^E[0-9]+$" },
          "source": {
            "type": "string",
            "enum": ["paper_text", "pdf_text", "repo_file", "run_log", "bench_report", "metadata", "user_input"]
          },
          "locator": { "type": "string", "minLength": 1 },
          "quote": { "type": "string", "maxLength": 500 },
          "note": { "type": "string", "maxLength": 200 }
        }
      }
    },
    "suggested_commands": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["command", "cwd", "why", "basis", "evidence_ids", "risk", "needs_approval"],
        "properties": {
          "command": { "type": "array", "items": { "type": "string" }, "minItems": 1 },
          "cwd": { "type": "string", "minLength": 1 },
          "why": { "type": "string", "minLength": 1, "maxLength": 400 },
          "basis": {
            "type": "string",
            "enum": ["paper_quote", "repo_file", "run_log", "bench_report", "user_input", "inference"]
          },
          "evidence_ids": { "type": "array", "items": { "type": "string" }, "minItems": 0 },
          "risk": { "type": "string", "enum": ["low", "medium", "high"] },
          "needs_approval": { "type": "boolean" }
        }
      }
    },
    "missing_info": { "type": "array", "items": { "type": "string" } },
    "conflicts": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["field", "values", "evidence_ids"],
        "properties": {
          "field": { "type": "string" },
          "values": { "type": "array", "items": {} },
          "evidence_ids": { "type": "array", "items": { "type": "string" } }
        }
      }
    },
    "stop": { "type": "boolean" },
    "stop_reason": { "type": "string", "maxLength": 300 }
  }
}

DEFAULT_ALLOWLIST_EXECUTABLES = ["python", "pip", "pytest", "bash", "make", "uv", "conda"]
