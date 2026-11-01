# Candidate generation and revision protocol

## Research capability and implementation status

The candidate loop accepts arbitrary finite response profiles in a bounded JSON
contract, checks identification and compatibility without receiving simulator
truth, and sends the actual feedback to a subsequent generation round. It records
every requested attempt, including invalid outputs and transport failures. A
provider-neutral command adapter allows a separately configured model wrapper;
offline tests exercise the same protocol. No live model run has been completed
in the preparation environment. Authored test responses are regression cases,
not natural AI errors or evidence of AI performance.

## Reproduce the protocol demonstration

Run from this directory with Python 3.10 or later:

```bash
python -m unittest discover -v
python run_local.py --dry-run --tasks 12
python run_local.py --model YOUR_MODEL_ID --tasks 12
```

The regression tests deliberately assert a unique mechanism from baseline
evidence. The checker retains three compatible families and reports structural
ambiguity and an unsupported singleton. A revision may receive that feedback
and return a scoped abstention. The checker does not require the model to obey
feedback and records continuing errors. Tests demonstrate routing, not learning
effectiveness. Live behavior must be measured from local API runs.

A trusted provider wrapper can be substituted using `--command-json` with a
JSON argv array. It reads one request from stdin and returns one raw candidate
JSON document on stdout. Configure authentication in that wrapper; do not place
credentials in task files. Record provider and exact model version, sampling
settings, prompt, response, usage and monetary cost in the wrapper's separate
run log. The harness records wall time; it does not infer missing token usage or
authenticate whether a transport is a language model. Use an accessible model
with archived artifacts for independent reproduction.

## Candidate and evidence contract

Every family contains an ID, an organizational mechanism description and one
or more nuisance profiles. Each profile maps every registered intervention to
an explicit probability. Probabilities may be rationals. This initial adapter
cannot translate arbitrary theories or discover causal equations. It checks a
finite formal representation. Textual assumptions and organizational meaning
remain unverified. It never executes generated code.

Public input contains only task ID, question, intervention names, observed
counts and alpha. Hidden-world labels and evaluation targets belong in an
independent evaluator. Strict fields prevent accidental direct truth input but
do not guarantee that a natural-language question contains no clue: prospective
benchmark construction needs a separate leakage audit.

The checker returns compatible families, exact design distances, unsupported
claim feedback and conditional suggestions for unused interventions. A
singleton supports a candidate-scoped claim only. Neither declared assumptions
nor an empty compatible set verify completeness or empirical validity. Aliased
omitted mechanisms remain undetectable.

## Prospective comparison

Preregister a pilot of 12 task-design combinations and two accessible model
configurations. Generate five initial outputs per cell, retain all 120 planned
initial attempts including failures, and branch each output into four arms:

1. Initial answer alone.
2. One self-revision with the same public evidence and no checker feedback.
3. One revision with schema/format feedback only.
4. One revision with evidence-limit feedback and conditional experiment options.

Use common initial outputs, matched generation settings and the same evidence.
Arms 2 to 4 receive equal output-token ceilings and one additional call; report
actual elapsed time, tokens and cost rather than claiming exact computational
equivalence. Initial-answer comparisons quantify gains and additional cost;
the other controls separate extra reasoning and formatting help from substantive
evidence feedback. Prospective model errors and authored faults are separate
analysis strata. No failed generation is silently repaired or dropped. These
pilot sizes estimate feasibility, not a powered population effect.

After freezing candidate families, compare candidate-directed and random
experiment selection under matched evidence budgets. Use independently
generated holdout batches for post-revision compatibility checks, with a
preregistered allocation of error across looks. The current fixed-batch bands
do not provide a joint guarantee for adaptive candidate revision on reused data.
Candidate revisions and new-data acquisition must be separately timestamped.

Outcomes include unsupported singleton claims, supported conditional claims,
unnecessary abstention, representation failures, semantic disagreement, time
and cost to a discriminating experiment, and unresolved branches investigated.
Jointly report risk and coverage. Proposed decision rule: demonstrate a
preregistered reduction in unsupported claims at matched evidence while
supported-claim opportunities and exploration costs satisfy prespecified pilot-
informed margins. No success threshold is chosen after seeing comparative data.

## Additional organizational tasks and human roles

Extend from team authority to escalation of commitment (sunk-cost attachment,
reputational protection, updated expected returns) and organizational silence
(retaliation concerns, futility, shared interpretation). Register cross-channel
effects and mixtures; compare conclusions when strong exclusion restrictions
are relaxed. These are planned families, not established empirical findings.

Researchers check whether formal profiles adequately express organizational
claims and authorize substantive design changes. They do not certify truth by
approval. Automate routine numerical checks and surface consequential scope
changes. A later human study distinguishes static access to identical extra
evidence from interactive access, and measures review load and exploration
delay. The present fixture cannot estimate those outcomes.
