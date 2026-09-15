#!/bin/bash
# England OSM extract (Geofabrik) into data/osm/, with a live progress bar, resume, and MD5 check.
#   round2/get_osm_map.sh           resume the partial download (bar starts where it left off)
#   round2/get_osm_map.sh --fresh   delete the partial and start from 0
# Ctrl+C is safe: the partial is kept and the next run resumes it.
set -e
HERE="$(dirname "$(readlink -f "$0")")"
mkdir -p "$HERE/../data/osm"
cd "$HERE/../data/osm"
URL="https://download.geofabrik.de/europe/united-kingdom/england-latest.osm.pbf"
OUT=england-latest.osm.pbf
PART=$OUT.part

[ "$1" = "--fresh" ] && rm -f "$PART" "$OUT" "$OUT.md5"
if [ -f "$OUT" ]; then echo "Already complete: data/osm/$OUT"; exit 0; fi

# Geofabrik rebuilds the file daily. Resuming across two versions would corrupt it.
LM=$(curl -sIL "$URL" | awk 'tolower($1)=="last-modified:"{sub(/^[^:]*: /,""); v=$0} END{print v}' | tr -d '\r')
if [ -f "$PART" ] && [ -f "$OUT.md5" ] && [ "$(date -d "$LM" +%s)" -gt "$(stat -c %Y "$OUT.md5")" ]; then
  echo "Server file was rebuilt since this partial started — starting fresh."
  rm -f "$PART"
fi
[ -f "$PART" ] && [ -f "$OUT.md5" ] || curl -sL -o "$OUT.md5" "$URL.md5"

echo "Downloading england-latest.osm.pbf into data/osm/  (server version: $LM)"
wget -c -q --show-progress --progress=bar:force:noscroll \
     --tries=30 --retry-connrefused --read-timeout=60 --waitretry=10 \
     -O "$PART" "$URL"

mv "$PART" "$OUT"
echo "Verifying checksum..."
got=$(md5sum "$OUT" | cut -d' ' -f1); want=$(cut -d' ' -f1 "$OUT.md5")
if [ "$got" = "$want" ]; then
  echo "✓ COMPLETE — MD5 OK ($got)"
else
  echo "✗ MD5 MISMATCH — got $got, expected $want. Run: round2/get_osm_map.sh --fresh"
  exit 1
fi
