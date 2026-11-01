# Knowing When We Do Not Know: prototype AI research loop

Prototype accompanying the Stage 1 proposal "Knowing When We Do Not Know: An AI Research Loop for Identifying Organizational Mechanisms" (Organization Science special issue, AI-Enabled Frontiers in Organizational Science).

The loop asks a model to formalize response profiles for a registered family of candidate mechanisms (compliance pressure N, informational reliance I, shared erroneous information S), checks identification and compatibility without giving the model simulator truth, and returns feedback for a revision round. Appropriate abstention is scored as success. Protocol details are in `AI_LOOP_PROTOCOL.md`.

## Requirements

Python 3.10 or later. No third-party packages.

## Reproduce without an API key

```bash
python -m unittest discover -p 'test_*.py'     # 44 offline tests
python run_local.py --dry-run --tasks 12       # mocked 12 tasks x 4 arms, no network
```

## Replay the recorded version 2 pilot

`results/20261010T000215Z_648e6f33/` holds the full version 2 run (12 tasks x 4 arms, 48 calls, model alias `azure/gpt-5.2` via an institutional LiteLLM proxy). `results/20261010T000148Z_b9a3652f/` is the 1-task feasibility run. Recompute the summary from the raw attempt and provider logs (work on a copy, since the script rewrites summary files):

```bash
cp -r results/20261010T000215Z_648e6f33 /tmp/replay
python summarize_run.py /tmp/replay
```

## Run live

```bash
export OPENAI_API_KEY=...            # never written to logs or results
export OPENAI_API_BASE=...           # optional, for an OpenAI-compatible proxy
python run_local.py --model <exact-model-id> --tasks 1    # 4 requests
python run_local.py --model <exact-model-id> --tasks 12   # 48 requests
```

## Files

- `pilot/public_tasks.json`: the 12 public tasks given to the model.
- `pilot/evaluator_only.json`: evaluator-side truth, never sent to the model. It is included so reviewers can replay scoring.
- `RUN_NOTE_v2.txt`, `VERIFICATION.json`: run conditions and offline verification record.
- `README_ZH.md`, `RESULTS_REVIEW_v2_ZH.md`: original Chinese run guide and results review.
- `ETHICS_NOTE.md`: Stage 1 ethics and dual-use note (no human participants; synthetic tasks; redacted logs).
- `AI_LOOP_PROTOCOL.md`: loop protocol and the planned prospective comparison.

## Scope and caveats

Constructed tasks, descriptive results only. Arms share initial outputs, so cases are dependent; no significance tests and no general AI-superiority claim. Version 2 fixed interface problems found in version 1 after observing it, so the two versions are not one pre-registered experiment. The model name is a proxy alias, not a verified snapshot; the proxy URL has been replaced with `<institutional-litellm-proxy>` in the logs.

## Ethics and data

All tasks are constructed (synthetic) response profiles; no human participants were involved in Stage 1. Provider logs are redacted: no API keys, account identifiers, or gateway URLs. Version 1 results are kept outside this repository and are not pooled with version 2. See `ETHICS_NOTE.md`.

## License

MIT, see `LICENSE`.
