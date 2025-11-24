import subprocess, sys, time

steps = [
  "10_create_vlans_b4.py",
  "11_set_trunk_b4.py",
  "20_create_svis_b4.py",
  "30_create_vrfs_b4.py",
  "31_bind_svis_to_vrf_b4.py",
  "35_create_vrrp_b4.py",
  "50_create_ospf_b4.py",
  "40_collect_outputs_b4.py",
]

for s in steps:
    subprocess.run([sys.executable, s], check=True)
    time.sleep(0.5)

print("OK")
