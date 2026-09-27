"""Multi-Agent Skill Optimizer using NVIDIA NIM / OpenAI-compatible API.

3 agents work together to improve agent skills:
  Executor: runs the skill against test scenarios, scores outputs, analyzes skills
  Analyst: diagnoses why evals failed, picks a mutation strategy
  Mutator: makes one targeted fix per round
"""

import json
import os
import re
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

load_dotenv()



# -- Pydantic schemas for structured agent output ----------------------------


class FailureAnalysis(BaseModel):
    diagnosis: str = Field(description="Root cause of failures")
    mutation_strategy: str = Field(
        description="One of: add_example, add_constraint, restructure, add_edge_case"
    )
    target_section: str = Field(description="Which part of the skill to change")
    suggested_change: str = Field(description="What specific change to make")


class SkillMutation(BaseModel):
    description: str = Field(description="Short description of the change made")
    reasoning: str = Field(description="Why this change should help")
    new_skill_md: str = Field(description="The full updated SKILL.md content")


# -- System instructions for agent roles -------------------------------------

EXECUTOR_INSTRUCTION = (
    "You are a versatile skill execution agent. You have three modes:\n\n"
    "1. EXECUTE MODE: Given a skill's instructions and a user request, "
    "produce the output that skill would generate. Follow the instructions "
    "exactly. No meta-commentary.\n\n"
    "2. ANALYZE MODE: Given a skill definition, generate test scenarios "
    "and evaluation criteria. Return valid JSON only.\n\n"
    "3. SCORE MODE: Given an output and evaluation criteria, score the "
    "output against each criterion. Return valid JSON only."
)

ANALYST_INSTRUCTION = (
    "You diagnose why agent skill evaluations fail.\n"
    "Given failed eval results, identify the root cause and suggest "
    "a specific fix. Pick one mutation_strategy from: "
    "add_example, add_constraint, restructure, or add_edge_case.\n"
    "Return valid JSON only matching the schema:\n"
    "{\n"
    '  "diagnosis": "Root cause of failures",\n'
    '  "mutation_strategy": "add_example | add_constraint | restructure | add_edge_case",\n'
    '  "target_section": "Which part of the skill to change",\n'
    '  "suggested_change": "What specific change to make"\n'
    "}"
)

MUTATOR_INSTRUCTION = (
    "You edit agent skill files. Given a SKILL.md and a diagnosis, "
    "make exactly ONE targeted change. Keep the YAML frontmatter and "
    "overall structure intact. Return valid JSON only matching the schema:\n"
    "{\n"
    '  "description": "Short description of the change made",\n'
    '  "reasoning": "Why this change should help",\n'
    '  "new_skill_md": "The full updated SKILL.md content"\n'
    "}"
)


# -- Optimizer ---------------------------------------------------------------


class SkillOptimizer:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ):
        load_dotenv()
        resolved_api_key = (
            api_key
            or os.environ.get("NVIDIA_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or ""
        ).strip()

        resolved_base_url = (
            base_url
            or os.environ.get("NVIDIA_BASE_URL")
            or os.environ.get("OPENAI_BASE_URL")
            or os.environ.get("GEMINI_BASE_URL")
        )

        default_model = "meta/llama-3.3-70b-instruct"
        if not resolved_base_url:
            if resolved_api_key.startswith("AIza") or (model and "gemini" in model.lower()) or os.environ.get("GEMINI_API_KEY"):
                resolved_base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
                default_model = os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
            elif resolved_api_key.startswith("nvapi-") or os.environ.get("NVIDIA_API_KEY"):
                resolved_base_url = "https://integrate.api.nvidia.com/v1"
                default_model = os.environ.get("NVIDIA_MODEL") or "nvidia/nemotron-3.5-lightning-30b-a3b"
            elif resolved_api_key.startswith("sk-") or os.environ.get("OPENAI_API_KEY"):
                resolved_base_url = "https://api.openai.com/v1"
                default_model = os.environ.get("OPENAI_MODEL") or "gpt-4o"
            else:
                resolved_base_url = "https://integrate.api.nvidia.com/v1"

        if not resolved_api_key:
            raise ValueError(
                "No API key provided. Please enter an API key in the interface or set NVIDIA_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY in backend environment variables."
            )

        self.model = (
            model
            or os.environ.get("NVIDIA_MODEL")
            or os.environ.get("OPENAI_MODEL")
            or os.environ.get("GEMINI_MODEL")
            or default_model
        )
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.client = AsyncOpenAI(
            api_key=resolved_api_key,
            base_url=resolved_base_url,
        )

    # -- Agent runner helpers ------------------------------------------------

    async def _ask(
        self,
        instruction: str,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Run an LLM call with system instruction and user prompt."""
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": prompt},
        ]
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
        )
        choice = response.choices[0]
        content = choice.message.content or ""
        if not content and hasattr(choice.message, "reasoning_content"):
            content = getattr(choice.message, "reasoning_content") or ""
        return content.strip()

    async def _ask_json(
        self,
        instruction: str,
        prompt: str,
        schema: Optional[type[BaseModel]] = None,
        fallback: Optional[Any] = None,
    ) -> Any:
        """Run an LLM call and parse the JSON response robustly."""
        json_prompt = (
            f"{prompt}\n\nIMPORTANT: Respond with valid JSON only. Do not include markdown codeblocks or extra text."
        )
        text = await self._ask(instruction, json_prompt)

        # 1. Look for ```json ... ``` codeblocks anywhere in text
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            clean_text = match.group(1).strip()
        else:
            clean_text = text.strip()

        # 2. Try parsing directly
        try:
            parsed = json.loads(clean_text)
            if schema:
                return schema.model_validate(parsed).model_dump()
            return parsed
        except Exception:
            pass

        # 3. Try finding outermost JSON object or array bounds
        idx_brace = clean_text.find("{")
        idx_bracket = clean_text.find("[")
        starts = [i for i in (idx_brace, idx_bracket) if i != -1]
        if starts:
            start_idx = min(starts)
            end_brace = clean_text.rfind("}")
            end_bracket = clean_text.rfind("]")
            end_idx = max(end_brace, end_bracket)
            if end_idx > start_idx:
                json_sub = clean_text[start_idx : end_idx + 1]
                try:
                    parsed = json.loads(json_sub)
                    if schema:
                        return schema.model_validate(parsed).model_dump()
                    return parsed
                except Exception:
                    pass

                # Try raw_decode as additional fallback
                decoder = json.JSONDecoder()
                try:
                    result, _ = decoder.raw_decode(clean_text, start_idx)
                    if schema and isinstance(result, dict):
                        return schema.model_validate(result).model_dump()
                    return result
                except Exception:
                    pass

        if fallback is not None:
            return fallback

        raise ValueError(f"Failed to parse JSON from LLM output: {text[:200]}")

    # -- Public API -----------------------------------------------------------

    async def analyze_skill(self, skill_files: dict) -> dict:
        """Generate test scenarios and eval criteria from skill files."""
        skill_md = next(
            (v for k, v in skill_files.items() if k.endswith("SKILL.md")), ""
        )
        refs = {k: v for k, v in skill_files.items() if "references/" in k}
        ref_text = ""
        if refs:
            ref_text = "\n\nReference files:\n" + "\n---\n".join(
                f"## {k}\n{v}" for k, v in refs.items()
            )

        prompt = (
            f"Analyze this agent skill and generate test scenarios "
            f"with evaluation criteria.\n\n"
            f"# SKILL.md\n{skill_md}\n{ref_text}\n\n"
            f"Generate:\n"
            f"1. 3-4 diverse test scenarios (realistic user inputs)\n"
            f"2. 4-6 binary yes/no evaluation criteria\n\n"
            f"Return JSON:\n"
            f'{{"scenarios": [{{"id": 1, "name": "short name", "description": "short name", '
            f'"input": "the user request to test"}}], '
            f'"evals": [{{"id": 1, "name": "what to check", "criterion": "what to check", '
            f'"question": "yes/no question about the output", '
            f'"pass_condition": "what yes looks like", "fail_condition": "what no looks like"}}]}}'
        )
        return await self._ask_json(EXECUTOR_INSTRUCTION, prompt)

    async def optimize(
        self,
        skill_files: dict,
        scenarios: list,
        evals: list,
        max_rounds: int = 5,
        callback: Optional[Callable] = None,
    ) -> dict:
        """Run the optimization loop with 3 agent roles."""

        async def emit(event):
            if callback:
                await callback(event)

        skill_md = next(
            (v for k, v in skill_files.items() if k.endswith("SKILL.md")), ""
        )
        current_md = skill_md
        score_history = []
        mutation_log = []

        # -- Baseline ---------------------------------------------------------
        baseline = await self._score_skill(current_md, scenarios, evals)
        baseline_pct = round(100 * baseline["passed"] / max(baseline["total"], 1), 1)
        score_history.append(baseline_pct)

        await emit({
            "type": "baseline",
            "data": {
                "score": baseline_pct,
                "passed": baseline["passed"],
                "total": baseline["total"],
                "per_eval": baseline["per_eval"],
            },
        })

        # -- Rounds -----------------------------------------------------------
        for rnd in range(1, max_rounds + 1):
            await emit({"type": "experiment_start", "data": {"round": rnd}})

            # Analyst diagnoses worst failure
            analysis = await self._analyze_failures(
                current_md, scenarios, evals, baseline["details"]
            )

            # Mutator applies fix
            mutation = await self._mutate_skill(current_md, analysis)
            new_md = mutation.get("new_skill_md", current_md)

            # Re-score
            result = await self._score_skill(new_md, scenarios, evals)
            new_pct = round(100 * result["passed"] / max(result["total"], 1), 1)

            kept = new_pct > baseline_pct
            entry = {
                "round": rnd,
                "strategy_type": analysis.get("mutation_strategy", "unknown"),
                "diagnosis": analysis.get("diagnosis", ""),
                "description": mutation.get("description", ""),
                "score_before": baseline_pct,
                "score_after": new_pct,
                "kept": kept,
            }
            mutation_log.append(entry)

            if kept:
                current_md = new_md
                baseline = result
                baseline_pct = new_pct

            score_history.append(baseline_pct)

            await emit({
                "type": "experiment_result",
                "data": {
                    "round": rnd,
                    "score": new_pct,
                    "kept": kept,
                    "status": "kept" if kept else "discarded",
                    "description": mutation.get("description", ""),
                    "strategy": analysis.get("mutation_strategy", ""),
                    "per_eval": result["per_eval"],
                },
            })

        # -- Done -------------------------------------------------------------
        final_pct = baseline_pct
        await emit({
            "type": "complete",
            "data": {
                "baseline_score": score_history[0],
                "final_score": final_pct,
                "improved_skill_md": current_md,
                "score_history": score_history,
                "mutation_log": mutation_log,
                "strategy_stats": self._strategy_stats(mutation_log),
            },
        })

        return {
            "baseline_score": score_history[0],
            "final_score": final_pct,
            "improved_skill_md": current_md,
            "score_history": score_history,
            "mutation_log": mutation_log,
        }

    # -- Internal helpers -----------------------------------------------------

    async def _score_skill(self, skill_md, scenarios, evals):
        """Executor runs all scenarios, then scores outputs."""
        all_results = []
        total_passed = 0
        total_checks = 0
        per_eval = {e["id"]: {"passed": 0, "total": 0} for e in evals}

        for sc in scenarios:
            # Executor runs the skill (free-form text)
            output = await self._ask(
                EXECUTOR_INSTRUCTION,
                f"Execute this skill:\n\n{skill_md}\n\nUser request:\n{sc['input']}",
            )
            # Executor scores the output (JSON)
            scoring = await self._ask_json(
                EXECUTOR_INSTRUCTION,
                (
                    f"Evaluate this output against the criteria.\n\n"
                    f"Input: {sc['input']}\n\n"
                    f"Output: {output}\n\n"
                    f"Criteria:\n{json.dumps(evals, indent=2)}\n\n"
                    f"Return JSON: {{\"results\": [{{\"eval_id\": 1, \"passed\": true, \"reason\": \"...\"}}]}}"
                ),
                fallback={"results": []},
            )
            scores = scoring.get("results", []) if isinstance(scoring, dict) else scoring

            for s in scores:
                eid = s.get("eval_id")
                passed = s.get("passed", False)
                if passed:
                    total_passed += 1
                total_checks += 1
                if eid in per_eval:
                    per_eval[eid]["total"] += 1
                    if passed:
                        per_eval[eid]["passed"] += 1
                all_results.append({**s, "scenario_id": sc["id"]})

        return {
            "passed": total_passed,
            "total": total_checks,
            "per_eval": [
                {
                    "eval_id": k,
                    **v,
                    "pass_rate": round(v["passed"] / max(v["total"], 1) * 100, 1),
                }
                for k, v in per_eval.items()
            ],
            "details": all_results,
        }

    async def _analyze_failures(self, skill_md, scenarios, evals, details):
        """Analyst agent diagnoses the worst failures."""
        failed = [d for d in details if not d.get("passed")]
        if not failed:
            return {
                "diagnosis": "All passed",
                "mutation_strategy": "add_constraint",
                "target_section": "N/A",
                "suggested_change": "none",
            }

        return await self._ask_json(
            ANALYST_INSTRUCTION,
            (
                f"Diagnose these failures and suggest ONE fix.\n\n"
                f"Skill:\n{skill_md[:2000]}\n\n"
                f"Failed evals:\n{json.dumps(failed[:5], indent=2)}"
            ),
            schema=FailureAnalysis,
            fallback={
                "diagnosis": "Unable to diagnose",
                "mutation_strategy": "add_constraint",
                "target_section": "unknown",
                "suggested_change": "unclear",
            },
        )

    async def _mutate_skill(self, skill_md, analysis):
        """Mutator agent makes one targeted change."""
        return await self._ask_json(
            MUTATOR_INSTRUCTION,
            (
                f"Apply this fix to the skill. Make ONE change only.\n\n"
                f"SKILL.md:\n{skill_md}\n\n"
                f"Diagnosis: {analysis.get('diagnosis')}\n"
                f"Strategy: {analysis.get('mutation_strategy')}\n"
                f"Target: {analysis.get('target_section')}\n"
                f"Change: {analysis.get('suggested_change')}"
            ),
            schema=SkillMutation,
            fallback={
                "description": "Failed to parse mutation",
                "reasoning": "",
                "new_skill_md": skill_md,
            },
        )

    @staticmethod
    def _strategy_stats(mutation_log):
        stats = {}
        for m in mutation_log:
            s = m.get("strategy_type", "unknown")
            if s not in stats:
                stats[s] = {"total": 0, "kept": 0}
            stats[s]["total"] += 1
            if m.get("kept"):
                stats[s]["kept"] += 1
        return stats