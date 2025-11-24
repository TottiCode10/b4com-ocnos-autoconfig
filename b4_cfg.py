# =========================
# Параметры подключения
# =========================
HOST = "10.10.10.10"             # IP устройства 
PORT = 22                       # SSH порт,при работе в симуляторе gns3 можно использовать DEVICE_TYPE = "ipinfusion_ocnos_telnet" и порт который предоставляет gns3
USER = "admin"                     # Имя пользователя
PASSWORD = "admin"                 # Пароль 
DEVICE_TYPE = "ipinfusion_ocnos"   # Netmiko device_type для OcNOS/B4Com, при работе в симуляторе gns3 можно использовать DEVICE_TYPE = "ipinfusion_ocnos_telnet"

# =========================
# Логи и тайминги
# =========================
OUT_DIR = "out_b4"                 # Папка куда складываем логи (session/commands/errors/show)
GLOBAL_DELAY_FACTOR = 1.8          # Множитель задержек Netmiko: ниже — быстрее, выше — стабильнее
READ_TIMEOUT = 300                 # Таймаут чтения (сек) для show и конфигурации
CFG_PER_BATCH = 20                 # Размер пакета команд в send_config_set
CFG_SLEEP = 0.3                   # Пауза между пакетами команд (сек)

# =========================
# L2 bridge / trunk
# =========================
BRIDGE_ID = 1                      # ID VLAN bridge
BRIDGE_PROTOCOL = "rstp"           # Протокол STP (rstp/stp — по поддержке ОС)
TRUNK_IF = "eth0"                  # имя интерфейса для trunk

# =========================
# Масштаб конфигурации
# =========================
VLAN_START = 151                  # Первый VLAN в диапазоне
VLAN_COUNT = 10                    # Количество VLAN

SVI_COUNT = 10                     # Количество SVI 

VRF_COUNT = 10                     # Количество VRF (скрипт предназначен для схемы 1:1)
VRF_PREFIX = "VRF"                 # Префикс имени VRF 

# =========================
# IP-схема
# =========================
# Для индекса i адрес/сеть вычисляются по формуле:
# A.(B_START + i//NET_SIZE).(C_START + i%NET_SIZE).1/24
IP_BASE_A = 10
IP_BASE_B_START = 10
IP_BASE_C_START = 10
NET_SIZE = 254                   # Размер “шага” по третьему октету для /24
VIP_LAST_OCTET = 254               # Последний октет VIP для VRRP

# =========================
# VRRP
# =========================
VRRP_COUNT = 70                    # Количество VRRP-групп
VRRP_START_ID = 1                  # Первый VRID
VRRP_PRIORITY = 254                # Приоритет VRRP

# =========================
# OSPF 
# =========================
OSPF_ENABLE = True                 # Включение/отключение OSPF-этапа
OSPF_IDX_START = 0                 # Смещение индекса сетей для OSPF
OSPF_PROCESS_BASE = 1              # Базовый PID; далее PID = base + i
