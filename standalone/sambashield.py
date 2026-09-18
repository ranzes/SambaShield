#!/usr/bin/env python3
import time
import subprocess
import re
from collections import deque, defaultdict

LOG_FILE = "/var/log/syslog" # Ajuste para o seu log do Samba
THRESHOLD = 10
TIME_WINDOW = 5 # segundos

# Dicionário para armazenar timestamps de acesso por usuário
user_accesses = defaultdict(lambda: deque(maxlen=THRESHOLD))

def block_user(username):
    print(f"Bloqueando usuário: {username}")
    
    # 1. Obter PIDs do usuário
    status_output = subprocess.run(['smbstatus', '-u', username], capture_output=True, text=True)
    pids = re.findall(r'^\s*(\d+)\s+'+username, status_output.stdout, re.MULTILINE)
    
    # 2. Matar processos
    for pid in pids:
        subprocess.run(['kill', '-9', pid])
        
    # 3. Desativar conta
    subprocess.run(['smbpasswd', '-d', username])

def process_log():
    with open(LOG_FILE, "r") as f:
        f.seek(0, 2) # Vai para o final do arquivo
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            
            # Filtro básico para vfs_full_audit (Ajuste o regex conforme seu log)
            if "smbd_audit" in line and ("open" in line or "write" in line):
                match = re.search(r'smbd_audit:\s+([^|]+)\|', line)
                if match:
                    user = match.group(1).strip()
                    now = time.time()
                    
                    user_accesses[user].append(now)
                    
                    if len(user_accesses[user]) == THRESHOLD:
                        time_diff = user_accesses[user][-1] - user_accesses[user][0]
                        if time_diff <= TIME_WINDOW:
                            block_user(user)
                            user_accesses[user].clear() # Reseta para não travar em loop

if __name__ == "__main__":
    process_log()

