import csv
import hashlib
import itertools
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

SEED = "kyouen-9x9-pair-components-factorial-v1-2026-09-05"
POPULATION = Path("artifacts/9x9-factorial-population.csv")
EXCLUSION = Path("artifacts/exclusion-canonical-parents.csv")
HOLDOUT = Path("artifacts/9x9-factorial-holdout.csv")
MANIFEST = Path("artifacts/9x9-factorial-holdout.manifest.csv")
EXCL_MANIFEST = Path("artifacts/exclusion-manifest.json")
OUT = Path("artifacts/9x9-factorial-holdout-preoutcome-audit.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def main():
    pop = read_csv(POPULATION)
    excl = read_csv(EXCLUSION)
    holdout = read_csv(HOLDOUT)
    man = read_csv(MANIFEST)
    excl_man = json.loads(EXCL_MANIFEST.read_text(encoding="utf-8"))

    sets = {
        "E_at_O0": {r["canonical_parent"] for r in holdout if truthy(r["sample_E_at_O0"])},
        "O_at_E0": {r["canonical_parent"] for r in holdout if truthy(r["census_O_at_E0"])},
        "E_at_O1": {r["canonical_parent"] for r in holdout if truthy(r["sample_E_at_O1"])},
        "O_at_E1": {r["canonical_parent"] for r in holdout if truthy(r["census_O_at_E1"])},
    }

    pairwise = {}
    for a, b in itertools.combinations(sets, 2):
        pairwise[f"{a}__and__{b}"] = len(sets[a] & sets[b])

    man_by = {r["comparison"]: r for r in man}
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()

    audit = {
        "status": "pre_outcome",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "selector_seed": SEED,
        "git_commit": commit,
        "population_total": len(pop),
        "population_sha256": sha256(POPULATION),
        "excluded_unique": int(excl_man["excluded_unique"]),
        "exclusion_sha256": sha256(EXCLUSION),
        "exclusion_sources": excl_man["sources"],
        "eligible_total": len(pop) - int(excl_man["excluded_unique"]),
        "E_at_O0_eligible": int(man_by["E_at_O0"]["eligible"]),
        "E_at_O0_selected": int(man_by["E_at_O0"]["selected"]),
        "O_at_E0_eligible": int(man_by["O_at_E0"]["eligible"]),
        "O_at_E0_selected": int(man_by["O_at_E0"]["selected"]),
        "E_at_O1_eligible": int(man_by["E_at_O1"]["eligible"]),
        "E_at_O1_selected": int(man_by["E_at_O1"]["selected"]),
        "O_at_E1_eligible": int(man_by["O_at_E1"]["eligible"]),
        "O_at_E1_selected": int(man_by["O_at_E1"]["selected"]),
        "unique_parents_to_solve": len(holdout),
        "intersection_sample_E_at_O0_and_E_at_O1": len(sets["E_at_O0"] & sets["E_at_O1"]),
        "pairwise_intersections": pairwise,
        "holdout_sha256": sha256(HOLDOUT),
        "holdout_manifest_sha256": sha256(MANIFEST),
        "holdout_rows": len(holdout),
        "exclusion_csv_rows": len(excl),
        "outcomes_collected": False,
    }
    OUT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
