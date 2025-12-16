# Unified Metrics Stack Guide

## Architecture Overview

Three containers run as systemd services in the `sglang-stack-pod.service` container pod:

1. `sglang.service` - Qwen3-32B-AWQ model server on GPU
2. `prometheus.service` - Metrics collector (scrapes `localhost:30000`)
3. `grafana.service` - Visualization dashboard
4. `openwebui.service` - Web interface for model interaction (http://localhost:8080)

## Service Configuration

### Prometheus

- **Image:** prom/prometheus:latest
- **Volumes:**
  - `./prometheus.yaml:/etc/prometheus/prometheus.yml`
- **Configuration:**
  ```yaml
  (Scrape configuration for sglang server at 127.0.0.1:30000 with 5s interval)
  ```

### Grafana

- **Image:** grafana/grafana:latest
- **Volumes:**
  - `./grafana/datasources:/etc/grafana/provisioning/datasources`
  - `./grafana/dashboards:/etc/grafana/provisioning/dashboards`
- **Access:** [Grafana](http://localhost:3000) (admin/admin_secure_password)
- **Prometheus Link:** [Prometheus](http://localhost:9091)

## Deployment Workflow

1. **Symlink services** to systemd:

   ```bash
   stow -R -v -t ~/.config/containers/systemd/ quadlet
   ```

2. **Reload systemd**:

   ```bash
   systemctl --user daemon-reload
   ```

3. **Start services**:
   ```bash
   systemctl --user enable --now sglang-stack-pod.service
   ```

## Service Monitoring

### Status Checks

```bash
# Pod status
systemctl --user status sglang-stack-pod.service

# Individual service status
systemctl --user status sglang.service
systemctl --user status prometheus.service
systemctl --user status grafana.service
```

### Log Management

```bash
# Live pod logs
journalctl --user -u sglang-stack-pod.service -f

# Live service logs
journalctl --user -u prometheus.service -f

# Historical logs (last 5 minutes)
journalctl --user -u sglang-stack-pod.service --since "5 minutes ago"
```

> ⚠️ To disable auto-start:
> `systemctl --user disable sglang-stack-pod.service`
> To stop services:
> `systemctl --user stop sglang-stack-pod.service`
