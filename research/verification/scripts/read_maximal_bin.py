"""Read a kc_maximal_*.bin dump: u64 count, then count masks."""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "data"
for arg in sys.argv[1:]:
    p = ROOT / arg if not Path(arg).is_absolute() else Path(arg)
    if not p.exists():
        print(f"{p.name}: MISSING")
        continue
    raw = p.read_bytes()
    (count,) = struct.unpack("<Q", raw[:8])
    print(f"{p.name}: {count} masks, {len(raw)} bytes "
          f"(expect {8 + 8 * count} = {'OK' if len(raw) == 8 + 8 * count else 'TRUNCATED'})")
    if count and count <= 12:
        for i in range(count):
            (m,) = struct.unpack("<Q", raw[8 + 8 * i:16 + 8 * i])
            print(f"    [{i}] 0x{m:016x}")
