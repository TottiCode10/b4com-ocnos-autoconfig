# 30_create_vrfs_b4.py
import b4_cfg as cfg
from b4_netmiko import B4

# =========================
# Идея скрипта
# =========================
# Создаём набор VRF по схеме 1:1 с первыми VRF_COUNT VLAN.
# Имя VRF строится как "<VRF_PREFIX><VID>".

vrfs = [f"{cfg.VRF_PREFIX}{cfg.VLAN_START + i}" for i in range(cfg.VRF_COUNT)]
cmds = [f"ip vrf {v}" for v in vrfs]

r = B4(
    cfg.HOST, cfg.USER, cfg.PASSWORD, cfg.DEVICE_TYPE, cfg.PORT,
    global_delay=cfg.GLOBAL_DELAY_FACTOR, out_dir=cfg.OUT_DIR, tag="30_create_vrfs"
).open()

r.cfg(cmds, per_batch=cfg.CFG_PER_BATCH, read_timeout=cfg.READ_TIMEOUT, sleep_between=cfg.CFG_SLEEP)

# Проверяем, что VRF реально создались
r.save_text("show_run_vrf", r.show("show running-config vrf", read_timeout=cfg.READ_TIMEOUT))

r.close()
