"""Generate the protocol file of the stopping-criterion experiment (SMS).

Seven stopping criteria, each run under the two harness recipes of the main experiment (Minimal, Full),
so 14 recipes and 14 campaigns over the given workloads and work sizes:

  sms              StableMedianStoppingCriterion    retained rule (C0 + C1 + C2)
  sms-c0           StableMedianC0StoppingCriterion  C0 alone, at its own optimum
  fixed-<N_max>    StoppingCriterion                fixed budget, equal to the N_max of the two rules
  fixed-2000       StoppingCriterion                reference budget of the stopping-criterion study
  primbench        VariationStoppingCriterion       PrimBench
  nvbench-entropy  EntropyStoppingCriterion         NVBench
  nvbench-stdrel   StdRelStoppingCriterion          NVBench

The parameters of the criteria are not set here: they are the defaults compiled in the binary, read
with `gen --default-pf`. The workload, backend and stats presets come from there too. Only the two
harness recipes are written here, identical to the main experiment (rq1_rq3/experiment/amd-experiment-protocol.json).
Regenerate the protocol after any change of the C++ defaults.

The workloads file is a JSON list of workload names, or an object with a "workloads" list.

  ./.venv/bin/python rq4/experiment/make_sms_protocol.py rq4/experiment/amd-sms-workloads.json -o rq4/experiment/amd-sms-experiment-protocol.json
  ./.venv/bin/python rq4/experiment/make_sms_protocol.py rq4/experiment/nvidia-sms-workloads.json --device 1 -o rq4/experiment/nvidia-sms-experiment-protocol.json
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_BIN = Path("bin/baseliner-blas-rq4")
WORK_SIZES = (8, 32, 128, 512)

# Harness recipes of the main experiment (Benchmark presets of rq1_rq3/experiment/amd-experiment-protocol.json).
HARNESS = {
    "Minimal": {
        "warmup": "0", "flush": "0", "dynamic_batch": "0", "batch_size": "25", "minimal_batch_duration": "10.000000",
        "block": "0", "block_duration": "1000.000000", "block_queue_size": "64", "warm_cool": "0", "validate_workload": "0",
    },
    "Full": {
        "warmup": "1", "flush": "1", "dynamic_batch": "1", "batch_size": "25", "minimal_batch_duration": "10.000000",
        "block": "1", "block_duration": "1000.000000", "block_queue_size": "64", "warm_cool": "0", "validate_workload": "0",
    },
}

# Reference budget of the stopping-criterion study (evaluate_nonparametric_criterion.py, failures against N = 2,000).
REFERENCE_BUDGET = 2000

# (key, campaign label, implementation). The fixed budgets get their own presets, built here.
CRITERIA = (
    ("sms", "SMS", "StableMedianStoppingCriterion"),
    ("sms-c0", "SMS C0", "StableMedianC0StoppingCriterion"),
    ("fixed-nmax", "Fixed", "StoppingCriterion"),
    ("fixed-reference", "Fixed", "StoppingCriterion"),
    ("primbench", "PrimBench", "VariationStoppingCriterion"),
    ("nvbench-entropy", "NVBench Entropy", "EntropyStoppingCriterion"),
    ("nvbench-stdrel", "NVBench StdRel", "StdRelStoppingCriterion"),
)
SMS_IMPLS = ("StableMedianStoppingCriterion", "StableMedianC0StoppingCriterion")

# Stats recorded by every campaign, whatever its criterion, with their names in `gen --metadata`:
# m* (Median), RCV_OQAD (RCVOQAD), t_gpu (GpuAccumulatedTime), mean, CV of the whole trace
# (TraceCoefficientOfVariation) and the CV of PrimBench (CoefficientOfVariation, last 10 batch durations). N* (repetitions) and
# t_mur (cpu_time, wall-clock duration of the trace) are always recorded, without a stat.
STATS = ("Median", "Mean", "CoefficientOfVariation", "TraceCoefficientOfVariation", "RCVOQAD", "GpuAccumulatedTime")


def binary_defaults(binary: Path) -> tuple[dict, dict, dict]:
    """Default protocol, metadata and protocol schema of the binary (`gen --default-pf`, `--metadata`, `--schema`)."""
    with tempfile.TemporaryDirectory() as tmp:
        files = {flag: Path(tmp) / f"{flag[2:]}.json" for flag in ("--default-pf", "--metadata", "--schema")}
        for flag, path in files.items():
            done = subprocess.run([str(binary), "gen", flag, str(path)], capture_output=True, text=True)
            if done.returncode != 0 or not path.exists():
                raise SystemExit(f"`{binary} gen {flag}` failed:\n{done.stdout}{done.stderr}")
        return tuple(json.loads(path.read_text(encoding="utf-8")) for path in files.values())


def schema_errors(value, schema: dict, path: str = "protocol") -> list[str]:
    """Errors of a value against the subset of JSON Schema used by `gen --schema`."""
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(value, dict):
            return [f"{path}: expected an object"]
        errors = [f"{path}: missing field '{key}'" for key in schema.get("required", []) if key not in value]
        props, extra = schema.get("properties", {}), schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in props:
                errors += schema_errors(item, props[key], f"{path}.{key}")
            elif extra is False:
                errors.append(f"{path}: unexpected field '{key}'")
            elif isinstance(extra, dict):
                errors += schema_errors(item, extra, f"{path}.{key}")
        return errors
    if kind == "array":
        if not isinstance(value, list):
            return [f"{path}: expected an array"]
        return [e for i, item in enumerate(value) for e in schema_errors(item, schema.get("items", {}), f"{path}[{i}]")]
    if kind == "string" and not isinstance(value, str):
        return [f"{path}: expected a string"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{path}: '{value}' not in {schema['enum']}"]
    return []


def load_workloads(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    workloads = data["workloads"] if isinstance(data, dict) else data
    if not workloads or not all(isinstance(w, str) for w in workloads):
        raise SystemExit(f"{path}: expected a non-empty list of workload names.")
    duplicates = sorted({w for w in workloads if workloads.count(w) > 1})
    if duplicates:
        raise SystemExit(f"{path}: duplicated workloads: {', '.join(duplicates)}")
    return workloads


def option(preset: dict, group: str, name: str) -> dict:
    """An option of a preset, or an error naming it when the binary does not have it."""
    try:
        return preset["options"][group][name]
    except KeyError:
        raise SystemExit(f"Option {group}.{name} not found in the binary defaults.") from None


def values(preset: dict) -> str:
    return ", ".join(f"{name} = {opt['value']}" for opts in preset["options"].values() for name, opt in opts.items())


def build_protocol(defaults: dict, metadata: dict, workloads: list[str], work_sizes: list[int], device: str | None) -> dict:
    presets = defaults["presets"]
    components = metadata["components"]

    unknown = [w for w in workloads if w not in components["Workload"]]
    if unknown:
        raise SystemExit(f"Workloads unknown to the binary: {', '.join(unknown)}")
    missing = [impl for _, _, impl in CRITERIA if impl not in components["StoppingCriterion"]]
    if missing:
        raise SystemExit(f"Stopping criteria missing from the binary (rebuild it?): {', '.join(missing)}")
    # An unknown stat only raises a warning, and Baseliner then measures nothing in the campaign.
    missing = [name for name in STATS if name not in metadata["stats"]]
    if missing:
        raise SystemExit(f"Stats not declared by the binary (gen --metadata): {', '.join(missing)}. "
                         "Baseliner would skip every campaign of the protocol.")

    out = {w: copy.deepcopy(presets[w]) for w in workloads}

    # Harness recipes, on top of the Benchmark defaults of the binary.
    out["Benchmark"] = {}
    for harness, overrides in HARNESS.items():
        preset = copy.deepcopy(presets["Benchmark"]["default"])
        preset["description"] = f"{harness} harness of the main experiment"
        for name, value in overrides.items():
            option(preset, "Benchmark", name)["value"] = value
        out["Benchmark"][harness.lower()] = preset

    # Criteria: defaults of the binary, and two fixed budgets: the shared N_max of the SMS rules and the
    # reference budget.
    n_max = {impl: option(presets[impl]["default"], "StoppingCriterion", "max_nb_repetition")["value"] for impl in SMS_IMPLS}
    if len(set(n_max.values())) != 1:
        raise SystemExit(f"The SMS rules do not share the same N_max: {n_max}")
    n_max = next(iter(n_max.values()))
    fixed = {
        "fixed-nmax": (n_max, "N_max of the SMS rules"),
        "fixed-reference": (str(REFERENCE_BUDGET), "reference budget of the stopping-criterion study"),
    }
    if n_max == str(REFERENCE_BUDGET):
        raise SystemExit(f"N_max equals the reference budget ({n_max}): the two fixed budgets would be the same run.")
    stopping = {}
    for key, _, impl in CRITERIA:
        if key in fixed:
            budget, role = fixed[key]
            preset = copy.deepcopy(presets[impl]["default"])
            preset["description"] = f"Fixed budget of {budget} executions ({role})"
            option(preset, "StoppingCriterion", "max_nb_repetition")["value"] = budget
            stopping[key] = (impl, f"n{budget}")
            out.setdefault(impl, {})[f"n{budget}"] = preset
        else:
            stopping[key] = (impl, "default")
            out[impl] = {"default": copy.deepcopy(presets[impl]["default"])}

    for backend in components["Backend"]:
        out[backend] = copy.deepcopy(presets[backend])
        if device is not None:
            option(out[backend]["default"], "Backend", "device")["value"] = device

    sweep = {
        "strategy": "FullGrid",
        "axes": [{
            "interface": "Workload", "option": "work_size",
            "hint": {"policy": "Enumerated", "min": "1", "max": "256", "step": "1", "enumerated": [str(s) for s in work_sizes]},
        }],
    }
    recipes, campaigns = {}, []
    for harness in HARNESS:
        for key, label, impl in CRITERIA:
            impl, preset = stopping[key]
            suffix = f"fixed-{fixed[key][0]}" if key in fixed else key
            label = f"Fixed {fixed[key][0]}" if key in fixed else label
            name = f"{harness.lower()}-{suffix}"
            recipes[name] = {
                "description": f"{harness} harness, {impl} ({values(out[impl][preset])})",
                "benchmark": {"impl": "Benchmark", "preset": harness.lower()},
                "stopping": {"impl": impl, "preset": preset},
                "stats": {"preset": "default"},
                "sweep": copy.deepcopy(sweep),
            }
            campaigns.append({
                "name": f"{harness} {label}",
                "recipe": name,
                "workloads": [{"impl": w, "preset": "default"} for w in workloads],
                "backends": [{"impl": b, "preset": "default"} for b in components["Backend"]],
                "on_incompatible": "Skip",  # As in the main experiment, where no cell was skipped
            })

    return {
        "baseliner_version": defaults["baseliner_version"],
        "presets": out,
        "stats_presets": {"default": {"description": "Stats of the SMS experiment", "stat_names": list(STATS), "stat_options": {}}},
        "recipes": recipes,
        "campaigns": campaigns,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the protocol file of the stopping-criterion (SMS) experiment.")
    parser.add_argument("workloads", type=Path, help="JSON list of workload names (or an object with a 'workloads' list).")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Protocol file to write.")
    parser.add_argument("--bin", type=Path, default=DEFAULT_BIN, help=f"Baseliner binary with the SMS criteria (default: {DEFAULT_BIN}).")
    parser.add_argument("--work-sizes", type=int, nargs="+", default=list(WORK_SIZES), help="Work sizes of the sweep (default: 8 32 128 512).")
    parser.add_argument("--device", type=str, default=None, help="Device index written in the backend preset (default: the binary's, 0). V100: 1.")
    args = parser.parse_args()

    if not args.bin.exists():
        raise SystemExit(f"Binary not found: {args.bin}. Build it first (README, Run the experiments).")
    defaults, metadata, schema = binary_defaults(args.bin.resolve())
    workloads = load_workloads(args.workloads)
    protocol = build_protocol(defaults, metadata, workloads, args.work_sizes, args.device)
    errors = schema_errors(protocol, schema)
    if errors:
        raise SystemExit("Protocol rejected by the schema of the binary:\n  " + "\n  ".join(errors[:20]))
    args.output.write_text(json.dumps(protocol, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    n_traces = len(protocol["campaigns"]) * len(workloads) * len(args.work_sizes)
    print(f"{args.output}: {len(protocol['campaigns'])} campaigns x {len(workloads)} workloads x {len(args.work_sizes)} work sizes = {n_traces} traces per report")
    for name, recipe in protocol["recipes"].items():
        print(f"  {name:<26} {recipe['description']}", file=sys.stdout)


if __name__ == "__main__":
    main()
