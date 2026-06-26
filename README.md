# Flask MySQL App on GCP Free Tier

This repo is set up for a low-cost GCP deployment: one Compute Engine VM runs both the Flask app and MySQL with Docker Compose. The GitHub Actions workflow redeploys the app to the VM on pushes to `main`.

## Cost target

Use an Always Free eligible Compute Engine VM, for example an `e2-micro` in `us-central1`, with a standard persistent disk no larger than 30 GB. Check the current Google Cloud Free Tier terms before creating resources. Cloud SQL is intentionally not used because it is a managed, billable MySQL service.

Create a budget alert in GCP Billing before deploying.

## One-time GCP VM setup

Create an Ubuntu VM with:

- Machine type: `e2-micro`
- Region: `us-central1`
- Boot disk: standard persistent disk, 30 GB or smaller
- Firewall: allow HTTP traffic on port `80`
- SSH: prefer restricting SSH to your IP address

SSH into the VM and install Docker, Compose, and rsync:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg rsync
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
sudo mkdir -p /opt/app_python_mysql
sudo chown "$USER:$USER" /opt/app_python_mysql
```

An `e2-micro` is memory constrained. Add a small swap file so MySQL and Docker builds are less likely to run out of memory:

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Log out and back in so Docker group membership takes effect, then verify:

```bash
docker --version
docker compose version
```

## GitHub Actions secrets

Add these repository secrets in GitHub under Settings > Secrets and variables > Actions:

- `GCP_VM_HOST`: VM external IP address
- `GCP_VM_USER`: VM SSH username
- `GCP_SSH_PRIVATE_KEY`: private key allowed to SSH into the VM
- `FLASK_SECRET_KEY`: long random Flask session secret
- `MYSQL_DATABASE`: use `appdb`
- `MYSQL_USER`: use `appuser`
- `MYSQL_PASSWORD`: strong app database password
- `MYSQL_ROOT_PASSWORD`: strong MySQL root password

Generate local secrets with a password manager or:

```bash
openssl rand -hex 32
```

## Deploy

Push to the `main` branch or run the `Deploy to GCP VM` workflow manually from GitHub Actions. The workflow copies the repo to `/opt/app_python_mysql`, writes `.env` on the VM from GitHub Secrets, rebuilds the app container, and runs:

```bash
docker compose up -d --build
```

After deployment, open:

```text
http://<VM_EXTERNAL_IP>/
```

## Local test with Docker Compose

Create a local `.env` from the example file:

```bash
cp .env.example .env
```

Edit the placeholder secrets, then run:

```bash
docker compose up --build
```

Open `http://localhost/`.

## Useful VM commands

```bash
cd /opt/app_python_mysql
docker compose ps
docker compose logs web
docker compose logs mysql
docker compose down
```

The MySQL data is stored in the named Docker volume `app_python_mysql_mysql_data`, so app rebuilds do not erase user data. The Compose file also starts MySQL with lower memory settings for the free-tier VM size.
