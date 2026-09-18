#!/bin/bash
# Requer pacote 'jq' instalado para parsear o JSON do Wazuh

# Lê o JSON da entrada padrão (padrão Wazuh 4.x+)
read INPUT_JSON

# Extrai o usuário da chave correspondente do alerta
USER=$(echo "$INPUT_JSON" | jq -r '.parameters.alert.data.srcuser')

if [ -z "$USER" ] || [ "$USER" == "null" ]; then
    exit 1
fi

# 1. Coletar PIDs
PIDS=$(smbstatus -u "$USER" | awk 'NR>4 {print $1}')

# 2. Derrubar processos
for PID in $PIDS; do
    kill -9 "$PID" 2>/dev/null
done

# 3. Desativar no Samba
smbpasswd -d "$USER"

# Registrar a ação no log do Active Response
echo "$(date '+%Y-%m-%d %H:%M:%S') - Active Response: Usuário $USER bloqueado por múltiplos acessos" >> /var/ossec/logs/active-responses.log

