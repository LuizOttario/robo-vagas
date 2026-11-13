#!/usr/bin/env bash
# Agenda o robô pra buscar vagas sozinho (Linux com systemd).
#
#   ./agendar.sh              -> busca 2x por dia, às 9h e às 18h
#   ./agendar.sh "8,12,20"    -> busca nos horários que você escolher
#   ./agendar.sh status       -> mostra a próxima execução
#   ./agendar.sh remover      -> cancela o agendamento
#
# Se o computador estiver desligado no horário, o robô roda assim que ligar.
# O log fica em dados/robo.log.

set -e
PASTA="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$PASTA/.venv/bin/python"
DESTINO="$HOME/.config/systemd/user"
NOME="robo-vagas"

case "$1" in
    remover)
        systemctl --user disable --now "$NOME.timer" 2>/dev/null || true
        rm -f "$DESTINO/$NOME.service" "$DESTINO/$NOME.timer"
        systemctl --user daemon-reload
        echo "Agendamento removido."
        exit 0 ;;
    status)
        systemctl --user list-timers "$NOME.timer"
        exit 0 ;;
esac

if [ ! -x "$PYTHON" ]; then
    echo "Não achei o Python em $PYTHON"
    echo "Rode antes: python -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

HORAS="${1:-9,18}"
mkdir -p "$DESTINO"

cat > "$DESTINO/$NOME.service" <<EOF
[Unit]
Description=Robô de Vagas: busca vagas novas
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$PASTA
ExecStart=$PYTHON -m vagas coletar
EOF

cat > "$DESTINO/$NOME.timer" <<EOF
[Unit]
Description=Roda o Robô de Vagas nos horários escolhidos

[Timer]
OnCalendar=*-*-* $HORAS:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now "$NOME.timer"
echo "Pronto! O robô vai buscar vagas todo dia às ${HORAS//,/h, }h."
echo "Pra testar agora: systemctl --user start $NOME.service && tail dados/robo.log"
