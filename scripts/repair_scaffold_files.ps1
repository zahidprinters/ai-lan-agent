$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Write-Exact {
  param(
    [Parameter(Mandatory = $true)][string]$RelativePath,
    [Parameter(Mandatory = $true)][string]$Content
  )
  $full = Join-Path $root $RelativePath
  $parent = Split-Path -Parent $full
  if (-not (Test-Path $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
  }
  Set-Content -Path $full -Value $Content -Encoding utf8
}

$initDirs = @(
  'core','core/model','core/inference','core/quantization',
  'agents','agents/react','agents/planner','agents/executor',
  'memory','memory/short_term','memory/long_term','memory/episodic','memory/summaries',
  'safety','router','learning','learning/dataset','learning/reward','learning/training','learning/registry',
  'runtime','api','api/routes',
  'tools/base','tools/web','tools/system','tools/desktop','tools/android','tools/perception'
)

foreach ($d in $initDirs) {
    Write-Exact "$d/__init__.py" '"""package marker"""'
}

Write-Exact 'core/model/transformer.py' @'
"""Transformer model entrypoint placeholder."""

from training.models.transformer import StackedTransformer

__all__ = ["StackedTransformer"]
'@

Write-Exact 'core/model/tokenizer.py' @'
"""Tokenizer access layer placeholder."""

from tokenizer.factory import load_tokenizer

__all__ = ["load_tokenizer"]
'@

Write-Exact 'core/model/config.py' @'
"""Core config facade for model and inference settings."""

from dataclasses import dataclass


@dataclass
class ModelConfig:
    model_type: str = "transformer"
    device: str = "cpu"
'@

Write-Exact 'core/inference/generate.py' @'
"""Generation facade for future KV-cache focused runtime."""


def generate_text(prompt: str) -> str:
    return prompt
'@

Write-Exact 'core/inference/sampler.py' @'
"""Sampling controls placeholder (temperature, top-k, top-p)."""


def apply_sampling_controls(logits, temperature: float = 1.0):
    _ = temperature
    return logits
'@

Write-Exact 'core/inference/stopping.py' @'
"""Stopping criteria placeholder."""


def should_stop(token_id: int) -> bool:
    _ = token_id
    return False
'@

Write-Exact 'core/quantization/dynamic_int8.py' @'
"""Dynamic int8 quantization facade."""

from scripts.quantize_model import main as quantize_main

__all__ = ["quantize_main"]
'@

Write-Exact 'agents/react/agent.py' @'
"""Main Thought -> Action -> Observation loop skeleton."""

from actions.react_loop import orchestrate_react_payload


def run_react_step(payload: str) -> dict[str, object]:
    return orchestrate_react_payload(payload)
'@

Write-Exact 'agents/react/parser.py' @'
"""Model output to strict action schema parser adapter."""

from actions.action_schema import parse_agent_action

__all__ = ["parse_agent_action"]
'@

Write-Exact 'agents/react/prompt.py' @'
"""Prompt templates for the ReAct agent."""

SYSTEM_PROMPT = "You are AI Lan. Think safely, act minimally, and log every tool call."
'@

Write-Exact 'agents/react/state.py' @'
"""Per-session ReAct state container."""

from dataclasses import dataclass, field


@dataclass
class ReactState:
    thoughts: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)
'@

Write-Exact 'agents/planner/task_planner.py' @'
"""Goal decomposition placeholder."""


def plan_goal(goal: str) -> list[str]:
    return [goal]
'@

Write-Exact 'agents/planner/goal_manager.py' @'
"""Goal lifecycle placeholder."""


class GoalManager:
    def __init__(self) -> None:
        self._goals: list[str] = []

    def add(self, goal: str) -> None:
        self._goals.append(goal)
'@

Write-Exact 'agents/executor/action_executor.py' @'
"""Safe tool execution adapter."""

from actions.router import dispatch_agent_action


def execute_action(payload: dict[str, object], confirmed: bool = False) -> dict[str, object]:
    return dispatch_agent_action(payload, confirmed=confirmed).to_dict()
'@

Write-Exact 'agents/executor/observation.py' @'
"""Observation formatting placeholder."""


def to_observation_text(result: dict[str, object]) -> str:
    return str(result.get("observation", ""))
'@

Write-Exact 'tools/base/tool.py' @'
"""Base tool contract for all adapters."""

from abc import ABC, abstractmethod


class Tool(ABC):
    name: str = "tool"

    @abstractmethod
    def run(self, **kwargs):
        raise NotImplementedError
'@

Write-Exact 'tools/base/registry.py' @'
"""Simple in-memory tool registry."""

from collections.abc import Callable

TOOL_REGISTRY: dict[str, Callable[..., object]] = {}


def register_tool(name: str, handler: Callable[..., object]) -> None:
    TOOL_REGISTRY[name] = handler
'@

Write-Exact 'tools/web/search.py' @'
"""Web search adapter facade."""

from tools.web_search import search_web

__all__ = ["search_web"]
'@

Write-Exact 'tools/web/fetch.py' @'
"""Trusted source fetch facade."""

from tools.web_ingest import fetch_source_content

__all__ = ["fetch_source_content"]
'@

Write-Exact 'tools/web/clean.py' @'
"""Web text cleaning facade."""

from tools.web_ingest import normalize_text

__all__ = ["normalize_text"]
'@

Write-Exact 'tools/system/shell.py' @'
"""Safe shell adapter facade."""

from tools.pc_control import execute_shell

__all__ = ["execute_shell"]
'@

Write-Exact 'tools/system/clipboard.py' @'
"""System clipboard adapter facade."""

from tools.pc_control import read_clipboard

__all__ = ["read_clipboard"]
'@

Write-Exact 'tools/system/files.py' @'
"""Workspace file listing adapter facade."""

from tools.pc_control import list_workspace_files

__all__ = ["list_workspace_files"]
'@

Write-Exact 'tools/desktop/mouse.py' @'
"""Desktop mouse adapter facade."""

from tools.pc_control import move_mouse

__all__ = ["move_mouse"]
'@

Write-Exact 'tools/desktop/keyboard.py' @'
"""Desktop keyboard adapter facade."""

from tools.pc_control import type_text

__all__ = ["type_text"]
'@

Write-Exact 'tools/desktop/screen.py' @'
"""Desktop screenshot placeholder."""


def capture_screen() -> dict[str, str]:
    return {"status": "not_implemented", "detail": "Desktop screenshot adapter pending."}
'@

Write-Exact 'tools/android/adb.py' @'
"""Android ADB adapter facade."""

from tools.android_control import launch_app, list_devices

__all__ = ["list_devices", "launch_app"]
'@

Write-Exact 'tools/android/input.py' @'
"""Android input adapter facade."""

from tools.android_control import swipe_screen, tap_screen

__all__ = ["tap_screen", "swipe_screen"]
'@

Write-Exact 'tools/android/screen.py' @'
"""Android screenshot adapter facade."""

from tools.android_control import capture_screenshot

__all__ = ["capture_screenshot"]
'@

Write-Exact 'tools/perception/ocr.py' @'
"""OCR adapter placeholder for future perception layer."""


def run_ocr(image_path: str) -> dict[str, str]:
    return {"status": "not_implemented", "detail": f"OCR not wired yet: {image_path}"}
'@

Write-Exact 'tools/perception/vision.py' @'
"""Vision adapter placeholder for future perception layer."""


def analyze_image(image_path: str) -> dict[str, str]:
    return {"status": "not_implemented", "detail": f"Vision not wired yet: {image_path}"}
'@

Write-Exact 'memory/short_term/buffer.py' @'
"""Short-term conversation buffer."""

from collections import deque


class ShortTermBuffer:
    def __init__(self, max_items: int = 20) -> None:
        self._items = deque(maxlen=max_items)

    def add(self, message: str) -> None:
        self._items.append(message)

    def get_all(self) -> list[str]:
        return list(self._items)
'@

Write-Exact 'memory/long_term/vector_store.py' @'
"""Vector store adapter placeholder."""


class VectorStore:
    def upsert(self, key: str, text: str) -> None:
        _ = (key, text)

    def query(self, query_text: str, limit: int = 5) -> list[str]:
        _ = (query_text, limit)
        return []
'@

Write-Exact 'memory/long_term/embeddings.py' @'
"""Embedding adapter placeholder."""


def embed_text(text: str) -> list[float]:
    _ = text
    return []
'@

Write-Exact 'memory/long_term/retrieval.py' @'
"""Long-term retrieval facade."""

from tools.memory_store import retrieve_relevant_memories

__all__ = ["retrieve_relevant_memories"]
'@

Write-Exact 'memory/episodic/actions_log.py' @'
"""Episodic memory facade for action logs."""

from actions.router import append_action_audit_log

__all__ = ["append_action_audit_log"]
'@

Write-Exact 'memory/summaries/summarizer.py' @'
"""Summary generation facade."""

from tools.memory_store import summarize_entries

__all__ = ["summarize_entries"]
'@

Write-Exact 'safety/policy_engine.py' @'
"""Policy engine facade."""

from actions.policy import evaluate_action_policy

__all__ = ["evaluate_action_policy"]
'@

Write-Exact 'safety/validator.py' @'
"""Input validation facade for action schema."""

from actions.action_schema import parse_agent_action

__all__ = ["parse_agent_action"]
'@

Write-Exact 'safety/sandbox.py' @'
"""Sandbox policy placeholder."""


def can_execute(action_name: str) -> bool:
    _ = action_name
    return True
'@

Write-Exact 'safety/confirmation.py' @'
"""User confirmation helper."""


def requires_confirmation(action_name: str) -> bool:
    return action_name in {
        "pc.type_text",
        "pc.open_app",
        "android.launch_app",
        "android.tap",
        "android.swipe",
        "android.capture_screenshot",
    }
'@

Write-Exact 'router/router.py' @'
"""Router facade to dispatch validated actions."""

from actions.router import dispatch_agent_action

__all__ = ["dispatch_agent_action"]
'@

Write-Exact 'router/schema.py' @'
"""Schema facade for action payloads."""

from actions.action_schema import AgentAction, parse_agent_action

__all__ = ["AgentAction", "parse_agent_action"]
'@

Write-Exact 'learning/dataset/builder.py' @'
"""Nightly learning dataset builder placeholder."""


def build_dataset() -> dict[str, object]:
    return {"status": "not_implemented"}
'@

Write-Exact 'learning/dataset/filter.py' @'
"""Learning dataset filter placeholder."""


def filter_samples(samples: list[str]) -> list[str]:
    return samples
'@

Write-Exact 'learning/reward/reward_model.py' @'
"""Reward model placeholder."""


def score_output(text: str) -> float:
    _ = text
    return 0.0
'@

Write-Exact 'learning/training/finetune.py' @'
"""Fine-tuning placeholder."""


def run_finetune() -> dict[str, str]:
    return {"status": "not_implemented"}
'@

Write-Exact 'learning/training/eval.py' @'
"""Learning evaluation placeholder."""


def evaluate_candidate() -> dict[str, str]:
    return {"status": "not_implemented"}
'@

Write-Exact 'learning/registry/model_registry.py' @'
"""Model registry facade."""

from scripts.model_registry import record_model_entry

__all__ = ["record_model_entry"]
'@

Write-Exact 'runtime/session.py' @'
"""Session state placeholder."""


class RuntimeSession:
    def __init__(self) -> None:
        self.id = "local-session"
'@

Write-Exact 'runtime/context.py' @'
"""Runtime context assembly facade."""

from tools.context_builder import build_prompt_context

__all__ = ["build_prompt_context"]
'@

Write-Exact 'runtime/scheduler.py' @'
"""Background scheduler placeholder."""


def schedule_task(task_name: str) -> dict[str, str]:
    return {"status": "queued", "task": task_name}
'@

Write-Exact 'api/routes/health.py' @'
"""Health route placeholder."""


def health() -> dict[str, str]:
    return {"status": "ok"}
'@

Write-Output 'Scaffold repair completed.'
