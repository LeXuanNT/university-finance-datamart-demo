#!/usr/bin/env bash
# PreToolUse guard: an agent may build and test locally, but may not touch production or raw data.
# Reads the tool call as JSON on stdin; exit 2 = block (message on stderr goes back to the agent).
input="$(cat)"
cmd="$(printf '%s' "$input" | python3 -c 'import sys,json; d=json.load(sys.stdin); print((d.get("tool_input") or {}).get("command",""))' 2>/dev/null)"
[ -z "$cmd" ] && exit 0
lc="$(printf '%s' "$cmd" | tr '[:upper:]' '[:lower:]')"

if printf '%s' "$lc" | grep -Eq 'dbt[^|;&]*--target[ =]+(snowflake|prod)'; then
  echo "Blocked: direct runs against the Snowflake/production target are not allowed. Open a pull request; CI deploys after review." >&2
  exit 2
fi
if printf '%s' "$lc" | grep -Eq 'dbt[^|;&]*--full-refresh'; then
  echo "Blocked: --full-refresh rebuilds finance history. Ask the data owner first." >&2
  exit 2
fi
if printf '%s' "$lc" | grep -Eq '(drop|truncate|delete[[:space:]]+from|update)[^;]*raw_(sis|workday)'; then
  echo "Blocked: raw SIS/Workday tables are read-only (audit trail)." >&2
  exit 2
fi
exit 0
