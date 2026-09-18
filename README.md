SambaShield (SRD) - Samba Ransomware Defender

O SambaShield é uma solução de resposta ativa (Active Response) projetada para proteger servidores de arquivos Samba contra ataques de ransomware e extração em massa de dados. Ele monitora o tráfego de arquivos em tempo real e bloqueia instantaneamente usuários que excedem um limite predefinido de acessos ou modificações em um curto período de tempo.
Como Funciona

A ferramenta depende do módulo vfs_full_audit nativo do Samba. Quando habilitado, o Samba registra as operações de arquivos (leitura, escrita, renomeação, exclusão) e envia esses eventos para o log do sistema (Syslog).

O motor do SambaShield analisa esse fluxo de logs em tempo real. Ao detectar um padrão anômalo — como um usuário modificando 10 arquivos em menos de 5 segundos —, ele assume que uma automação maliciosa (ransomware) está agindo e executa três ações automáticas de contenção:

    Mapeia a sessão do usuário usando smbstatus -u <usuario>.

    Isola o Process ID (PID) do serviço responsável e o encerra instantaneamente enviando um kill -9.

    Desativa o usuário no banco de dados com smbpasswd -d <usuario>, impedindo reconexões subsequentes.

Pré-requisito: Configuração do smb.conf

Para que o SambaShield capture as atividades nos dois cenários (Standalone ou Wazuh), é necessário habilitar a auditoria no arquivo /etc/samba/smb.conf. Adicione as configurações abaixo na seção [global] ou nos compartilhamentos específicos que deseja monitorar.
Ini, TOML

[global]
    # Ativa o módulo VFS de auditoria
    vfs objects = full_audit
    
    # Formata o prefixo da mensagem para facilitar a coleta pelo script/Wazuh
    full_audit:prefix = smbd_audit: %u|%I|%m|%S
    
    # Define quais operações serão monitoradas. Foco em gravação e alteração
    full_audit:success = write pwrite rename unlink
    full_audit:failure = none
    
    # Envia os registros para o daemon de logs do Linux
    full_audit:facility = local5
    full_audit:priority = notice

Após inserir a configuração, reinicie o serviço do Samba para aplicar as mudanças:
sudo systemctl restart smbd
Instalação e Uso: Cenário Standalone

Esta abordagem cria um serviço isolado em background. É ideal para ambientes em que você deseja controle total da heurística no próprio servidor, sem depender de uma central de logs externa.

Diretório Principal: /opt/sambashield
1. Preparação

Crie a pasta do projeto e mova o script de monitoramento para lá:
Bash

sudo mkdir -p /opt/sambashield
# Mova o seu arquivo samba_monitor.py para essa pasta
sudo chmod +x /opt/sambashield/samba_monitor.py

2. Configuração do Serviço Systemd

Crie ou edite o arquivo /etc/systemd/system/samba-defense.service apontando para o novo diretório:
Ini, TOML

[Unit]
Description=SambaShield - Ransomware Defender Daemon
After=smbd.service

[Service]
ExecStart=/usr/bin/python3 /opt/sambashield/samba_monitor.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target

3. Ativação

Recarregue os daemons e inicie a proteção:
Bash

sudo systemctl daemon-reload
sudo systemctl enable --now samba-defense
sudo systemctl status samba-defense

Instalação e Uso: Cenário Wazuh SIEM

Neste cenário, aproveita-se a coleta nativa do agente Wazuh. As regras ficam no Manager, e o bloqueio é executado através de um script de Active Response.
1. No Servidor Wazuh Manager

Insira as lógicas de correlação no arquivo /var/ossec/etc/rules/local_rules.xml. O Manager identificará o log auditado e fará a contagem de frequência usando o parâmetro frequency="10" timeframe="5".

No arquivo /var/ossec/etc/ossec.conf, declare o comando de resposta ativa e relacione-o ao ID da regra configurada no passo anterior:
XML

<command>
  <name>samba-block</name>
  <executable>samba-block.sh</executable>
  <timeout_allowed>no</timeout_allowed>
</command>

<active-response>
  <command>samba-block</command>
  <location>local</location>
  <rules_id>ID_DA_REGRA</rules_id>
</active-response>

Reinicie o Manager: systemctl restart wazuh-manager
2. No Servidor de Arquivos (Agente Wazuh)

Mova o script Bash criado (samba-block.sh) para o diretório padrão de binários de resposta do agente:
Bash

sudo cp samba-block.sh /var/ossec/active-response/bin/

Ajuste as permissões de segurança para que o agente tenha os privilégios corretos de execução:
Bash

sudo chmod 750 /var/ossec/active-response/bin/samba-block.sh
sudo chown root:wazuh /var/ossec/active-response/bin/samba-block.sh

Reinicie o agente localmente: systemctl restart wazuh-agent
