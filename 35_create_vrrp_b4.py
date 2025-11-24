# 35_create_vrrp_b4.py
import re
from pathlib import Path
import b4_cfg as cfg
from b4_netmiko import B4

# =========================
# Идея скрипта
# =========================
# Находим реальный IP на каждом SVI и вешаем VRRP:
# - VRID = VRRP_START_ID + индекс
# - VIP берём из ip address на интерфейсе 
# Если IP на интерфейсе нет — группу пропускаем и пишем в errors.log.

IP_RE = re.compile(r"^\s*ip address\s+(\d+\.\d+\.\d+\.\d+)(?:/\d+)?", re.I | re.M)

def ifn(vid: int) -> str:
    return f"vlan1.{vid}"

vlan_ids = [cfg.VLAN_START + i for i in range(min(cfg.VRRP_COUNT, cfg.SVI_COUNT))]
start_id = cfg.VRRP_START_ID
priority = cfg.VRRP_PRIORITY

r = B4(
    cfg.HOST, cfg.USER, cfg.PASSWORD, cfg.DEVICE_TYPE, cfg.PORT,
    global_delay=cfg.GLOBAL_DELAY_FACTOR, out_dir=cfg.OUT_DIR, tag="35_create_vrrp"
).open()

plan = []
cmds = []
miss = []

for idx, vid in enumerate(vlan_ids):
    ifname = ifn(vid)
    vrid = start_id + idx

    # Смотрим конфиг интерфейса и вытаскиваем IP
    rc = r.show(f"show running-config interface {ifname}", read_timeout=cfg.READ_TIMEOUT)
    m = IP_RE.search(rc)

    if not m:
        miss.append(f"{ifname} (VRID {vrid})")
        continue

    vip = m.group(1)
    plan.append(f"VRID {vrid} -> {ifname} VIP {vip}")

    cmds += [
        f"router vrrp {vrid} {ifname}",
        f"virtual-ip {vip}",
        f"priority {priority}",
        "v2-compatible",
        "enable",
        "exit",
    ]

# План и фактическая заливка
if plan:
    r.save_text("vrrp_plan", "\n".join(plan))
if cmds:
    r.cfg(cmds, per_batch=cfg.CFG_PER_BATCH, read_timeout=cfg.READ_TIMEOUT, sleep_between=cfg.CFG_SLEEP)

# Что пропустили — фиксируем в errors.log
if miss:
    Path(r.error_log).parent.mkdir(parents=True, exist_ok=True)
    with open(r.error_log, "a", encoding="utf-8") as f:
        f.write("[VRRP skipped]\n")
        for line in miss:
            f.write(line + "\n")

r.save_text("show_vrrp", r.show("show vrrp summary", read_timeout=cfg.READ_TIMEOUT))
r.close()
