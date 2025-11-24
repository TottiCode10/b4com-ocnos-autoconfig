# 40_collect_outputs_b4.py
import b4_cfg as cfg
from b4_netmiko import B4

# =========================
# Идея скрипта
# =========================
# Сбор диагностических show после всех шагов.
# Здесь нет конфигурации — только фиксация состояния устройства.

r = B4(
    cfg.HOST, cfg.USER, cfg.PASSWORD, cfg.DEVICE_TYPE, cfg.PORT,
    global_delay=cfg.GLOBAL_DELAY_FACTOR, out_dir=cfg.OUT_DIR, tag="40_collect"
).open()

r.save_text("show_version", r.show("show version", read_timeout=cfg.READ_TIMEOUT))
r.save_text("show_vlan_brief", r.show("show vlan brief", read_timeout=cfg.READ_TIMEOUT))
r.save_text("show_ip_int_brief", r.show("show ip interface brief", read_timeout=cfg.READ_TIMEOUT))
r.save_text("show_run_trunk", r.show(f"show running-config interface {cfg.TRUNK_IF}", read_timeout=cfg.READ_TIMEOUT))
r.save_text("show_run_vrf", r.show("show running-config vrf", read_timeout=cfg.READ_TIMEOUT))
r.save_text("show_running", r.show("show running-config", read_timeout=cfg.READ_TIMEOUT))
r.save_text("show_ip_ospf", r.show("show ip ospf interface brief", read_timeout=cfg.READ_TIMEOUT))
r.save_text("show_ip_ospf_ro", r.show("show ip ospf route", read_timeout=cfg.READ_TIMEOUT))
r.save_text("show_ip_VRF", r.show("show ip vrf", read_timeout=cfg.READ_TIMEOUT))

r.close()
