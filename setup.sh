set -e

echo "=== OneDrop Setup ==="

echo "Installing package and development dependencies..."
pip install -e ".[dev]" --break-system-packages

if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
else
    echo ".env configuration already exists, so we are skipping."
fi

echo "Setting up locally-trusted certificates..."
PRIMARY_IP=$(python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 1)); print(s.getsockname()[0])" 2>/dev/null || echo "")

if [ -n "$PRIMARY_IP" ]; then
    echo "Detected primary IP: $PRIMARY_IP"
    HOSTS="localhost 127.0.0.1 $PRIMARY_IP"
else
    echo "Could not detect primary IP. Using localhost and 127.0.0.1."
    HOSTS="localhost 127.0.0.1"
fi

if command -v mkcert >/dev/null 2>&1; then
    echo "Running mkcert to generate certificates for: $HOSTS"
    mkcert -cert-file onedrop.pem -key-file onedrop-key.pem $HOSTS
    echo "Certificates generated successfully: onedrop.pem, onedrop-key.pem"
else
    echo "WARNING: mkcert is not installed. Please install mkcert to generate locally-trusted certificates."
    echo "         Alternatively, the server will auto-generate temporary self-signed certificates at runtime."
fi

echo "=== Setup completed successfully! ==="
