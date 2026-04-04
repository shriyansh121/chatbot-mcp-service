# 🚀 Deployment Guide: DigitalOcean & Name.com

This guide will help you deploy your **NexusAI GCP Assistant** to a DigitalOcean Droplet using the Docker configuration we just created.

## 1. DigitalOcean Settings
### Create a Droplet
1. Log in to **DigitalOcean**.
2. Click **Create** -> **Droplets**.
3. **Region**: Choose a location closest to you (e.g., Bangalore, Singapore).
4. **Image**: Choose **Ubuntu 24.04** or **Docker (Marketplace App)**. 
   - *Tip*: Selecting the **Docker** app from the Marketplace tab saves time!
5. **Size**: The **Basic** $6/mo (1GB RAM, 1 CPU) is perfectly sufficient for this college project.
6. **Authentication**: Choose **SSH Keys** (preferred) or Password.
7. Click **Create Droplet**.

### Get Your IP Address
- Copy the **IPv4 address** of your new Droplet (e.g., `157.245.xx.xx`).

---

## 2. Domain & DNS (Name.com)
### Map Your Domain
1. Log in to **Name.com**.
2. Go to **My Domains** and click on your domain.
3. Click **DNS Templates** or **DNS Records**.
4. Add an **A Record**:
   - **Host**: `@` (for yourdomain.com)
   - **Answer**: Paste your Droplet's **IPv4 address**.
   - **TTL**: 300
5. Add another **A Record** for `www` (optional):
   - **Host**: `www`
   - **Answer**: Paste your Droplet's **IPv4 address**.

---

## 3. Server Setup (Via Console/SSH)
### Connect to Server
Open your terminal (on your Mac) and run:
```bash
ssh root@YOUR_DROPLET_IP
```

### Install Docker (If not using Marketplace Image)
If you chose a plain Ubuntu image, run:
```bash
curl -fsSL https://get.docker.com | sh
```

### Clone Your Code
```bash
# Clone your private repo (you'll need to sign in or use a Personal Access Token)
git clone https://github.com/shriyansh121/chatbot-mcp-service.git
cd chatbot-mcp-service
```

---

## 4. Run the Application
### Setup Environment
1. Ensure your `.env.dev` is present (if not pushed to git for security, create it manually):
```bash
nano .env.dev  # Paste your content here then Ctrl+O, Enter, Ctrl+X
```

### Build and Start
```bash
docker compose up -d --build
```
The `-d` flag runs it in the background.

---

## 5. Security
### Configure Firewall
Allow HTTP (80) and HTTPS (443):
```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

---

## ✅ Verification
1. Open your browser and go to `http://your-domain.com`.
2. Ensure you can see the **NexusAI** Login page.
3. Login and try a command like `List running VMs`.

### Troubleshooting
- **Logs**: `docker compose logs -f`
- **Rebuild**: If you push code, run `git pull` then `docker compose up -d --build`.
