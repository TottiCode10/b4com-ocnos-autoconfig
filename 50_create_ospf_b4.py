# 50_create_ospf_b4.py
import b4_cfg as cfg
from b4_netmiko import B4

# =========================
# Идея скрипта
# =========================
# Создаём OSPF :
# - Количество процессов = VRF_COUNT
# - PID идёт от OSPF_PROCESS_BASE
# - Сеть берётся по той же IP-схеме, что и в 31-м скрипте
# То есть на каждый VRF объявляется своя /24.

def subnet_for_idx(idx: int) -> str:
    b = cfg.IP_BASE_B_START + (idx // cfg.NET_SIZE)
    c = cfg.IP_BASE_C_START + (idx % cfg.NET_SIZE)
    return f"{cfg.IP_BASE_A}.{b}.{c}.0/24"

def build_cmds():
    cmds = []
    for i in range(cfg.VRF_COUNT):
        vid = cfg.VLAN_START + i
        vrf = f"{cfg.VRF_PREFIX}{vid}"
        net = subnet_for_idx(cfg.OSPF_IDX_START + i)
        pid = cfg.OSPF_PROCESS_BASE + i

        cmds += [
            f"router ospf {pid} {vrf}",
            f"network {net} area 0",
            "exit",
        ]
    return cmds

r = B4(
    cfg.HOST, cfg.USER, cfg.PASSWORD, cfg.DEVICE_TYPE, cfg.PORT,
    global_delay=cfg.GLOBAL_DELAY_FACTOR, out_dir=cfg.OUT_DIR, tag="50_create_ospf"
).open()

try:
    if not cfg.OSPF_ENABLE:
        r.save_text("verify", "OSPF disabled in cfg")
    else:
        r.cfg(build_cmds(), per_batch=cfg.CFG_PER_BATCH,
              read_timeout=cfg.READ_TIMEOUT, sleep_between=cfg.CFG_SLEEP)

        
        r.save_text("verify", r.show("show ip ospf interface brief", read_timeout=cfg.READ_TIMEOUT))
finally:
    r.close()
