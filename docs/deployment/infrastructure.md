# Infrastructure Setup

This document tracks the infrastructure components and setup procedures for the InGest-LLM.as service deployment.

## Overview

InGest-LLM.as requires several infrastructure components for production deployment:
- Application hosting (local or cloud)
- Tunnel management for secure external access
- Supporting services (memOS.as, embedding services)

## Components

### 1. Cloudflared Tunnel Agent

**Status:** ✅ Installed and Verified  
**Version:** 2025.8.1 (built 2025-08-21-1534 UTC)  
**Installation Date:** December 31, 2025  
**Installation Method:** winget package manager

#### Installation Details

The cloudflared daemon has been installed on the Windows host machine to provide secure tunnel connectivity to Cloudflare's network.

**Installation Command:**
```powershell
winget install Cloudflare.cloudflared
```

**Verification:**
```powershell
cloudflared --version
# Output: cloudflared version 2025.8.1 (built 2025-08-21-1534 UTC)
```

#### Installation Requirements

- **Administrator privileges:** Required for system-wide installation
- **Terminal restart:** After installation, close and reopen PowerShell/Terminal to ensure PATH is updated
- **Windows version:** Compatible with Windows 10/11 and Windows Server

#### Post-Installation Configuration

After successful installation, the following steps are needed to configure the tunnel:

1. **Authenticate with Cloudflare:**
   ```powershell
   cloudflared tunnel login
   ```
   This opens a browser window for Cloudflare authentication.

2. **Create a tunnel:**
   ```powershell
   cloudflared tunnel create ingest-llm-tunnel
   ```
   Replace `ingest-llm-tunnel` with your preferred tunnel name.

3. **Configure DNS routing:**
   ```powershell
   cloudflared tunnel route dns ingest-llm-tunnel ingest-llm.yourdomain.com
   ```
   Replace with your actual hostname.

4. **Create tunnel configuration file:**
   Create a `config.yml` in `%USERPROFILE%\.cloudflared\` directory:
   ```yaml
   tunnel: ingest-llm-tunnel
   credentials-file: /path/to/tunnel-credentials.json
   
   ingress:
     - hostname: ingest-llm.yourdomain.com
       service: http://localhost:8000
     - service: http_status:404
   ```

5. **Run as Windows Service (optional):**
   For automatic startup and persistent operation:
   ```powershell
   cloudflared service install
   ```

#### Verification Steps

- [x] cloudflared binary installed via winget
- [x] Terminal restarted to update PATH
- [x] `cloudflared --version` returns valid version string (2025.8.1)
- [ ] Tunnel created and configured (pending)
- [ ] DNS routing configured (pending)
- [ ] Service running and tested (pending)

### 2. Application Service

**Status:** ⏳ Development  
**Deployment Target:** Windows host with Docker support

The InGest-LLM.as service can be deployed via:
- Docker container (recommended)
- Direct Python/Poetry execution
- Windows service wrapper

### 3. Supporting Services

The following services are required for full functionality:

- **memOS.as:** Memory storage backend
  - Status: ⏳ Configuration pending
  - Default URL: `http://devenviro_memos_api:8090`

- **Embedding Service:** LM Studio or Ollama
  - Status: ⏳ Configuration pending
  - Default URL: `http://localhost:1234/v1`

- **Observability Stack** (optional):
  - Langfuse for tracing
  - Prometheus for metrics
  - Jaeger for distributed tracing

## Network Architecture

```
Internet
    ↓
Cloudflare Network
    ↓
cloudflared tunnel (Windows host)
    ↓
InGest-LLM.as service (localhost:8000)
    ↓
memOS.as (internal network)
    ↓
Embedding Service (localhost)
```

## Security Considerations

- Cloudflare tunnel provides encrypted connection without exposing ports
- No inbound firewall rules required
- Authentication handled through Cloudflare dashboard
- Service-to-service communication on internal network only

## Maintenance

### Updating cloudflared

To update the cloudflared binary:
```powershell
winget upgrade Cloudflare.cloudflared
```

### Monitoring

Check tunnel status:
```powershell
cloudflared tunnel info ingest-llm-tunnel
```

View tunnel logs:
```powershell
# If running as service
Get-EventLog -LogName Application -Source cloudflared -Newest 50
```

## References

- [Cloudflare Tunnel Documentation](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [InGest-LLM.as Service Status](../STATUS.md)
- [Docker Deployment Guide](../docker-compose.README.md)

## Change Log

| Date | Component | Version | Change | Status |
|------|-----------|---------|--------|--------|
| 2025-12-31 | cloudflared | 2025.8.1 | Initial installation on Windows host | ✅ Complete |
