# Flask MySQL CI/CD App on GCP

This project is a Flask user-authentication web app deployed on Google Cloud Platform with a GitHub Actions CI/CD pipeline.

The application runs on a Google Compute Engine VM using Docker Compose. The VM hosts both the Flask web container and a MySQL container. Every push to the `main` branch triggers a GitHub Actions workflow that syncs the latest code to the VM, writes the production `.env` file from GitHub Secrets, rebuilds the Docker containers, restarts the app, and runs a health check.

## Live App

- Home: http://34.145.64.86
- Sign up: http://34.145.64.86/signup
- Sign in: http://34.145.64.86/signin
- Dashboard: available after signing in at `/dashboard`

## App Features

- Flask web app with server-rendered HTML templates
- User signup and signin flow
- Password hashing for new users
- Session-based authentication
- Protected dashboard page after signin
- MySQL database persistence
- Dockerized Flask and MySQL services
- Production deployment through GitHub Actions

## Architecture

```text
GitHub main branch
        |
        v
GitHub Actions workflow
        |
        v
SSH + rsync to GCP Compute Engine VM
        |
        v
Docker Compose rebuild/restart
        |
        v
Flask app + MySQL container
```

## CI/CD Workflow

The workflow is defined in `.github/workflows/deploy.yml`.

It runs on:

- Pushes to `main`
- Manual workflow dispatch from the GitHub Actions tab

Deployment steps:

1. Check out the repository.
2. Configure SSH using the GitHub Actions secret `GCP_SSH_PRIVATE_KEY_B64`.
3. Sync project files to `/opt/app_python_mysql` on the GCP VM with `rsync`.
4. Write the production `.env` file on the VM from GitHub Secrets.
5. Rebuild and restart containers with Docker Compose.
6. Run a health check against `http://localhost/` on the VM.

## GCP Infrastructure

The app is deployed to a Google Compute Engine VM.

Recommended low-cost setup:

- Ubuntu 22.04 LTS VM
- `e2-micro` machine type
- Standard persistent disk
- HTTP firewall rule enabled for port `80`
- Docker and Docker Compose installed on the VM
- App directory: `/opt/app_python_mysql`

Cloud SQL is not used. MySQL runs as a Docker container on the same VM to keep the setup simple and low cost.

## GitHub Actions Secrets

Add these secrets under GitHub repo Settings > Secrets and variables > Actions:

- `GCP_VM_HOST`: external IP address of the GCP VM, for example `34.145.64.86`
- `GCP_VM_USER`: SSH username for the VM
- `GCP_SSH_PRIVATE_KEY_B64`: base64-encoded private SSH key used by GitHub Actions
- `FLASK_SECRET_KEY`: long random Flask session secret
- `MYSQL_DATABASE`: database name, for example `appdb`
- `MYSQL_USER`: database user, for example `appuser`
- `MYSQL_PASSWORD`: strong MySQL app-user password
- `MYSQL_ROOT_PASSWORD`: strong MySQL root password

`GCP_SSH_PRIVATE_KEY_B64` is used instead of a raw multiline private key because it avoids newline and formatting issues when storing the key in GitHub Secrets.

## Creating the Base64 SSH Secret

Create a deployment SSH key on local machine:

```powershell
ssh-keygen -t ed25519 -C "github-actions-gcp" -f "$env:USERPROFILE\.ssh\app_python_mysql_gcp"
```

Add the public key to the VM:

```powershell
Get-Content "$env:USERPROFILE\.ssh\app_python_mysql_gcp.pub"
```

Copy that public key into the VM user's `~/.ssh/authorized_keys` file.

Generate the base64 private key value for GitHub Secrets:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("$env:USERPROFILE\.ssh\app_python_mysql_gcp"))
```

Paste that one-line output into the GitHub secret named `GCP_SSH_PRIVATE_KEY_B64`.

## One-Time VM Setup

SSH into the VM and install Docker, Docker Compose, and rsync:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg rsync
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
ARCH=$(dpkg --print-architecture)
CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
echo "deb [arch=$ARCH signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
sudo mkdir -p /opt/app_python_mysql
sudo chown "$USER:$USER" /opt/app_python_mysql
```

Add a small swap file for the free-tier VM size:

```bash
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Log out and back in, then verify Docker:

```bash
docker --version
docker compose version
```

## Deploying

Push to `main`:

```bash
git push origin main
```

Or run the workflow manually from GitHub Actions:

```text
Actions > Deploy to GCP VM > Run workflow
```

## Checking the Deployment

From a browser:

```text
http://34.145.64.86
http://34.145.64.86/signup
http://34.145.64.86/signin
```

## Local Development

Create a local `.env` from the example file:

```bash
cp .env.example .env
```

Edit the placeholder values, then run:

```bash
docker compose up --build
```

Open:

```text
http://localhost/
```

## Data Persistence

MySQL data is stored in the named Docker volume `app_python_mysql_mysql_data`, so app rebuilds and container restarts do not erase user data.
