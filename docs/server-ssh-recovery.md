# Server SSH Recovery

## Infrastructure

| Resource | Value |
|----------|-------|
| Instance | `i-00d3bea88a7fc01ea` (mbabb), `t2.xlarge`, `us-east-1c` |
| OS | Ubuntu 22.04 LTS |
| EIP | `34.197.214.67` → `10.0.2.253` |
| Root volume | `vol-0ce57ce4b012bf874`, 512GB gp2 |
| VPN server | `i-0811c145059c295cb` (vpn-prod), `10.0.4.214` |
| SSH key (VPN) | `~/.ssh/til_key`, user `openvpnas` |
| SSH key (mbabb) | default (`~/.ssh/key`), user `mbabb` |

## SSH tunnel (normal operation)

```bash
ssh -f -N -L 27018:localhost:27017 -p 1022 mbabb@10.0.2.253
```

Requires: VPN connected, fail2ban not banning `10.0.4.214`.

## What can go wrong

### 1. fail2ban bans the VPN server

All VPN client traffic is NAT'd through `10.0.4.214`. Repeated failed connection attempts (e.g., probing when sshd is down) trigger fail2ban's sshd jail.

**Symptom**: Port 1022 returns "Connection refused" but sshd is listening (`ss -tlnp` shows it).

**Fix** (via port 22, which fail2ban doesn't monitor):
```bash
ssh -p 22 mbabb@10.0.2.253 "sudo fail2ban-client set sshd unbanip 10.0.4.214"
```

**Prevention**: `/etc/fail2ban/jail.local` has `ignoreip` whitelisting `10.0.4.214` and `10.1.128.0/24`. If this file gets reset, re-add:
```ini
[DEFAULT]
ignoreip = 127.0.0.1/8 10.0.4.214 10.1.128.0/24
```

### 2. sshd not running after reboot

Ubuntu service is `ssh`, not `sshd`. If it's not enabled, it won't start on boot.

**Check**: `systemctl is-enabled ssh` — should say `enabled`.

**Fix** (if you can't SSH in): Stop the instance, set user data, start:
```bash
aws ec2 stop-instances --instance-ids i-00d3bea88a7fc01ea
aws ec2 wait instance-stopped --instance-ids i-00d3bea88a7fc01ea

USERDATA=$(cat <<'SCRIPT' | base64
#cloud-boothook
#!/bin/bash
ufw allow 22/tcp || true
ufw allow 1022/tcp || true
grep -q "^Port 1022" /etc/ssh/sshd_config || echo "Port 1022" >> /etc/ssh/sshd_config
(sleep 10 && systemctl enable ssh && systemctl restart ssh) &
SCRIPT
)
aws ec2 modify-instance-attribute --instance-id i-00d3bea88a7fc01ea --user-data "Value=$USERDATA"
aws ec2 start-instances --instance-ids i-00d3bea88a7fc01ea
```

**Critical**: The boothook must start ssh in the background (`&`) or it deadlocks cloud-init. Use `#cloud-boothook` (not `#cloud-config runcmd`) — runcmd only runs on first boot.

### 3. Instance unresponsive (all ports down)

EC2 health checks pass but nothing is reachable.

**Diagnosis**:
```bash
aws ec2 describe-instance-status --instance-ids i-00d3bea88a7fc01ea
aws ec2 get-console-output --instance-id i-00d3bea88a7fc01ea --output text | tail -30
```

**Fix**: Reboot first (`aws ec2 reboot-instances`). If that doesn't work, stop/start cycle. The EIP is persistent — stop/start won't lose the public IP.

## Debugging checklist

```bash
# 1. Can you reach the instance?
nc -vz -w 5 10.0.2.253 443    # web server (Docker)
nc -vz -w 5 10.0.2.253 1022   # ssh
nc -vz -w 5 10.0.2.253 22     # ssh (backup)

# 2. "Connection refused" on 1022 but 443 works?
#    → fail2ban. SSH in via port 22 and unban.

# 3. "Timeout" on everything?
#    → Instance or VPN issue. Check EC2 status + VPN connection.

# 4. Can VPN server reach it?
ssh -i ~/.ssh/til_key openvpnas@10.0.4.214 "nc -vz -w 3 10.0.2.253 1022"

# 5. Is sshd running?
ssh -p 22 mbabb@10.0.2.253 "sudo ss -tlnp | grep ssh"

# 6. Is fail2ban blocking?
ssh -p 22 mbabb@10.0.2.253 "sudo fail2ban-client status sshd"

# 7. No SSH access at all? Use stop/start with cloud-boothook (see above).
```

## Port map

| Port | Service | SG source | UFW | fail2ban |
|------|---------|-----------|-----|----------|
| 22 | sshd | VPN SG only | allow | no |
| 1022 | sshd | VPN SG only | allow | yes (jail: sshd) |
| 443 | nginx (Docker) | public | allow | no |
| 27017 | MongoDB | internal | — | no |
