# 10_create_vlans_b4.py
import b4_cfg as cfg
from b4_netmiko import B4

# =========================
# Идея скрипта
# =========================
# Создаём диапазон VLAN и привязываем их к VLAN bridge.
# Диапазон берём из cfg: VLAN_START ... VLAN_START+VLAN_COUNT-1

vlan_ids = [cfg.VLAN_START + i for i in range(cfg.VLAN_COUNT)]

# 1) включаем bridge в vlan режим
# 2) переходим в vlan database
# 3) создаём VLAN и цепляем к bridge
cmds = (
    [f"bridge {cfg.BRIDGE_ID} protocol {cfg.BRIDGE_PROTOCOL} vlan-bridge", "vlan database"]
    + [f"vlan {vid} bridge {cfg.BRIDGE_ID} state enable" for vid in vlan_ids]
    + ["exit"]
)

r = B4(
    cfg.HOST, cfg.USER, cfg.PASSWORD, cfg.DEVICE_TYPE, cfg.PORT,
    global_delay=cfg.GLOBAL_DELAY_FACTOR, out_dir=cfg.OUT_DIR, tag="10_create_vlans"
).open()

# Льём конфиг пакетами, чтобы устройство не захлебнулось на больших объёмах
r.cfg(cmds, per_batch=cfg.CFG_PER_BATCH, read_timeout=cfg.READ_TIMEOUT, sleep_between=cfg.CFG_SLEEP)

# Контрольная точка: должны увидеть созданный диапазон
r.save_text("show_vlan_brief", r.show("show vlan brief", read_timeout=cfg.READ_TIMEOUT))

r.close()
