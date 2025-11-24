# 11_set_trunk_b4.py
import b4_cfg as cfg
from b4_netmiko import B4

# =========================
# Идея скрипта
# =========================
# Настраиваем trunk на заданном порту TRUNK_IF:
# - включаем switchport
# - добавляем bridge-group
# - ставим mode trunk
# - разрешаем диапазон VLAN, который создали в 10-м скрипте

first = cfg.VLAN_START
last = cfg.VLAN_START + cfg.VLAN_COUNT - 1

cmds = [
    f"interface {cfg.TRUNK_IF}",
    "switchport",
    f"bridge-group {cfg.BRIDGE_ID}",
    "switchport mode trunk",
    f"switchport trunk allowed vlan add {first}-{last}",
]

r = B4(
    cfg.HOST, cfg.USER, cfg.PASSWORD, cfg.DEVICE_TYPE, cfg.PORT,
    global_delay=cfg.GLOBAL_DELAY_FACTOR, out_dir=cfg.OUT_DIR, tag="11_set_trunk"
).open()

r.cfg(cmds, per_batch=cfg.CFG_PER_BATCH, read_timeout=cfg.READ_TIMEOUT, sleep_between=cfg.CFG_SLEEP)

# Снимаем состояние порта после настройки
r.save_text(
    "show_run_trunk",
    r.show(f"show running-config interface {cfg.TRUNK_IF}", read_timeout=cfg.READ_TIMEOUT),
)
r.save_text("show_ip_int_brief", r.show("show ip int brief", read_timeout=cfg.READ_TIMEOUT))

r.close()
