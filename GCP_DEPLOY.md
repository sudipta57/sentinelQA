# GCP Compute Engine — Backend Deployment Guide

Deploy the SentinelQA backend to a GCP **e2-standard-2** VM in ~15 minutes.  
Everything runs inside Docker — no Python or Node needed on the VM.

---

## What You Need Before Starting

- [ ] A GCP account with a project created → [console.cloud.google.com](https://console.cloud.google.com)
- [ ] `gcloud` CLI installed on your **local machine** → [Install guide](https://cloud.google.com/sdk/docs/install)
- [ ] Your repo pushed to GitHub (or you'll `scp` files to the VM)
- [ ] Your `GEMINI_API_KEY` and `DATABASE_URL` ready

---

## Step 1 — Authenticate gcloud (run on your local machine)

```bash
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID
```

> Find your Project ID at: console.cloud.google.com → top dropdown

---

## Step 2 — Create the VM

Run this single command on your **local machine**:

```bash
gcloud compute instances create sentinelqa-backend \
  --machine-type=e2-standard-2 \
  --zone=us-central1-a \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB \
  --boot-disk-type=pd-standard \
  --tags=sentinelqa-backend \
  --metadata=startup-script='#!/bin/bash
    apt-get update -y
    curl -fsSL https://get.docker.com | sh
    apt-get install -y docker-compose-plugin
    usermod -aG docker ubuntu
    systemctl enable docker
    systemctl start docker'
```

The `startup-script` automatically installs Docker when the VM boots — saves you doing it manually.

> ⏱️ VM creation takes ~60 seconds. Docker install runs in the background another ~60 seconds.

---

## Step 3 — Open Port 8000 in the Firewall

```bash
gcloud compute firewall-rules create allow-sentinelqa-8000 \
  --allow=tcp:8000 \
  --target-tags=sentinelqa-backend \
  --description="SentinelQA backend API port"
```

---

## Step 4 — Get the VM's External IP

```bash
gcloud compute instances describe sentinelqa-backend \
  --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```
<!-- 34.122.134.236 -->
**Save this IP** — you'll use it as your backend URL:  
`http://YOUR_VM_IP:8000`

---

## Step 5 — Copy Your Project Files to the VM

> **Note**: `gcloud compute scp` does NOT support `--exclude`. Use the tarball approach instead.

On your **local machine**, from the `sentinelqa2/` root:

```bash
# 1. Pack only the backend-relevant files into a tarball
tar \
  --exclude='./.git' \
  --exclude='./.venv' \
  --exclude='./node_modules' \
  --exclude='./frontend' \
  --exclude='./demo-app' \
  --exclude='./screenshots' \
  --exclude='./*.png' \
  -czf /tmp/sentinelqa-backend.tar.gz .

# 2. Copy the tarball to the VM
gcloud compute scp --zone=us-central1-a \
  /tmp/sentinelqa-backend.tar.gz \
  sentinelqa-backend:/tmp/sentinelqa-backend.tar.gz

# 3. Extract on the VM
gcloud compute ssh sentinelqa-backend --zone=us-central1-a \
  --command='mkdir -p ~/sentinelqa2 && tar -xzf /tmp/sentinelqa-backend.tar.gz -C ~/sentinelqa2 && echo "Done!" && ls ~/sentinelqa2'
```

---

## Step 6 — SSH Into the VM

```bash
gcloud compute ssh sentinelqa-backend --zone=us-central1-a
```

All remaining commands run **inside the VM**.

---

## Step 7 — Wait for Docker to Finish Installing

```bash
# Check Docker is ready (may take 1-2 min after first boot)
docker --version

# If command not found, wait 30 seconds and retry
# Or run manually:
sudo apt-get update -y && curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

---

## Step 8 — Create the .env File on the VM

```bash
cd /home/ubuntu/sentinelqa2

cat > .env << 'EOF'
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
CORS_ORIGIN=*
EOF
```

> Setting `CORS_ORIGIN=*` is fine for a 1-day hackathon demo. It means any frontend can call your API.

Edit the file with real values:
```bash
nano .env
```

---

## Step 9 — Build and Start the Backend

```bash
cd /home/ubuntu/sentinelqa2

# Build and start (this takes 3-5 minutes on first run — Playwright downloads Chromium)
docker compose -f docker-compose.gcp.yml up -d --build

# Watch the build logs
docker compose -f docker-compose.gcp.yml logs -f
```

When you see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

The backend is live. Press `Ctrl+C` to stop watching logs (the container keeps running).

---

## Step 10 — Verify It's Working

From your **local machine**:

```bash
# Replace with your VM's actual IP
curl http://YOUR_VM_IP:8000/health
```

Expected response:
```json
{"status": "ok"}
```

Also test the API docs:  
Open `http://YOUR_VM_IP:8000/docs` in your browser.

---

## Step 11 — Point Your Frontend at the VM

Wherever your frontend runs (local dev, Vercel, etc.), set the backend URL to:

```
http://YOUR_VM_IP:8000
```

**For local frontend dev** — update `frontend/.env.local`:
```env
VITE_BACKEND_URL=http://YOUR_VM_IP:8000
```

**For Vercel** — go to Project Settings → Environment Variables:
```
VITE_BACKEND_URL = http://YOUR_VM_IP:8000
```

Then redeploy the frontend.

---

## Useful Commands (run inside the VM)

```bash
# View live backend logs
docker compose -f docker-compose.gcp.yml logs -f backend

# Check container status
docker compose -f docker-compose.gcp.yml ps

# Restart the backend
docker compose -f docker-compose.gcp.yml restart backend

# Rebuild after code changes
docker compose -f docker-compose.gcp.yml up -d --build

# Check last agent run result
curl http://localhost:8000/api/last-run
```

---

## After the Hackathon — Delete Everything

Run these on your **local machine** to avoid any further charges:

```bash
# Delete the VM (this stops billing immediately)
gcloud compute instances delete sentinelqa-backend \
  --zone=us-central1-a \
  --quiet

# Delete the firewall rule
gcloud compute firewall-rules delete allow-sentinelqa-8000 --quiet
```

> ⚠️ The VM charges stop the moment it's deleted. Don't forget this step!

---

## Troubleshooting

### "Permission denied" running docker

```bash
sudo usermod -aG docker $USER
newgrp docker
# Then retry your docker command
```

### Build fails — "playwright install chromium" error

Usually a network timeout. Just retry:
```bash
docker compose -f docker-compose.gcp.yml up -d --build
```

### Can't reach http://YOUR_VM_IP:8000

Check the firewall rule was created:
```bash
gcloud compute firewall-rules list --filter="name=allow-sentinelqa-8000"
```

Check the container is running:
```bash
docker ps
```

### CORS errors in the browser

Make sure `.env` on the VM has the correct `CORS_ORIGIN`:
```bash
# For hackathon — allow everything
CORS_ORIGIN=*
```

Then restart:
```bash
docker compose -f docker-compose.gcp.yml restart backend
```

---

## Cost Summary

| Resource | Rate | 1 Day |
|---|---|---|
| e2-standard-2 VM | $0.067/hr | ~$1.61 |
| 20GB boot disk | $0.04/GB/month | ~$0.03 |
| Egress (est. 1GB) | $0.12/GB | ~$0.12 |
| **Total** | | **~$1.76** |

If you have GCP free trial credits ($300), cost = **$0**.
