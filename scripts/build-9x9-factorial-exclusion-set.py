import csv
import hashlib
import json
from pathlib import Path

sources = {
    "pilot-64-input": Path("results/9x9/pair-vs-true-unique-pilot-64-input.csv"),
    "confirmatory-1024-regenerated": Path("artifacts/9x9-confirmatory-1024.csv"),
    "first12": Path("results/9x9/pair-vs-true-unique-first12.csv"),
    "smoke": Path("results/9x9/pair-vs-true-unique-smoke.csv"),
}

parents = set()
file_rows = []
for name, path in sources.items():
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0].keys()) if rows else []
    if "canonical_parent" not in cols:
        raise SystemExit(f"{path} missing canonical_parent: {cols}")
    vals = [r["canonical_parent"] for r in rows]
    parents.update(vals)
    file_rows.append(
        {
            "source": name,
            "path": str(path).replace("\\", "/"),
            "sha256": sha,
            "rows": len(vals),
            "unique_in_file": len(set(vals)),
            "columns": ",".join(cols),
        }
    )
    print(f"{name}: rows={len(vals)} unique={len(set(vals))} sha256={sha}")

out = Path("artifacts/exclusion-canonical-parents.csv")
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["canonical_parent"])
    for p in sorted(parents):
        w.writerow([p])

out_sha = hashlib.sha256(out.read_bytes()).hexdigest()
print(f"excluded_unique={len(parents)}")
print(f"exclusion_csv={out}")
print(f"exclusion_sha256={out_sha}")

manifest = {
    "excluded_unique": len(parents),
    "exclusion_csv": str(out).replace("\\", "/"),
    "exclusion_sha256": out_sha,
    "sources": file_rows,
}
Path("artifacts/exclusion-manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
)
print("wrote artifacts/exclusion-manifest.json")
