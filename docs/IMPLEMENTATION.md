# Aegis — Implementation Details

## Form Factor

Aegis is a **CLI tool** installed via pip:

```bash
pip install aegis-dev
```

Two modes of operation:
- **Interactive** (`aegis plan`) — Terminal-based conversation for the Planning Advisor
- **Autonomous** (`aegis build`, `aegis review`) — Runs pipeline stages without user interaction, outputs progress to stdout

A TUI upgrade (using `textual`) and web dashboard are future enhancements, not MVP requirements.

## Project Structure

```
aegis/
├── cli/                      # CLI entry points
│   ├── __init__.py
│   ├── main.py               # aegis command router
│   ├── plan.py               # aegis plan (interactive session)
│   ├── build.py              # aegis build (autonomous pipeline)
│   ├── review.py             # aegis review (autonomous pipeline)
│   ├── status.py             # aegis status
│   └── config.py             # aegis config
│
├── pipeline/                 # LangGraph pipeline definitions
│   ├── __init__.py
│   ├── graph.py              # Top-level pipeline state machine
│   ├── plan_stage.py         # Stage 1: Planning Advisor + Readiness Gate
│   ├── build_stage.py        # Stage 2: Test/Impl/Debug agents + runners
│   └── review_stage.py       # Stage 3: Code Review + Documentation
│
├── agents/                   # Agent role definitions (prompts + behavior)
│   ├── __init__.py
│   ├── planning_advisor.py
│   ├── test_agent.py
│   ├── impl_agent.py
│   ├── debug_agent.py
│   ├── fresh_agent.py
│   ├── code_reviewer.py
│   └── doc_generator.py
│
├── engines/                  # AI engine adapters
│   ├── __init__.py
│   ├── base.py               # Abstract engine interface
│   ├── gemini_cli.py         # Wraps `gemini -p` subprocess
│   ├── claude_cli.py         # Wraps `claude -p --print` subprocess
│   ├── codex_cli.py          # Wraps `codex` subprocess
│   ├── anthropic_api.py      # Direct Anthropic API calls
│   ├── openai_api.py         # Direct OpenAI API calls
│   ├── google_api.py         # Direct Google AI API calls
│   └── ollama.py             # Local models via Ollama
│
├── schemas/                  # JSON Schema definitions
│   ├── plan_document.json
│   ├── build_report.json
│   ├── review_report.json
│   ├── planning_session.json
│   └── readiness_result.json
│
├── validation/               # Schema validation + Readiness Gate
│   ├── __init__.py
│   ├── schema_validator.py   # JSON Schema validation (mechanical)
│   └── readiness_gate.py     # PlanDocument readiness checklist
│
├── runners/                  # Isolated execution environments
│   ├── __init__.py
│   ├── docker_runner.py      # Docker-based test execution
│   ├── mutation_runner.py    # Mutation testing orchestration
│   └── workspace.py          # Isolated workspace creation per agent
│
├── memory/                   # Project Memory (SQLite)
│   ├── __init__.py
│   ├── store.py              # CRUD operations on project memory
│   └── models.py             # Data models for memory entries
│
└── config/                   # Configuration management
    ├── __init__.py
    ├── defaults.py           # Default thresholds, loop limits, etc.
    └── loader.py             # Reads .aegis/config.toml
```

## Engine Adapter Interface

Every AI engine adapter implements this interface:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class EngineResponse:
    content: str
    usage: dict          # tokens in/out, cost if available
    model: str           # which model actually responded
    raw: dict            # engine-specific metadata

class EngineAdapter(ABC):

    @abstractmethod
    def invoke(self, prompt: str, system_prompt: str,
               working_directory: str) -> EngineResponse:
        """Single-turn invocation. Used by Build/Review stage agents."""
        ...

    @abstractmethod
    def stream(self, prompt: str, system_prompt: str,
               working_directory: str):
        """Streaming invocation. Used by Planning Advisor for
        real-time conversation display."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this engine is installed and authenticated."""
        ...
```

### Gemini CLI Adapter (subprocess wrapper)

```python
class GeminiCLIAdapter(EngineAdapter):

    def invoke(self, prompt, system_prompt, working_directory):
        result = subprocess.run(
            ["gemini", "-p", prompt, "--output-format", "json"],
            capture_output=True, text=True,
            cwd=working_directory,
            env={**os.environ, "GEMINI_SYSTEM_PROMPT": system_prompt}
        )
        parsed = json.loads(result.stdout)
        return EngineResponse(
            content=parsed["response"],
            usage=parsed.get("stats", {}),
            model="gemini-cli",
            raw=parsed
        )
```

### Claude Code Adapter (subprocess wrapper)

```python
class ClaudeCodeAdapter(EngineAdapter):

    def invoke(self, prompt, system_prompt, working_directory):
        result = subprocess.run(
            ["claude", "-p", prompt,
             "--output-format", "json", "--bare",
             "--system-prompt", system_prompt],
            capture_output=True, text=True,
            cwd=working_directory
        )
        parsed = json.loads(result.stdout)
        return EngineResponse(
            content=parsed["result"],
            usage=parsed.get("usage", {}),
            model="claude-code",
            raw=parsed
        )
```

### Direct API Adapter (example: Anthropic)

```python
class AnthropicAPIAdapter(EngineAdapter):

    def invoke(self, prompt, system_prompt, working_directory):
        response = self.client.messages.create(
            model=self.model_name,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096
        )
        return EngineResponse(
            content=response.content[0].text,
            usage={"input": response.usage.input_tokens,
                   "output": response.usage.output_tokens},
            model=self.model_name,
            raw=response.model_dump()
        )
```

## Adversarial Workspace Isolation

The `workspace.py` module enforces agent separation at the filesystem level:

```python
class AgentWorkspace:
    """Creates and manages isolated directories per agent invocation.
    Each agent can ONLY see files explicitly placed in its workspace."""

    def create_for_test_agent(self, plan_document_path: str) -> str:
        workspace = tempfile.mkdtemp(prefix="aegis-test-")
        shutil.copy(plan_document_path, Path(workspace) / "plan.json")
        # Nothing else. No source code, no other agent output.
        return workspace

    def create_for_impl_agent(self, plan_document_path: str) -> str:
        workspace = tempfile.mkdtemp(prefix="aegis-impl-")
        shutil.copy(plan_document_path, Path(workspace) / "plan.json")
        # No tests, no test agent output.
        return workspace

    def create_for_debug_agent(self, plan_path: str,
                                source_dir: str,
                                test_output: str) -> str:
        workspace = tempfile.mkdtemp(prefix="aegis-debug-")
        shutil.copy(plan_path, Path(workspace) / "plan.json")
        shutil.copytree(source_dir, Path(workspace) / "src")
        Path(workspace, "test_output.txt").write_text(test_output)
        # Has the code + raw test output. Does NOT have the test
        # agent's reasoning or the test suite source.
        return workspace
```

When Aegis spawns a CLI tool (Gemini, Claude, etc.), it sets `cwd` to the agent's workspace. The tool can only read files in that directory. This is filesystem-level enforcement -- not a prompt instruction the agent can ignore.

## Authentication & Cost Strategy

### Recommended Setup (Zero API cost)

```toml
# .aegis/config.toml

[engines.default]
type = "gemini-cli"
# Uses Google account auth (1000 free requests/day on Flash)
# Run `gemini auth login` once to authenticate

[engines.quality]
type = "claude-cli"
# Uses Claude Pro/Max subscription (included, no per-call cost)
# Run `claude auth login` once to authenticate
```

### Per-Role Engine Assignment

```toml
[roles]
planning_advisor = "quality"    # Claude -- needs deep reasoning
test_agent = "default"          # Gemini -- cheaper, spec-to-test is simpler
impl_agent = "quality"          # Claude -- complex code generation
mutation_tester = "default"     # Gemini -- high volume, simpler task
debug_agent = "default"         # Gemini -- fast iteration, switch to quality on escalation
code_reviewer = "quality"       # Claude -- needs careful analysis
doc_generator = "default"       # Gemini -- documentation is straightforward
```

### Cost Estimation Per Build Cycle

With the above config (Gemini free tier + Claude Pro subscription):

| Agent | Engine | Invocations per cycle | Cost |
|-------|--------|----------------------|------|
| Planning Advisor | Claude CLI | 5-15 turns | $0 (subscription) |
| Test Agent | Gemini CLI | 1-3 | $0 (free tier) |
| Mutation Tester | Gemini CLI | 3-10 | $0 (free tier) |
| Impl Agent | Claude CLI | 1-2 | $0 (subscription) |
| Test Runner | Docker | 5-20 | $0 (local compute) |
| Debug Agent | Gemini CLI | 0-9 | $0 (free tier) |
| Code Reviewer | Claude CLI | 1 | $0 (subscription) |
| Doc Generator | Gemini CLI | 1 | $0 (free tier) |
| **Total** | | ~20-60 invocations | **$0 per cycle** |

With API keys instead of subscriptions, estimated $0.50-3.00 per build cycle depending on complexity and model choice.

## CLI Commands

```
aegis init [project-name]      Initialize Aegis in a project directory
aegis config [key] [value]     Configure engines, thresholds, roles
aegis plan                     Start interactive planning session
aegis build                    Run build pipeline on latest PlanDocument
aegis build --plan <id>        Run build on a specific PlanDocument
aegis review                   Run review on latest BuildReport
aegis status                   Show pipeline state and recent documents
aegis docs                     Display project memory / documentation
aegis history                  Show document chain for a task
aegis inspect <document-id>    Pretty-print any interface document
```

## .aegis/ Project Directory

Created by `aegis init` in the project root:

```
.aegis/
├── config.toml               # Engine config, thresholds, role assignments
├── documents/                 # All interface documents (JSON)
│   ├── sessions/              # PlanningSession transcripts
│   ├── plans/                 # PlanDocuments
│   ├── builds/                # BuildReports
│   └── reviews/               # ReviewReports
├── workspaces/                # Temporary, cleaned after each build cycle
├── memory/
│   └── project.db             # SQLite project memory
└── schemas/                   # JSON Schema files (copied on init, can be customized)
```

## Dependencies

```
# Core
langgraph >= 0.3
langchain-core >= 0.3
jsonschema >= 4.0

# Engine adapters (optional, user installs what they need)
anthropic >= 0.40         # For direct Anthropic API
openai >= 1.60            # For direct OpenAI API
google-genai >= 1.0       # For direct Google AI API

# Execution
docker >= 7.0             # For isolated test runner

# CLI
click >= 8.0              # CLI framework
rich >= 13.0              # Terminal formatting and progress display
```
