#!/usr/bin/env python3
"""ASIP Stage 2.5D/E — AI Provider Runner

Explicit CLI entry for AI processing. Default: shows "AI processing disabled".
Must pass --execute to actually run API calls.
"""

import sys
import os
import argparse
import json

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.dirname(_HERE)
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from ai.providers.base import ProviderConfig, BudgetLimit
from ai.workbuddy_worker import claim_batch, ingest_results


def _get_provider(config: ProviderConfig):
    """Return provider instance for config.provider_type."""
    if config.provider_type == "disabled":
        from ai.providers.disabled import DisabledProvider
        return DisabledProvider(config)
    elif config.provider_type == "workbuddy_queue":
        from ai.providers.workbuddy_queue import WorkBuddyQueueProvider
        return WorkBuddyQueueProvider(config)
    elif config.provider_type in ("generic_api", "openai_api"):
        if config.provider_type == "openai_api":
            from ai.providers.openai_api import OpenAIAPIProvider
            return OpenAIAPIProvider(config)
        else:
            from ai.providers.generic_api import GenericAPIProvider
            return GenericAPIProvider(config)
    else:
        raise ValueError("unknown provider: %s" % config.provider_type)


def main(argv=None):
    args = parse_args(argv)
    config = ProviderConfig.from_env()
    budget = BudgetLimit.from_env()

    # Command: run
    if args.command == "run":
        if not args.execute:
            print(json.dumps({
                "status": "idle",
                "message": "AI processing disabled (use --execute to run)",
                "provider": config.provider_type,
                "processing_enabled": config.processing_enabled,
                "paid_fallback_allowed": config.paid_fallback_allowed,
                "max_tasks_per_run": budget.max_tasks,
            }))
            return 0

        provider = _get_provider(config)
        ok, msg = provider.validate_config()
        if not ok:
            print(json.dumps({
                "status": "invalid_config",
                "reason": msg,
            }))
            return 1

        budget_ok, budget_reason = budget.can_process()
        if not budget_ok:
            print(json.dumps({
                "status": "budget_exhausted",
                "reason": budget_reason,
                "completed_tasks": budget.completed_tasks,
                "total_tokens": (budget.total_input_tokens +
                                 budget.total_output_tokens),
            }))
            return 0

        # Claim batch with prompt binding
        result = claim_batch(
            batch_size=min(budget.max_tasks, 3),
            prompt_binding_enabled=True,
            expected_provider=config.provider_type,
            expected_model=provider.model if hasattr(provider, "model")
            else "workbuddy_internal")

        if result.get("batch_id"):
            print(json.dumps({
                "status": "batch_claimed",
                "batch_id": result["batch_id"],
                "task_count": result.get("task_count", 0),
            }))
        else:
            print(json.dumps({
                "status": "no_tasks",
                "cache_hits": result.get("cache_hits", 0),
                "error": result.get("claim_error"),
            }))

        return 0

    # Command: status
    elif args.command == "status":
        provider = _get_provider(config)
        ok, msg = provider.validate_config()
        hc, hc_msg = provider.healthcheck()
        print(json.dumps({
            "provider": config.provider_type,
            "processing_enabled": config.processing_enabled,
            "config_valid": ok,
            "config_message": msg,
            "healthcheck": hc_msg,
            "budget": {
                "max_tasks": budget.max_tasks,
                "max_tokens": budget.max_tokens,
                "max_cost_usd": budget.max_cost_usd,
                "completed": budget.completed_tasks,
            },
        }))
        return 0 if ok else 1

    return 0


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="ASIP AI Provider Runner")
    sub = p.add_subparsers(dest="command", help="command")

    run = sub.add_parser("run", help="claim and possibly execute AI tasks")
    run.add_argument("--execute", action="store_true",
                     help="actually call the AI API (required)")
    run.add_argument("--batch-size", type=int, default=3,
                     help="max tasks per batch")

    sub.add_parser("status", help="show provider config and health")
    return p.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
