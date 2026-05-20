# iptables Rules for PulseDash Tailscale Access

## Overview
Exposes PostgreSQL and MinIO services through Tailscale VPN via iptables NAT rules.

> Note: the production bridge name is pinned to `pulsedash-br` and the subnet/IPs are fixed in [podman-compose.yml](podman-compose.yml). The addresses below are the intended stable assignments for the Tailscale DNAT rules.

---

## PostgreSQL (Port 5432)

### PREROUTING (Incoming traffic redirection)
```bash
iptables -t nat -I PREROUTING -i tailscale0 -p tcp --dport 5432 -j DNAT --to 10.89.3.2:5432
```
Redirects incoming Tailscale traffic on port 5432 to PostgreSQL container IP (10.89.3.2)

### FORWARD (Internal routing)
```bash
iptables -I FORWARD -p tcp -d 10.89.3.2 --dport 5432 -j ACCEPT
```
Allows forwarding of TCP traffic to PostgreSQL container

### POSTROUTING (Return path)
```bash
iptables -t nat -I POSTROUTING -o tailscale0 -p tcp --sport 5432 -j MASQUERADE
```
Rewrites return traffic source to appear from host, routing back through Tailscale

---

## MinIO S3 API (Port 9000)

### PREROUTING
```bash
iptables -t nat -I PREROUTING -i tailscale0 -p tcp --dport 9000 -j DNAT --to 10.89.3.4:9000
```
Redirects Tailscale traffic on 9000 to MinIO container (10.89.3.4)

### FORWARD
```bash
iptables -I FORWARD -p tcp -d 10.89.3.4 --dport 9000 -j ACCEPT
```
Allows forwarding to MinIO S3 API port

### POSTROUTING
```bash
iptables -t nat -I POSTROUTING -o tailscale0 -p tcp --sport 9000 -j MASQUERADE
```
Return path for MinIO S3 traffic

---

## MinIO Console (Port 9001)

### PREROUTING
```bash
iptables -t nat -I PREROUTING -i tailscale0 -p tcp --dport 9001 -j DNAT --to 10.89.3.4:9001
```
Redirects Tailscale traffic on 9001 to MinIO console

### FORWARD
```bash
iptables -I FORWARD -p tcp -d 10.89.3.4 --dport 9001 -j ACCEPT
```
Allows forwarding to MinIO console port

### POSTROUTING
```bash
iptables -t nat -I POSTROUTING -o tailscale0 -p tcp --sport 9001 -j MASQUERADE
```
Return path for MinIO console traffic

---

## UFW Rules (Supplementary)

```bash
# PostgreSQL
ufw allow 5432/tcp

# MinIO S3 API
ufw allow 9000/tcp

# MinIO Console
ufw allow 9001/tcp
```

---

## Current Container Network Information

These addresses are the pinned assignments used by the running `pulsedash-network`.

| Service | Container IP | Port | Network |
|---------|-------------|------|---------|
| PostgreSQL | 10.89.3.2 | 5432 | pulsedash-network |
| Redis | 10.89.3.3 | 6379 | pulsedash-network |
| MinIO | 10.89.3.4 | 9000, 9001 | pulsedash-network |

---

## Persistence

All rules saved to:
```bash
/etc/iptables/rules.v4
```

Restored automatically on reboot via `netfilter-persistent` service.

---

## Testing from Tailscale

```bash
# PostgreSQL
nc -zv api-pulsedash 5432
psql -h api-pulsedash -U pulsedash -d pulsedash

# MinIO S3 API
nc -zv api-pulsedash 9000

# MinIO Console
curl http://api-pulsedash:9001
```

---

## NAT Flow Diagram

```
Tailscale Client (100.81.251.100)
         ↓
tailscale0 interface
         ↓
[PREROUTING] DNAT: :5432 → 10.89.1.2:5432
         ↓
[FORWARD] Allow routing to container
         ↓
PostgreSQL Container (10.89.3.2:5432)
         ↓
[POSTROUTING] MASQUERADE: Return via tailscale0
         ↓
Tailscale Client receives response
```

---

## Security Notes

**Exposed via Tailscale only** - No direct internet exposure  
Access restricted to Tailscale VPN members  
Encrypted via Tailscale WireGuard tunnel
