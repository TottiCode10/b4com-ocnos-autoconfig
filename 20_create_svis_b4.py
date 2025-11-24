# 20_create_svis_b4.py
import b4_cfg as cfg
from b4_netmiko import B4

# =========================
# Идея скрипта
# =========================
# Создаём SVI для VLAN-ов (интерфейсы vlan1.<VID>).
# Здесь только поднимаем интерфейс.
# IP и VRF вяжутся отдельным шагом (31-й скрипт).

def svi_name(vid: int) -> str:
    return f"vlan1.{vid}"

vlan_ids = [cfg.VLAN_START + i for i in range(cfg.SVI_COUNT)]

cmds = []
for vid in vlan_ids:
    cmds += [
        f"interface {svi_name(vid)}",
        "no shutdown",
        "exit",
    ]

r = B4(
    cfg.HOST, cfg.USER, cfg.PASSWORD, cfg.DEVICE_TYPE, cfg.PORT,
    global_delay=cfg.GLOBAL_DELAY_FACTOR, out_dir=cfg.OUT_DIR, tag="20_create_svis"
).open()

r.cfg(cmds, per_batch=cfg.CFG_PER_BATCH, read_timeout=cfg.READ_TIMEOUT, sleep_between=cfg.CFG_SLEEP)

# Проверка: SVI должны появиться в "show ip interface brief"
r.save_text("show_ip_int_brief", r.show("show ip interface brief", read_timeout=cfg.READ_TIMEOUT))

r.close()
