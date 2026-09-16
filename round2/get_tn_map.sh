#!/bin/bash
# Tamil Nadu OSM extract (openstreetmap.fr) into data/osm/, with a live progress bar, resume, and a full-read check.
#   round2/get_tn_map.sh           resume the partial download (bar starts where it left off)
#   round2/get_tn_map.sh --fresh   delete the partial and start from 0
# Ctrl+C is safe: the partial is kept and the next run resumes it.
# Geofabrik has no state-level file for India (smallest is southern-zone, 557 MB), so this uses openstreetmap.fr,
# which publishes no MD5 — the file is instead verified by reading every object in it with osmium.
set -e
HERE="$(dirname "$(readlink -f "$0")")"
ROOT="$HERE/.."
mkdir -p "$ROOT/data/osm"
cd "$ROOT/data/osm"
URL="https://download.openstreetmap.fr/extracts/asia/india/tamil_nadu-latest.osm.pbf"
OUT=tamil_nadu-latest.osm.pbf
PART=$OUT.part
STAMP=$OUT.version

[ "$1" = "--fresh" ] && rm -f "$PART" "$OUT" "$STAMP"
if [ -f "$OUT" ]; then echo "Already complete: data/osm/$OUT"; exit 0; fi

# The server rebuilds the file daily. Resuming across two versions would corrupt it.
HEAD=$(curl -sIL "$URL" | tr -d '\r')
LM=$(echo "$HEAD" | awk 'tolower($1)=="last-modified:"{sub(/^[^:]*: /,""); v=$0} END{print v}')
SIZE=$(echo "$HEAD" | awk 'tolower($1)=="content-length:"{v=$2} END{print v}')
if [ -f "$PART" ] && { [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$LM" ]; }; then
  echo "Server file was rebuilt since this partial started — starting fresh."
  rm -f "$PART"
fi
echo "$LM" > "$STAMP"

echo "Downloading $OUT into data/osm/  (server version: $LM)"
wget -c -q --show-progress --progress=bar:force:noscroll \
     --tries=30 --retry-connrefused --read-timeout=60 --waitretry=10 \
     -O "$PART" "$URL"

got=$(stat -c %s "$PART")
if [ "$got" != "$SIZE" ]; then
  echo "✗ SIZE MISMATCH — got $got bytes, server says $SIZE. Run: round2/get_tn_map.sh --fresh"
  exit 1
fi
echo "Size OK ($got bytes). Verifying: reading every object in the file..."
PY="$ROOT/.venv/bin/python3"
if "$PY" - "$PART" <<'EOF'
import sys, osmium
class Count(osmium.SimpleHandler):
    def __init__(self):
        super().__init__(); self.n = self.w = self.r = self.roads = 0
    def node(self, n): self.n += 1
    def way(self, w):
        self.w += 1
        if "highway" in w.tags: self.roads += 1
    def relation(self, r): self.r += 1
c = Count(); c.apply_file(osmium.io.File(sys.argv[1], "pbf"))   # .part has no extension osmium recognises
print(f"  {c.n:,} nodes · {c.w:,} ways ({c.roads:,} highway ways) · {c.r:,} relations")
sys.exit(0 if c.n and c.roads else 1)
EOF
then
  mv "$PART" "$OUT"
  echo "✓ COMPLETE — file reads end to end: data/osm/$OUT"
else
  echo "✗ FILE UNREADABLE OR EMPTY — run: round2/get_tn_map.sh --fresh"
  exit 1
fi
