#!/usr/bin/env bash
# Monitor de uptime + vencimiento de SSL.
# Falla (exit 1) si algún sitio está caído o un certificado vence pronto
# -> GitHub manda mail automático del workflow fallido.
set -u
SITES_FILE="${1:-monitor/sites.txt}"
SSL_MIN_DAYS="${SSL_MIN_DAYS:-14}"
FAIL=0
PROBLEMS=""

while IFS= read -r url; do
  [ -z "$url" ] && continue
  case "$url" in \#*) continue ;; esac
  host=$(echo "$url" | sed -E 's#https?://##; s#/.*##')

  # --- Uptime ---
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 25 -L "$url" || echo "000")
  if [ "$code" -lt 200 ] || [ "$code" -ge 400 ]; then
    echo "❌ CAÍDO: $url (HTTP $code)"
    PROBLEMS="$PROBLEMS\n- CAÍDO: $url (HTTP $code)"; FAIL=1
  else
    echo "✅ OK: $url (HTTP $code)"
  fi

  # --- SSL expiry ---
  end=$(echo | openssl s_client -servername "$host" -connect "$host:443" 2>/dev/null \
        | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
  if [ -n "$end" ]; then
    end_epoch=$(date -d "$end" +%s 2>/dev/null || echo 0)
    days=$(( (end_epoch - $(date +%s)) / 86400 ))
    if [ "$days" -lt "$SSL_MIN_DAYS" ]; then
      echo "⚠️  SSL por vencer: $host en $days días ($end)"
      PROBLEMS="$PROBLEMS\n- SSL por vencer: $host en $days días"; FAIL=1
    else
      echo "🔒 SSL OK: $host ($days días restantes)"
    fi
  else
    echo "⚠️  No pude leer el SSL de $host"
    PROBLEMS="$PROBLEMS\n- No pude leer el SSL de $host"; FAIL=1
  fi
done < "$SITES_FILE"

if [ "$FAIL" -ne 0 ]; then
  echo -e "\n=== PROBLEMAS DETECTADOS ===$PROBLEMS"
fi
exit $FAIL
