# LLM output evaluations

The evaluation harness protects structured decisions while allowing prose to
change. Each `EvalCase` contains product inputs and constraints for required
fields, severity, confidence, and permitted severity drift.

## Replay mode (CI default)

Store each recorded product response as a JSON object at
`evals/fixtures/<case_id>.json`. From that product repository run:

```powershell
$env:SHARED_LLM_EVAL_MODE = "replay"
python -m pytest tests/test_eval_gate.py -q
```

Replay never invokes a router or opens a network connection. Set
`SHARED_LLM_EVAL_FIXTURES` only when the fixture directory is not the current
repository's `evals/fixtures`.

## Recording and adding a case

1. Create a synthetic input with no customer identifiers, hosts, addresses, or
   credentials.
2. In an operator-controlled environment, invoke the product once with the
   model identifier selected for the baseline.
3. Review and write only the structured response to
   `evals/fixtures/<case_id>.json`; never record request headers or secrets.
4. Add an `EvalCase` whose `expected` mapping declares `required_fields`, a
   `severity` rule (`allowed`, `baseline`, `max_drift`), and a `confidence`
   range (`min`, `max`).
5. Record the date and model identifier in the product evaluation README, then
   run replay mode and deliberately mutate one fixture to prove the gate fails.

## Live mode (manual only)

Set `SHARED_LLM_EVAL_MODE=live` and pass `run_eval` a product-specific callback
that accepts `case.inputs` and invokes `LLMRouter`. Live mode may incur provider
cost and is intentionally excluded from CI. Review model output before
replacing any recorded fixture.
