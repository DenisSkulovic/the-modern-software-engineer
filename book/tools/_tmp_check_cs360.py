from pathlib import Path
import re

root = Path(__file__).resolve().parents[1] / "CS" / "CS360-algorithms-interview-lab"
for p in sorted(root.glob("*.md")):
    t = p.read_text(encoding="utf-8")
    m = re.search(r"^manuscript:\s*(\S+)", t, re.M)
    e = re.search(r'^edition:\s*"?([^"\n]+)', t, re.M)
    print(p.name, m.group(1) if m else "?", e.group(1) if e else "?")
