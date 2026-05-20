#!/usr/bin/env bash
# Smoke-test all documented API endpoints against a running backend.
set -euo pipefail
BASE="${BASE_URL:-http://127.0.0.1:5000}"
PASS=0
FAIL=0

check() {
  local name="$1" expected="$2" actual="$3" body="$4"
  if [[ "$actual" == "$expected" ]]; then
    echo "  OK   $name ($actual)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL $name (expected $expected, got $actual)"
    echo "       ${body:0:200}"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== AutoGate API smoke test ==="
echo "Base: $BASE"
echo ""

# --- Auth ---
LOGIN=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@123"}')
BODY=$(echo "$LOGIN" | sed '$d')
CODE=$(echo "$LOGIN" | tail -1)
check "POST /api/auth/login" "200" "$CODE" "$BODY"
TOKEN=$(echo "$BODY" | python3 -c "import sys,json; print(json.load(sys.stdin).get('token',''))" 2>/dev/null || true)
AUTH="Authorization: Bearer $TOKEN"

# --- Public / optional auth ---
for ep in \
  "GET|/api/parking/availability|200" \
  "GET|/api/camera/feed|200,503" \
  "POST|/api/chatbot/message|200|{\"message\":\"hello\"}"; do
  IFS='|' read -r METHOD PATH EXPECT <<< "$ep"
  EXTRA="${ep#*|*|*|}"
  if [[ -n "$EXTRA" && "$EXTRA" != "$ep" ]]; then
    R=$(curl -s -w "\n%{http_code}" -X "$METHOD" "$BASE$PATH" -H "Content-Type: application/json" -d "$EXTRA")
  else
    R=$(curl -s -w "\n%{http_code}" -X "$METHOD" "$BASE$PATH")
  fi
  B=$(echo "$R" | sed '$d'); C=$(echo "$R" | tail -1)
  ok=0
  IFS=',' read -ra EXP <<< "$EXPECT"
  for e in "${EXP[@]}"; do [[ "$C" == "$e" ]] && ok=1; done
  if [[ $ok -eq 1 ]]; then
    echo "  OK   $METHOD $PATH ($C)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL $METHOD $PATH (expected $EXPECT, got $C)"
    FAIL=$((FAIL + 1))
  fi
done

# --- JWT protected ---
endpoints=(
  "GET|/api/auth/me|200"
  "GET|/api/dashboard/stats|200"
  "GET|/api/parking/currently-parked|200"
  "GET|/api/parking/slots/available?date=2026-05-21&time=10:00|200"
  "GET|/api/parking/suggested|200"
  "GET|/api/parking/bookings/my|200"
  "GET|/api/vehicles|200"
  "GET|/api/logs|200"
  "GET|/api/logs/export|200"
  "GET|/api/forecast?period=24h|200"
  "GET|/api/anomalies|200"
  "GET|/api/gate/status|200"
  "GET|/api/timetable/my|200"
)

for ep in "${endpoints[@]}"; do
  IFS='|' read -r METHOD PATH EXPECT <<< "$ep"
  R=$(curl -s -w "\n%{http_code}" -X "$METHOD" "$BASE$PATH" -H "$AUTH")
  B=$(echo "$R" | sed '$d'); C=$(echo "$R" | tail -1)
  check "$METHOD $PATH" "$EXPECT" "$C" "$B"
done

# Gate mutations
for ep in "POST|/api/gate/emergency-stop" "POST|/api/gate/reset-emergency-stop"; do
  IFS='|' read -r METHOD PATH <<< "$ep"
  R=$(curl -s -w "\n%{http_code}" -X "$METHOD" "$BASE$PATH" -H "$AUTH")
  C=$(echo "$R" | tail -1)
  check "$METHOD $PATH" "200" "$C" ""
done

# Vehicle CRUD
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/vehicles" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"plate_number":"SMOKE-99","owner_name":"Smoke Test","owner_id":"SMK99","contact":"03009999999","status":"active"}')
B=$(echo "$R" | sed '$d'); C=$(echo "$R" | tail -1)
VID=""
if [[ "$C" == "201" || "$C" == "200" ]]; then
  VID=$(echo "$B" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id', d.get('vehicle',{}).get('id','')))" 2>/dev/null || true)
  echo "  OK   POST /api/vehicles ($C) id=$VID"
  PASS=$((PASS + 1))
else
  echo "  FAIL POST /api/vehicles (got $C) ${B:0:150}"
  FAIL=$((FAIL + 1))
fi

if [[ -n "$VID" && "$VID" != "0" ]]; then
  R=$(curl -s -w "\n%{http_code}" -X PUT "$BASE/api/vehicles/$VID" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"owner_name":"Smoke Updated"}')
  check "PUT /api/vehicles/$VID" "200" "$(echo "$R" | tail -1)" ""
  R=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE/api/vehicles/$VID" -H "$AUTH")
  check "DELETE /api/vehicles/$VID" "200" "$(echo "$R" | tail -1)" ""
fi

# Timetable save/update
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/timetable/save" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"classes":[{"day":"Mon","start":"09:00","end":"10:00","subject":"Test"}]}')
check "POST /api/timetable/save" "200" "$(echo "$R" | tail -1)" ""

R=$(curl -s -w "\n%{http_code}" -X PUT "$BASE/api/timetable/update" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"classes":[{"day":"Tue","start":"11:00","end":"12:00","subject":"Updated"}]}')
check "PUT /api/timetable/update" "200" "$(echo "$R" | tail -1)" ""

# Parking book (may 409 if no slots — still report)
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE/api/parking/book" -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"slot_id":1,"date":"2026-06-01","start_time":"10:00","end_time":"12:00","plate_number":"SMOKE-99"}')
C=$(echo "$R" | tail -1)
if [[ "$C" == "200" || "$C" == "201" || "$C" == "409" ]]; then
  echo "  OK   POST /api/parking/book ($C)"
  PASS=$((PASS + 1))
else
  echo "  FAIL POST /api/parking/book (got $C)"
  FAIL=$((FAIL + 1))
fi

echo ""
echo "=== Summary: $PASS passed, $FAIL failed ==="
[[ $FAIL -eq 0 ]]
