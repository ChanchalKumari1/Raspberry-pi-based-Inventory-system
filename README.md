# Inventory Manager – Flask + SQLite + LWR201 Scanner

A complete inventory management web application for IoT/electronics components, designed for use with the **LWR201 barcode scanner** on a Raspberry Pi (or any Linux system).  
Features include product management, barcode lookup, stock consumption, restock logging, and a clean dark‑theme UI.

https://drive.google.com/drive/folders/14fCVm6q0DsJF5zCD3UxgXJ081sIC9buH?usp=sharing
---

## Features

- **Dashboard** – real‑time stock summary, low‑stock alerts, recent scan activity.
- **Product Catalogue** – search, filter, add, edit, delete products with images.
- **Barcode Scanning** – use LWR201 (or any USB scanner) to lookup or consume stock instantly.
- **Restock** – add quantity, record supplier, PO number, and notes.
- **Activity Logs** – full history of scans and restock events.
- **Image Upload** – auto‑resize to 200×200 thumbnails.
- **Automatic Startup** – configured as a systemd service with browser auto‑launch on boot.

---

## Requirements

- **Hardware**: Raspberry Pi (or any Debian‑based system) with a monitor (for GUI) and optional barcode scanner.
- **Operating System**: Raspberry Pi OS **Bullseye** (or later).  
  *Note: Python 3.10+ is required for the code syntax (`str | None`).*
- **Packages**: Python 3.10, Flask, Pillow, and SQLite3 (built‑in).

---

## Installation

### 1. Install Python 3.10 (if not already present)

Raspberry Pi OS Bullseye ships with Python 3.9 by default. You need **Python 3.10 or higher**.

```bash
# Install build dependencies
sudo apt update
sudo apt install -y build-essential libssl-dev zlib1g-dev libncurses5-dev \
    libncursesw5-dev libreadline-dev libsqlite3-dev libgdbm-dev \
    libdb5.3-dev libbz2-dev libexpat1-dev liblzma-dev tk-dev libffi-dev

# Download and compile Python 3.10
cd /tmp
wget https://www.python.org/ftp/python/3.10.16/Python-3.10.16.tgz
tar -xzf Python-3.10.16.tgz
cd Python-3.10.16
./configure --enable-optimizations --prefix=/usr
make -j$(nproc)
sudo make altinstall

# Verify
python3.10 --version   # should show 3.10.x
```

### 2. Clone/Download the Project

Place your project folder somewhere, e.g. `/home/pi/Documents/flask_based`.  
The structure should be:

```
flask_based/
├── flask_based/
│   ├── app.py
│   ├── inventory.py
│   ├── inventory.db      (created on first run)
│   └── static/images/    (created automatically)
└── README.md
```

### 3. Install Python Dependencies

Using the newly installed Python 3.10:

```bash
python3.10 -m pip install flask Pillow
```

### 4. Initialise the Database

The database is auto‑created when you run the app for the first time. To seed it with demo products (including a sample LWR201 entry), run:

```bash
cd /home/pi/Documents/flask_based/flask_based
python3.10 inventory.py seed
```

### 5. Test Manually

Start the Flask server:

```bash
python3.10 app.py
```

Open your browser and go to `http://localhost:5000`. You should see the dashboard.

---

## Automatic Startup on Boot

The following steps configure the Flask app as a **systemd service** and launch the browser automatically when the Raspberry Pi desktop starts.

### A. Create the systemd Service

Create a service file:

```bash
sudo nano /etc/systemd/system/flaskapp.service
```

Paste the content below (adjust paths if needed):

```ini
[Unit]
Description=Flask Inventory App
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/Documents/flask_based
ExecStart=/usr/local/bin/python3.10 /home/pi/Documents/flask_based/flask_based/app.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment="PATH=/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
```

**Important**:  
- Replace `User=pi` with your actual username.  
- Verify the path to `python3.10` with `which python3.10` (usually `/usr/local/bin/python3.10`).  
- The `WorkingDirectory` should point to the parent folder containing `flask_based`.

### B. Enable and Start the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable flaskapp.service
sudo systemctl start flaskapp.service
sudo systemctl status flaskapp.service   
```

### C. Auto‑Launch Browser (GUI)

Create an autostart entry for the desktop session:

```bash
mkdir -p /home/pi/.config/autostart
nano /home/pi/.config/autostart/flask.desktop
```

Paste:

```ini
[Desktop Entry]
Type=Application
Name=Flask App
Exec=chromium-browser --start-fullscreen http://localhost:5000
```

> To avoid a “connection refused” if the browser opens too fast, you can add a small delay:  
> `Exec=sh -c "sleep 5 && chromium-browser --start-fullscreen http://localhost:5000"`

### D. Reboot and Test

```bash
sudo reboot
```

After the Pi restarts, the Flask server will run in the background, and Chromium will open in full‑screen mode with your inventory app.

---

## Access from Other Devices

Find your Pi’s IP address:

```bash
hostname -I
```

On any device on the same network, open a browser and go to `http://<pi-ip>:5000`.  
Make sure the Flask `app.run()` in `app.py` uses `host='0.0.0.0'` (it already does in the provided code).

---

## File Structure

```
flask_based/
├── flask_based/
│   ├── app.py            # Flask web application (UI & routes)
│   ├── inventory.py      # Core logic: database, images, CRUD, restock, scan
│   ├── inventory.db      # SQLite database (auto‑created)
│   └── static/images/    # Product thumbnails (auto‑created)
└── README.md
```

---

## Usage Overview

### Dashboard
- Shows total products, low/out‑of‑stock counts, and inventory value.
- Displays recent scans and low‑stock items with direct restock links.

### Products
- Full list with search and category filter.
- Each product row shows image, part number, barcode, model, description, category, price, stock level, location, and action buttons (Edit, Restock, Delete).

### Scan
- Designed for LWR201 scanner: scan a barcode, choose **Lookup** (just view) or **Consume** (reduce stock).
- Displays product details, stock badge, and logs each scan in a session history.

### Restock
- Search products by name, part number, or barcode.
- Select a product, enter quantity, supplier, PO number, and notes.
- Records a restock log and updates stock automatically.

### Logs
- Shows the last 50 scan events and restock transactions.

---

## Configuration

- **Database**: `inventory.db` – SQLite, stored in the same folder.
- **Image storage**: `static/images/` – thumbnails are resized to 200×200 pixels.
- **Low‑stock threshold**: defined per product (`min_stock` field).  
- **Barcode scanner**: Any USB HID scanner that sends characters followed by Enter will work. The app listens for Enter (`keyup`) on the barcode input field.

---

## Troubleshooting

### Service fails to start
Check the logs:

```bash
sudo journalctl -u flaskapp.service -f
```

Common issues:
- Wrong path to Python or script.
- Missing Python dependencies.
- Permission errors (ensure the `pi` user owns the folder).

### Browser says “connection refused”
- The Flask server may not have started yet. Use the delayed launch trick in the `.desktop` file.
- Verify that the service is running: `sudo systemctl status flaskapp.service`.

### Image upload not working
- Ensure the `static/images` directory exists and is writable.
- Check that Pillow is installed (`python3.10 -m pip install Pillow`).

### Barcode scanner not focusing
- The input fields automatically re‑focus after scanning. If you lose focus, click inside the barcode field or press Tab.

---



