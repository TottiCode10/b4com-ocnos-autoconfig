# 00_check_connect_b4.py
import b4_cfg as cfg
from b4_netmiko import B4

# =========================
# Идея скрипта
# =========================
# Минимальная проверка подключения:
# 1) подключились по SSH/Telnet
# 2) сняли базовые show, чтобы сразу видеть версию ОС и текущую конфигурацию

r = B4(
    cfg.HOST, cfg.USER, cfg.PASSWORD, cfg.DEVICE_TYPE, cfg.PORT,
    global_delay=cfg.GLOBAL_DELAY_FACTOR, out_dir=cfg.OUT_DIR, tag="00_check"
).open()

# Проверяем, что устройство отвечает и мы в нужной сессии
r.save_text("show_version", r.show("show version", read_timeout=cfg.READ_TIMEOUT)) 

# Сразу фиксируем running-config
r.save_text("show_running", r.show("show running-config", read_timeout=cfg.READ_TIMEOUT))

r.close()
