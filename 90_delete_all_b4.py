# 90_delete_all_b4.py
import b4_cfg as cfg
from b4_netmiko import B4

# =========================
# Идея скрипта
# =========================
# Cleanup в обратном порядке:
# 1) снимаем VLAN с trunk и переводим порт в access
# 2) удаляем VLAN-диапазон (SVI уедут вместе с VLAN)
# 3) удаляем VRF, которые были созданы 

first = cfg.VLAN_START
last = cfg.VLAN_START + cfg.VLAN_COUNT - 1

vlan_ids_for_vrf = [cfg.VLAN_START + i for i in range(cfg.VRF_COUNT)]
vrfs = [f"{cfg.VRF_PREFIX}{vid}" for vid in vlan_ids_for_vrf]

cmds = [
    f"interface {cfg.TRUNK_IF}",
    f"switchport trunk allowed vlan remove {first}-{last}",
    "switchport mode access",
    "exit",
]

cmds += [
    "vlan database",
    f"no vlan {first}-{last} bridge {cfg.BRIDGE_ID}",
    "exit",
]

cmds += [f"no ip vrf {v}" for v in vrfs]

r = B4(
    cfg.HOST, cfg.USER, cfg.PASSWORD, cfg.DEVICE_TYPE, cfg.PORT,
    global_delay=cfg.GLOBAL_DELAY_FACTOR, out_dir=cfg.OUT_DIR, tag="90_delete_all"
).open()

r.cfg(cmds, per_batch=cfg.CFG_PER_BATCH, read_timeout=cfg.READ_TIMEOUT, sleep_between=cfg.CFG_SLEEP)

# Проверяем, что VLAN-ы реально ушли
r.save_text("show_vlan_brief_after", r.show("show vlan brief", read_timeout=cfg.READ_TIMEOUT))

r.close()
