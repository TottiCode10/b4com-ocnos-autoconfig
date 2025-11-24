# 31_bind_svis_to_vrf_b4.py
import b4_cfg as cfg
from b4_netmiko import B4

# =========================
# Идея скрипта
# =========================
# 1) заходим в интерфейс vlan1.<VID>
# 2) привязываем к своему VRF
# 3) даём IP (по схеме из cfg)
# Важно: порядок "ip vrf forwarding" -> "ip address".
# Если сначала IP, потом VRF — IP слетит.

def ip_for_idx(idx: int) -> str:
    a = cfg.IP_BASE_A
    b = cfg.IP_BASE_B_START + (idx // cfg.NET_SIZE)
    c = cfg.IP_BASE_C_START + (idx % cfg.NET_SIZE)
    return f"{a}.{b}.{c}.1/24"

def svi_name(vid: int) -> str:
    return f"vlan1.{vid}"

vlan_ids = [cfg.VLAN_START + i for i in range(cfg.VRF_COUNT)]
vrfs = [f"{cfg.VRF_PREFIX}{vid}" for vid in vlan_ids]

cmds = []
for i, vid in enumerate(vlan_ids):
    cmds += [
        f"interface {svi_name(vid)}",
        f"ip vrf forwarding {vrfs[i]}",
        f"ip address {ip_for_idx(i)}",
        "no shutdown",
        "exit",
    ]

r = B4(
    cfg.HOST, cfg.USER, cfg.PASSWORD, cfg.DEVICE_TYPE, cfg.PORT,
    global_delay=cfg.GLOBAL_DELAY_FACTOR, out_dir=cfg.OUT_DIR, tag="31_bind_svis_to_vrfs"
).open()

r.cfg(cmds, per_batch=cfg.CFG_PER_BATCH, read_timeout=cfg.READ_TIMEOUT, sleep_between=cfg.CFG_SLEEP)

# Контроль: IP должны появиться на SVI
r.save_text("show_ip_int_brief", r.show("show ip interface brief", read_timeout=cfg.READ_TIMEOUT))

r.close()
