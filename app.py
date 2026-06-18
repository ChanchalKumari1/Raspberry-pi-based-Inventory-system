#!/usr/bin/env python3
"""
Inventory Web UI  —  Flask + SQLite + LWR201 barcode scanner support
Run:  python app.py
Open: http://localhost:5000
"""

from flask import Flask, render_template_string, request, redirect, url_for, jsonify, flash
import os, sys, tempfile

# pull in the inventory logic from same folder
sys.path.insert(0, os.path.dirname(__file__))
from inventory import (
    init_db, get_conn, save_image,
    add_product, update_product, delete_product,
    lookup_barcode, consume_stock, restock,
    restock_history, scan_history, IMAGE_DIR
)

app = Flask(__name__, static_folder="static")
app.secret_key = "inv-secret-2026"

# ─────────────────────────────── HTML template ───────────────────────────────
HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Inventory Manager · LWR201</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0f1117; --surface:#181c27; --card:#1e2336;
  --border:#2a3050; --accent:#4f8ef7; --accent2:#3dd68c;
  --warn:#f0a030; --danger:#e05555;
  --text:#e8eaf0; --muted:#7a84a0; --mono:'JetBrains Mono',monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh}
a{color:var(--accent);text-decoration:none}
/* ── Nav ── */
nav{background:var(--surface);border-bottom:1px solid var(--border);
    display:flex;align-items:center;justify-content:space-between;
    padding:.75rem 1.5rem;position:sticky;top:0;z-index:100}
.nav-brand{font-weight:700;font-size:1rem;letter-spacing:.02em;color:#fff}
.nav-brand span{color:var(--accent)}
.nav-links{display:flex;gap:.25rem}
.nav-links a{padding:.4rem .75rem;border-radius:6px;font-size:.85rem;
             color:var(--muted);transition:all .15s}
.nav-links a:hover,.nav-links a.active{background:var(--card);color:var(--text)}
/* ── Layout ── */
.wrap{max-width:1280px;margin:0 auto;padding:1.5rem}
.page-title{font-size:1.4rem;font-weight:700;margin-bottom:1.5rem;
            display:flex;align-items:center;gap:.6rem}
/* ── Cards / Grid ── */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1rem;margin-bottom:2rem}
.stat{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.2rem}
.stat-val{font-size:2rem;font-weight:700;line-height:1}
.stat-lbl{font-size:.78rem;color:var(--muted);margin-top:.3rem;text-transform:uppercase;letter-spacing:.04em}
/* ── Table ── */
.tbl-wrap{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin-bottom:2rem}
table{width:100%;border-collapse:collapse;font-size:.875rem}
th{background:var(--surface);padding:.7rem 1rem;text-align:left;
   font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);
   border-bottom:1px solid var(--border)}
td{padding:.65rem 1rem;border-bottom:1px solid var(--border)}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(79,142,247,.04)}
.badge{display:inline-block;padding:.18rem .55rem;border-radius:20px;font-size:.72rem;font-weight:600}
.badge-ok{background:#1d3a2a;color:#3dd68c}
.badge-low{background:#3a2a10;color:#f0a030}
.badge-out{background:#3a1515;color:#e05555}
.prod-img{width:44px;height:44px;object-fit:cover;border-radius:6px;border:1px solid var(--border)}
.img-placeholder{width:44px;height:44px;border-radius:6px;background:var(--surface);
                 border:1px solid var(--border);display:flex;align-items:center;
                 justify-content:center;font-size:1.2rem}
/* ── Forms ── */
.form-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.5rem;max-width:660px}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.form-row{display:flex;flex-direction:column;gap:.4rem}
.form-row.full{grid-column:1/-1}
label{font-size:.8rem;color:var(--muted);font-weight:500}
input,textarea,select{background:var(--surface);border:1px solid var(--border);
  color:var(--text);padding:.55rem .8rem;border-radius:8px;font-size:.9rem;
  font-family:inherit;width:100%;outline:none;transition:border .15s}
input:focus,textarea:focus,select:focus{border-color:var(--accent)}
textarea{resize:vertical;min-height:70px}
.btn{display:inline-flex;align-items:center;gap:.4rem;padding:.5rem 1.1rem;
     border-radius:8px;font-size:.875rem;font-weight:600;cursor:pointer;border:none;
     transition:all .15s;text-decoration:none}
.btn-primary{background:var(--accent);color:#fff}
.btn-primary:hover{background:#6fa3ff;color:#fff}
.btn-success{background:#1a3d2a;border:1px solid var(--accent2);color:var(--accent2)}
.btn-danger{background:#3a1515;border:1px solid var(--danger);color:var(--danger)}
.btn-ghost{background:transparent;border:1px solid var(--border);color:var(--muted)}
.btn-ghost:hover{border-color:var(--accent);color:var(--text)}
.btn-sm{padding:.3rem .7rem;font-size:.78rem}
/* ── Scanner input ── */
.scan-box{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.2rem 1.5rem;
          margin-bottom:2rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap}
.scan-box input{max-width:320px;font-family:var(--mono);font-size:1rem;letter-spacing:.06em}
/* ── Flash msgs ── */
.flash{padding:.65rem 1.1rem;border-radius:8px;margin-bottom:1rem;font-size:.875rem}
.flash-ok{background:#1a3d2a;border:1px solid var(--accent2);color:var(--accent2)}
.flash-err{background:#3a1515;border:1px solid var(--danger);color:var(--danger)}
/* ── Scan result card ── */
.result-card{background:var(--card);border:1px solid var(--accent);border-radius:12px;
             padding:1.2rem 1.5rem;margin-bottom:1.5rem;display:flex;gap:1.2rem;align-items:flex-start}
.result-card img{width:80px;height:80px;object-fit:cover;border-radius:8px;flex-shrink:0}
.mono{font-family:var(--mono);font-size:.85rem}
/* ── Image upload preview ── */
#img-preview{width:100px;height:100px;object-fit:cover;border-radius:8px;
             display:none;border:1px solid var(--border);margin-top:.5rem}
/* ── Pagination-like row count ── */
.tbl-footer{padding:.6rem 1rem;border-top:1px solid var(--border);
            font-size:.78rem;color:var(--muted);background:var(--surface)}
</style>
</head>
<body>
<nav>
  <div class="nav-brand">📦 <span>Inv</span>entor<span>y</span></div>
  <div class="nav-links">
    <a href="/" {% if page=='dash' %}class="active"{% endif %}>Dashboard</a>
    <a href="/products" {% if page=='products' %}class="active"{% endif %}>Products</a>
    <a href="/scan" {% if page=='scan' %}class="active"{% endif %}>🔍 Scan</a>
    <a href="/restock" {% if page=='restock' %}class="active"{% endif %}>📥 Restock</a>
    <a href="/add" {% if page=='add' %}class="active"{% endif %}>＋ Add</a>
    <a href="/logs" {% if page=='logs' %}class="active"{% endif %}>Logs</a>
  </div>
</nav>

<div class="wrap">
{% with msgs = get_flashed_messages(with_categories=True) %}
  {% for cat,msg in msgs %}
  <div class="flash flash-{{ 'ok' if cat=='success' else 'err' }}">{{ msg }}</div>
  {% endfor %}
{% endwith %}

{{ body|safe }}
</div>

<script>
// Auto-focus barcode input on scan page
document.addEventListener('DOMContentLoaded',()=>{
  const bc = document.getElementById('barcode-input');
  if(bc) bc.focus();
});
</script>
</body>
</html>
"""

# ─── helpers ─────────────────────────────────────────────────────────────────
def stock_badge(qty, min_qty):
    if qty == 0:   return f'<span class="badge badge-out">Out ({qty})</span>'
    if qty <= min_qty: return f'<span class="badge badge-low">Low ({qty})</span>'
    return f'<span class="badge badge-ok">{qty}</span>'

def img_tag(path, alt="", size=44):
    if path and os.path.exists(path):
        return f'<img src="/{path}" alt="{alt}" class="prod-img" width="{size}" height="{size}">'
    return '<div class="img-placeholder">📷</div>'

# ─── Dashboard ────────────────────────────────────────────────────────────────
@app.route("/")
def dashboard():
    conn = get_conn()
    total   = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    low     = conn.execute("SELECT COUNT(*) FROM products WHERE in_stock<=min_stock AND in_stock>0").fetchone()[0]
    out     = conn.execute("SELECT COUNT(*) FROM products WHERE in_stock=0").fetchone()[0]
    val     = conn.execute("SELECT ROUND(SUM(in_stock*unit_price),2) FROM products").fetchone()[0] or 0
    recent  = conn.execute("SELECT p.*,s.action,s.scanned_at FROM scan_log s LEFT JOIN products p ON s.barcode=p.barcode ORDER BY s.scanned_at DESC LIMIT 8").fetchall()
    lowrows = conn.execute("SELECT * FROM products WHERE in_stock<=min_stock ORDER BY in_stock ASC LIMIT 8").fetchall()
    conn.close()

    rows_html = "".join(f"""
    <tr>
      <td>{img_tag(r['image_path'],r['part_number'] or '')}</td>
      <td class="mono">{r['barcode'] or '—'}</td>
      <td>{r['model_name'] or '<span style="color:var(--muted)">Unknown</span>'}</td>
      <td><span class="badge {'badge-ok' if r['action']=='LOOKUP' else 'badge-low' if r['action']=='CONSUME' else 'badge-out'}">{r['action']}</span></td>
      <td style="color:var(--muted);font-size:.8rem">{r['scanned_at']}</td>
    </tr>""" for r in recent)

    low_html = "".join(f"""
    <tr>
      <td>{img_tag(r['image_path'],r['part_number'])}</td>
      <td class="mono">{r['part_number']}</td>
      <td>{r['model_name']}</td>
      <td>{stock_badge(r['in_stock'],r['min_stock'])}</td>
      <td style="color:var(--muted)">{r['min_stock']}</td>
      <td><a href="/restock?pn={r['part_number']}" class="btn btn-success btn-sm">Restock</a></td>
    </tr>""" for r in lowrows)

    body = f"""
    <div class="page-title">📊 Dashboard</div>
    <div class="stats">
      <div class="stat"><div class="stat-val">{total}</div><div class="stat-lbl">Total SKUs</div></div>
      <div class="stat"><div class="stat-val" style="color:var(--warn)">{low}</div><div class="stat-lbl">Low Stock</div></div>
      <div class="stat"><div class="stat-val" style="color:var(--danger)">{out}</div><div class="stat-lbl">Out of Stock</div></div>
      <div class="stat"><div class="stat-val" style="color:var(--accent2)">₹{val:,.2f}</div><div class="stat-lbl">Inventory Value</div></div>
    </div>

    <div class="page-title" style="font-size:1rem">⚠️ Low / Out-of-Stock</div>
    <div class="tbl-wrap">
      <table><thead><tr><th></th><th>Part No.</th><th>Model</th><th>In Stock</th><th>Min</th><th></th></tr></thead>
      <tbody>{low_html or '<tr><td colspan=6 style="text-align:center;color:var(--muted);padding:1.5rem">All items well stocked ✅</td></tr>'}</tbody></table>
    </div>

    <div class="page-title" style="font-size:1rem">🔍 Recent Scans</div>
    <div class="tbl-wrap">
      <table><thead><tr><th></th><th>Barcode</th><th>Product</th><th>Action</th><th>Time</th></tr></thead>
      <tbody>{rows_html or '<tr><td colspan=5 style="text-align:center;color:var(--muted);padding:1.5rem">No scans yet</td></tr>'}</tbody></table>
    </div>
    """
    return render_template_string(HTML, body=body, page='dash')


# ─── Products list ────────────────────────────────────────────────────────────
@app.route("/products")
def products():
    q   = request.args.get("q","").strip()
    cat = request.args.get("cat","").strip()
    conn = get_conn()
    cats = [r[0] for r in conn.execute("SELECT DISTINCT category FROM products ORDER BY category").fetchall()]
    sql  = "SELECT * FROM products WHERE 1=1"
    params = []
    if q:
        sql += " AND (model_name LIKE ? OR part_number LIKE ? OR barcode LIKE ? OR description LIKE ?)"
        params += [f"%{q}%"]*4
    if cat:
        sql += " AND category=?"
        params.append(cat)
    sql += " ORDER BY part_number"
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    cat_opts = "".join(f'<option value="{c}" {"selected" if c==cat else ""}>{c}</option>' for c in cats)
    rows_html = "".join(f"""
    <tr>
      <td>{img_tag(r['image_path'],r['part_number'])}</td>
      <td class="mono" style="white-space:nowrap">{r['part_number']}</td>
      <td class="mono" style="font-size:.8rem;color:var(--muted)">{r['barcode']}</td>
      <td>{r['model_name']}</td>
      <td style="color:var(--muted);font-size:.82rem;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{r['description'] or ''}</td>
      <td><span class="badge" style="background:var(--surface);color:var(--muted)">{r['category']}</span></td>
      <td>₹{r['unit_price']:.2f}</td>
      <td>{stock_badge(r['in_stock'],r['min_stock'])}</td>
      <td style="color:var(--muted);font-size:.82rem">{r['location'] or ''}</td>
      <td style="white-space:nowrap">
        <a href="/edit/{r['part_number']}" class="btn btn-ghost btn-sm">Edit</a>
        <a href="/restock?pn={r['part_number']}" class="btn btn-success btn-sm">+Stock</a>
        <a href="/delete/{r['part_number']}" class="btn btn-danger btn-sm"
           onclick="return confirm('Delete {r['part_number']}?')">Del</a>
      </td>
    </tr>""" for r in rows)

    body = f"""
    <div class="page-title">📦 Products
      <a href="/add" class="btn btn-primary btn-sm" style="margin-left:auto">＋ Add Product</a>
    </div>
    <div style="display:flex;gap:.75rem;margin-bottom:1.5rem;flex-wrap:wrap">
      <form method="get" style="display:flex;gap:.75rem;flex-wrap:wrap">
        <input name="q" value="{q}" placeholder="Search name / part / barcode…" style="max-width:280px">
        <select name="cat" style="max-width:160px"><option value="">All Categories</option>{cat_opts}</select>
        <button type="submit" class="btn btn-ghost">Filter</button>
        {'<a href="/products" class="btn btn-ghost">Clear</a>' if q or cat else ''}
      </form>
    </div>
    <div class="tbl-wrap">
      <table><thead><tr>
        <th></th><th>Part No.</th><th>Barcode</th><th>Model Name</th><th>Description</th>
        <th>Category</th><th>Price</th><th>In Stock</th><th>Location</th><th>Actions</th>
      </tr></thead>
      <tbody>{rows_html or '<tr><td colspan=10 style="text-align:center;color:var(--muted);padding:2rem">No products found</td></tr>'}</tbody></table>
      <div class="tbl-footer">{len(rows)} product(s)</div>
    </div>"""
    return render_template_string(HTML, body=body, page='products')



# ─── IoT Electronics category list ───────────────────────────────────────────
IOT_CATEGORIES = [
    ("Microcontrollers & SBCs", [
        "MCU – ESP32 / ESP8266", "MCU – Arduino / AVR", "MCU – STM32 / ARM",
        "MCU – RP2040 / Raspberry Pi Pico", "SBC – Raspberry Pi", "SBC – Other",
    ]),
    ("Wireless & Connectivity", [
        "WiFi Modules", "Bluetooth / BLE Modules", "NFC / RFID Modules",
        "LoRa / LoRaWAN Modules", "Zigbee / Z-Wave Modules",
        "GSM / LTE / 4G Modules", "GPS / GNSS Modules",
        "RF Transceivers", "Ethernet Modules",
    ]),
    ("Sensors", [
        "Sensors – Temperature / Humidity", "Sensors – Pressure / Altitude",
        "Sensors – Gas / Air Quality", "Sensors – Motion / PIR",
        "Sensors – Ultrasonic / Distance", "Sensors – Light / UV / IR",
        "Sensors – Current / Voltage", "Sensors – Accelerometer / Gyro / IMU",
        "Sensors – Magnetic / Hall Effect", "Sensors – Touch / Capacitive",
        "Sensors – Sound / Microphone", "Sensors – Flow / Level",
        "Sensors – Colour", "Sensors – Optical Reflective",
    ]),
    ("Display & UI", [
        "OLED Displays", "LCD Displays", "TFT / Colour Displays",
        "E-Paper / E-Ink Displays", "LED Matrices / WS2812",
        "7-Segment Displays", "Keypads / Buttons",
        "Rotary Encoders", "Touchscreens",
    ]),
    ("Power", [
        "Voltage Regulators – LDO", "Voltage Regulators – Switching / SMPS",
        "USB Power – PD / PPS Sink", "Battery Management ICs",
        "Li-Ion / LiPo Batteries", "Solar / Energy Harvesting",
        "DC-DC Converters", "Power Modules",
    ]),
    ("ICs & Semiconductors", [
        "Logic ICs", "Op-Amps / Comparators", "ADC / DAC ICs",
        "Level Shifters", "I/O Expanders", "Gate Drivers",
        "Motor Driver ICs", "Opto-Isolators", "Crystal Oscillators",
        "Memory – EEPROM / Flash", "Memory – SRAM",
    ]),
    ("Communication ICs", [
        "UART / RS232 / RS485 ICs", "SPI / I2C Bridge ICs",
        "CAN Bus ICs", "USB ICs", "Ethernet ICs",
    ]),
    ("Audio", [
        "Audio Amplifier ICs", "I2S DAC / Codec",
        "Speakers / Buzzers", "Microphone Modules",
    ]),
    ("Actuators & Output", [
        "Relays", "MOSFETs / Transistors", "Servo Motors",
        "Stepper Motors", "DC Motors", "Solenoids", "Vibration Motors",
    ]),
    ("Passive Components", [
        "Resistors", "Capacitors", "Inductors", "Diodes / Zeners",
        "TVS / ESD Protection", "Fuses / PTC Resetters",
        "Crystals / Resonators", "Ferrite Beads",
    ]),
    ("PCB & Prototyping", [
        "Breakout Boards", "Bare PCBs", "Breadboards",
        "Perfboards / Stripboards", "Dev / Eval Boards",
        "Jumper Wires / Cables", "Pin Headers / Connectors", "SMD Stencils",
    ]),
    ("Enclosures & Mechanical", [
        "Plastic Enclosures", "Metal Enclosures", "DIN Rail Enclosures",
        "Heat Sinks", "Standoffs / Spacers", "Screws / Nuts / Bolts",
        "Mounts / Brackets",
    ]),
    ("Tools & Consumables", [
        "Solder Wire", "Flux", "Thermal Paste", "PCB Cleaner",
        "Heat Shrink Tubing", "Kapton / Insulating Tape", "Conformal Coating",
    ]),
    ("Test & Measurement", [
        "Multimeters", "Oscilloscopes", "Logic Analysers",
        "Power Supplies", "Barcode Scanners", "Soldering Equipment",
    ]),
    ("Cables & Adapters", [
        "USB Cables", "HDMI / Display Cables", "Ribbon Cables / FFC",
        "Power Cables", "RF Cables / Antennas", "GPIO Adapters",
    ]),
]


def build_cat_options(current_val=""):
    all_known = {c for _, grp in IOT_CATEGORIES for c in grp}
    lines = ['<option value="">— Select category —</option>']
    matched = current_val in all_known
    # If existing value is custom (not in list) add it first as selected
    if current_val and not matched:
        lines.append(f'<option value="{current_val}" selected>{current_val} (current)</option>')
    for group_name, cats in IOT_CATEGORIES:
        lines.append(f'<optgroup label="{group_name}">')
        for c in cats:
            sel = 'selected' if c == current_val else ''
            lines.append(f'  <option value="{c}" {sel}>{c}</option>')
        lines.append('</optgroup>')
    lines.append('<option value="__custom__">✏️ Custom category…</option>')
    return "\n".join(lines)



def resolve_category(form):
    """Return final category value, handling custom input."""
    cat = form.get("category", "").strip()
    if cat == "__custom__":
        cat = form.get("category_custom", "").strip() or "General"
    return cat or "General"

# ─── Add / Edit ───────────────────────────────────────────────────────────────
def product_form(pn=None):
    row = None
    if pn:
        conn = get_conn()
        row  = conn.execute("SELECT * FROM products WHERE part_number=?", (pn,)).fetchone()
        conn.close()
        if not row: return "Not found", 404
    v = lambda f,d="": row[f] if row and row[f] is not None else d
    img_preview = f'<img id="img-preview" src="/{v("image_path")}" style="display:block">' if v("image_path") else '<img id="img-preview">'
    cat_options = build_cat_options(v("category", ""))

    body = f"""
    <div class="page-title">{'✏️ Edit' if pn else '＋ Add'} Product</div>
    <div class="form-card">
      <form method="post" enctype="multipart/form-data">
        <div class="form-grid">
          <div class="form-row">
            <label>Barcode *</label>
            <input name="barcode" value="{v('barcode')}" placeholder="Scan or type…" required>
          </div>
          <div class="form-row">
            <label>Part Number *</label>
            <input name="part_number" value="{v('part_number')}" placeholder="e.g. ESP32-S3" required {'readonly' if pn else ''}>
          </div>
          <div class="form-row full">
            <label>Model Name *</label>
            <input name="model_name" value="{v('model_name')}" placeholder="e.g. LWR201 Barcode Scanner" required>
          </div>
          <div class="form-row full">
            <label>Description</label>
            <textarea name="description">{v('description')}</textarea>
          </div>
          <div class="form-row full">
            <label>Category</label>
            <div style="display:flex;flex-direction:column;gap:.5rem">
              <select name="category" id="cat-select"
                onchange="const ci=document.getElementById('cat-custom');if(this.value==='__custom__'){{ci.style.display='block';ci.focus();ci.required=true}}else{{ci.style.display='none';ci.required=false}}"
                style="background:var(--surface);border:1px solid var(--border);color:var(--text);
                       padding:.55rem .8rem;border-radius:8px;font-size:.875rem;font-family:inherit;
                       max-width:420px">
                {cat_options}
              </select>
              <input id="cat-custom" name="category_custom"
                     placeholder="Type your custom category name…"
                     style="display:none;background:var(--surface);border:1px solid var(--accent);
                            color:var(--text);padding:.55rem .8rem;border-radius:8px;
                            font-size:.875rem;font-family:inherit;max-width:420px">
              <div style="font-size:.75rem;color:var(--muted)">
                Categories are grouped by IoT / electronics type. Pick ✏️ Custom to add your own.
              </div>
            </div>
          </div>
          <div class="form-row">
            <label>Location</label>
            <input name="location" value="{v('location')}" placeholder="Shelf-A1 / Bin-B2…">
          </div>
          <div class="form-row">
            <label>Unit Price (₹)</label>
            <input name="unit_price" type="number" step="0.01" value="{v('unit_price',0)}">
          </div>
          <div class="form-row">
            <label>In Stock</label>
            <input name="in_stock" type="number" value="{v('in_stock',0)}">
          </div>
          <div class="form-row">
            <label>Min Stock (alert threshold)</label>
            <input name="min_stock" type="number" value="{v('min_stock',5)}">
          </div>
          <div class="form-row">
            <label>Product Image (auto-resized to 200×200)</label>
            <input type="file" name="image" accept="image/*"
              onchange="const r=new FileReader();r.onload=e=>{{const i=document.getElementById('img-preview');i.src=e.target.result;i.style.display='block'}};r.readAsDataURL(this.files[0])">
            {img_preview}
          </div>
        </div>
        <div style="margin-top:1.25rem;display:flex;gap:.75rem">
          <button type="submit" class="btn btn-primary">{'Update' if pn else 'Add Product'}</button>
          <a href="/products" class="btn btn-ghost">Cancel</a>
        </div>
      </form>
    </div>"""
    return body


@app.route("/add", methods=["GET","POST"])
def add():
    if request.method == "POST":
        f = request.form
        img_path = None
        if "image" in request.files and request.files["image"].filename:
            file = request.files["image"]
            suffix = os.path.splitext(file.filename)[1] or ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as t:
                tmp = t.name
            file.save(tmp)
            img_path = save_image(tmp, f.get("part_number","tmp"))
            try: os.remove(tmp)
            except OSError: pass
        add_product(
            f["barcode"], f["part_number"], f["model_name"],
            f.get("description",""), resolve_category(f),
            float(f.get("unit_price",0)), int(f.get("in_stock",0)),
            int(f.get("min_stock",5)), f.get("location",""), None
        )
        if img_path:
            update_product(f["part_number"], image_path=img_path)
        flash(f"Product {f['part_number']} added!", "success")
        return redirect(url_for("products"))
    body = product_form()
    return render_template_string(HTML, body=body, page='add')


@app.route("/edit/<pn>", methods=["GET","POST"])
def edit(pn):
    if request.method == "POST":
        f = request.form
        kwargs = dict(
            barcode=f["barcode"], model_name=f["model_name"],
            description=f.get("description",""), category=resolve_category(f),
            unit_price=float(f.get("unit_price",0)), in_stock=int(f.get("in_stock",0)),
            min_stock=int(f.get("min_stock",5)), location=f.get("location","")
        )
        if "image" in request.files and request.files["image"].filename:
            file = request.files["image"]
            suffix = os.path.splitext(file.filename)[1] or ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as t:
                tmp = t.name
            file.save(tmp)
            kwargs["image_src"] = tmp
        update_product(pn, **kwargs)
        flash(f"Updated {pn}", "success")
        return redirect(url_for("products"))
    body = product_form(pn)
    if isinstance(body, tuple): return body
    return render_template_string(HTML, body=body, page='products')


@app.route("/delete/<pn>")
def delete(pn):
    delete_product(pn)
    flash(f"Deleted {pn}", "success")
    return redirect(url_for("products"))


# ─── Scan JSON API ────────────────────────────────────────────────────────────
@app.route("/api/do_scan", methods=["POST"])
def api_do_scan():
    data   = request.get_json(force=True)
    bc     = (data.get("barcode") or "").strip()
    action = data.get("action", "lookup")
    qty    = int(data.get("qty", 1))
    if not bc:
        return jsonify({"found": False, "error": "Empty barcode"})
    row = lookup_barcode(bc)
    if not row:
        return jsonify({"found": False, "barcode": bc})
    if action == "consume":
        consume_stock(bc, qty)
        conn = get_conn()
        row  = conn.execute("SELECT * FROM products WHERE barcode=?", (bc,)).fetchone()
        conn.close()
    img_path = row["image_path"] or ""
    img_url  = ("/" + img_path.replace("\\", "/")) if img_path and os.path.exists(img_path) else ""
    return jsonify({
        "found":       True,
        "barcode":     row["barcode"],
        "part_number": row["part_number"],
        "model_name":  row["model_name"],
        "description": row["description"] or "",
        "category":    row["category"] or "",
        "in_stock":    row["in_stock"],
        "min_stock":   row["min_stock"],
        "unit_price":  row["unit_price"],
        "location":    row["location"] or "",
        "image_url":   img_url,
        "action":      action,
        "qty":         qty,
    })


# ─── Scan page ────────────────────────────────────────────────────────────────
@app.route("/scan", methods=["GET"])
def scan():
    body = """
    <div class="page-title">
      \U0001f50d Barcode Scanner
      <span style="font-size:.8rem;color:var(--muted);font-weight:400;margin-left:.5rem">
        LWR201 ready &mdash; just scan!
      </span>
    </div>

    <div style="display:flex;gap:1rem;align-items:flex-end;flex-wrap:wrap;margin-bottom:1.5rem">
      <div style="display:flex;flex-direction:column;gap:.4rem;flex:1;min-width:220px;max-width:360px">
        <label style="font-size:.8rem;color:var(--muted);font-weight:500">Barcode</label>
        <input id="barcode-input" placeholder="Scan or type barcode&hellip;"
               autocomplete="off" spellcheck="false"
               style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;
                      letter-spacing:.06em;padding:.65rem 1rem;
                      background:var(--surface);border:2px solid var(--accent);
                      color:var(--text);border-radius:8px;width:100%;outline:none">
      </div>
      <div style="display:flex;flex-direction:column;gap:.4rem">
        <label style="font-size:.8rem;color:var(--muted);font-weight:500">Action</label>
        <select id="action-select" style="padding:.65rem .8rem;background:var(--surface);
                border:1px solid var(--border);color:var(--text);border-radius:8px;font-size:.9rem">
          <option value="lookup">Lookup only</option>
          <option value="consume">Consume (dispatch)</option>
        </select>
      </div>
      <div style="display:flex;flex-direction:column;gap:.4rem;width:90px">
        <label style="font-size:.8rem;color:var(--muted);font-weight:500">Qty</label>
        <input id="qty-input" type="number" value="1" min="1"
               style="padding:.65rem .8rem;background:var(--surface);
                      border:1px solid var(--border);color:var(--text);border-radius:8px;font-size:.9rem">
      </div>
      <button onclick="doScan()" class="btn btn-primary" style="padding:.65rem 1.4rem">Submit</button>
    </div>

    <div id="scan-result"></div>

    <div style="font-weight:600;font-size:.95rem;margin-bottom:.75rem;margin-top:2rem">
      Recent scans this session
    </div>
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th>#</th><th>Barcode</th><th>Part No.</th><th>Model</th>
          <th>Action</th><th>Stock</th><th>Location</th><th>Time</th>
        </tr></thead>
        <tbody id="scan-history-body">
          <tr id="placeholder-row"><td colspan="8"
            style="text-align:center;color:var(--muted);padding:1.5rem">
            No scans yet &mdash; waiting for scanner&hellip;
          </td></tr>
        </tbody>
      </table>
    </div>

    <script>
    const inp    = document.getElementById('barcode-input');
    const actSel = document.getElementById('action-select');
    const qtyInp = document.getElementById('qty-input');
    const result = document.getElementById('scan-result');
    const tbody  = document.getElementById('scan-history-body');
    let   scanCount = 0;

    function refocus() { inp.focus(); }

    // Keep input focused at all times except when editing action/qty
    document.addEventListener('click', e => {
      if (e.target !== actSel && e.target !== qtyInp) refocus();
    });
    refocus();

    // LWR201 sends barcode text then Enter key
    inp.addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); doScan(); }
    });

    async function doScan() {
      const bc  = inp.value.trim();
      const act = actSel.value;
      const qty = parseInt(qtyInp.value) || 1;
      if (!bc) {
        result.innerHTML = '<div class="flash flash-err">\u26a0\ufe0f Nothing scanned &mdash; point scanner at barcode and scan.</div>';
        return;
      }
      inp.value = '';  // clear immediately so next scan can come in
      refocus();

      try {
        const resp = await fetch('/api/do_scan', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({barcode: bc, action: act, qty: qty})
        });
        const d = await resp.json();

        if (!d.found) {
          result.innerHTML = `<div class="flash flash-err">\u274c Barcode not found: <span style="font-family:monospace">${bc}</span></div>`;
          addRow(bc, '\u2014', '\u2014', act, '\u2014', '\u2014', false);
          return;
        }

        const sb = d.in_stock === 0
          ? `<span class="badge badge-out">Out (0)</span>`
          : d.in_stock <= d.min_stock
            ? `<span class="badge badge-low">Low (${d.in_stock})</span>`
            : `<span class="badge badge-ok">${d.in_stock}</span>`;

        const imgHtml = d.image_url
          ? `<img src="${d.image_url}" style="width:80px;height:80px;object-fit:cover;border-radius:8px;flex-shrink:0">`
          : `<div style="width:80px;height:80px;border-radius:8px;background:var(--surface);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:2rem;flex-shrink:0">\U0001f4f7</div>`;

        const actLabel = act === 'consume'
          ? `<span class="badge badge-low">CONSUMED \u2212${qty}</span>`
          : `<span class="badge badge-ok">LOOKUP</span>`;

        result.innerHTML = `
          <div class="result-card">
            ${imgHtml}
            <div style="flex:1">
              <div style="font-weight:700;font-size:1.15rem">${d.model_name}</div>
              <div style="font-family:monospace;color:var(--muted);margin:.25rem 0;font-size:.82rem">
                ${d.part_number} &nbsp;|&nbsp; ${d.barcode}
              </div>
              <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-top:.5rem;align-items:center">
                ${sb} &nbsp;in stock
                <span style="color:var(--muted)">Min: ${d.min_stock}</span>
                <span style="color:var(--muted)">\u20b9${d.unit_price.toFixed(2)}</span>
                <span style="color:var(--muted)">${d.location}</span>
                <span style="color:var(--muted)">${d.category}</span>
                ${actLabel}
              </div>
              ${d.description ? `<div style="margin-top:.4rem;font-size:.82rem;color:var(--muted)">${d.description}</div>` : ''}
              ${d.in_stock === 0 ? '<div style="margin-top:.5rem;color:var(--danger);font-weight:600">\u26a0\ufe0f OUT OF STOCK</div>' : ''}
              ${d.in_stock > 0 && d.in_stock <= d.min_stock ? '<div style="margin-top:.5rem;color:var(--warn);font-weight:600">\u26a0\ufe0f LOW STOCK</div>' : ''}
            </div>
          </div>`;

        addRow(d.barcode, d.part_number, d.model_name, act, d.in_stock, d.location, true);

      } catch(err) {
        result.innerHTML = `<div class="flash flash-err">\U0001f534 Server error: ${err.message}</div>`;
      }
    }

    function addRow(barcode, pn, model, action, stock, loc, found) {
      scanCount++;
      const ph = document.getElementById('placeholder-row');
      if (ph) ph.remove();
      const badge = !found
        ? '<span class="badge badge-out">NOT FOUND</span>'
        : action === 'consume'
          ? '<span class="badge badge-low">CONSUME</span>'
          : '<span class="badge badge-ok">LOOKUP</span>';
      const stockCell = !found ? '\u2014'
        : stock === 0 ? '<span class="badge badge-out">0</span>'
        : String(stock);
      const now = new Date().toLocaleTimeString();
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="color:var(--muted);font-size:.8rem">${scanCount}</td>
        <td style="font-family:monospace;font-size:.82rem">${barcode}</td>
        <td style="font-family:monospace;font-size:.82rem">${pn}</td>
        <td style="font-size:.85rem">${model}</td>
        <td>${badge}</td>
        <td>${stockCell}</td>
        <td style="color:var(--muted);font-size:.82rem">${loc}</td>
        <td style="color:var(--muted);font-size:.78rem">${now}</td>`;
      tbody.insertBefore(tr, tbody.firstChild);
    }
    </script>
    """
    return render_template_string(HTML, body=body, page='scan')



# ─── Restock ──────────────────────────────────────────────────────────────────
# ─── Restock search API ──────────────────────────────────────────────────────
@app.route("/api/restock_search")
def api_restock_search():
    q  = request.args.get("q","").strip()
    bc = request.args.get("barcode","").strip()
    conn = get_conn()
    base_sql = """
        SELECT p.id,p.part_number,p.model_name,p.description,p.in_stock,p.min_stock,
               p.category,p.location,p.barcode,p.image_path,p.unit_price,
               r.supplier as last_supplier, r.po_number as last_po, r.qty_added as last_qty
        FROM products p
        LEFT JOIN (
            SELECT product_id, supplier, po_number, qty_added
            FROM restock_log
            WHERE id IN (SELECT MAX(id) FROM restock_log GROUP BY product_id)
        ) r ON r.product_id = p.id
    """
    if bc:
        rows = conn.execute(base_sql + " WHERE p.barcode=? LIMIT 1", (bc,)).fetchall()
    elif q:
        rows = conn.execute(base_sql + """
            WHERE p.part_number LIKE ? OR p.model_name LIKE ?
               OR p.barcode LIKE ? OR p.category LIKE ? OR p.description LIKE ?
            ORDER BY p.in_stock ASC LIMIT 20""",
            (f"%{q}%",)*5).fetchall()
    else:
        rows = conn.execute(base_sql + " ORDER BY p.in_stock ASC LIMIT 30").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/do_restock", methods=["POST"])
def api_do_restock():
    data = request.get_json(force=True)
    pn   = (data.get("part_number") or "").strip()
    qty  = int(data.get("qty", 0))
    if not pn or qty <= 0:
        return jsonify({"ok": False, "error": "Invalid part or qty"}), 400
    restock(pn, qty, data.get("supplier",""), data.get("po_number",""), data.get("notes",""))
    conn = get_conn()
    row  = conn.execute("SELECT in_stock FROM products WHERE part_number=?", (pn,)).fetchone()
    conn.close()
    return jsonify({"ok": True, "part_number": pn, "new_stock": row["in_stock"] if row else "?"})


@app.route("/restock", methods=["GET","POST"])
def restock_page():
    # Legacy POST support (from direct links like /restock?pn=X)
    pn = request.args.get("pn","").strip()
    if request.method == "POST":
        f = request.form
        restock(f["part_number"], int(f["qty"]), f.get("supplier",""),
                f.get("po_number",""), f.get("notes",""))
        flash(f"Restocked {f['part_number']} +{f['qty']}", "success")
        return redirect(url_for("products"))

    prefill_pn = pn  # passed from low-stock restock button

    body = f"""
    <div class="page-title">📥 Restock
      <span style="font-size:.8rem;color:var(--muted);font-weight:400;margin-left:.5rem">
        Scan barcode or search to find a product, then enter qty
      </span>
    </div>

    <!-- ── Find product bar ─────────────────────────────────────────── -->
    <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;
                padding:1.2rem 1.5rem;margin-bottom:1.5rem">
      <div style="font-weight:600;margin-bottom:.9rem;font-size:.95rem">
        Step 1 — Find Product
      </div>
      <div style="display:flex;gap:.75rem;flex-wrap:wrap;align-items:flex-end">
        <div style="display:flex;flex-direction:column;gap:.4rem;flex:1;min-width:200px;max-width:320px">
          <label style="font-size:.78rem;color:var(--muted);font-weight:500">
            🔍 Scan Barcode (LWR201)
          </label>
          <input id="bc-input" placeholder="Scan barcode…"
                 autocomplete="off" spellcheck="false"
                 style="font-family:'JetBrains Mono',monospace;font-size:1rem;
                        letter-spacing:.05em;padding:.6rem .9rem;
                        background:var(--surface);border:2px solid var(--accent);
                        color:var(--text);border-radius:8px;width:100%;outline:none">
        </div>
        <div style="display:flex;flex-direction:column;gap:.4rem;flex:2;min-width:200px;max-width:400px">
          <label style="font-size:.78rem;color:var(--muted);font-weight:500">
            🔎 Search by Name / Part No. / Category
          </label>
          <input id="search-input" placeholder="e.g. ESP32, NFC, AMS1117…"
                 oninput="onSearch()"
                 style="padding:.6rem .9rem;background:var(--surface);
                        border:1px solid var(--border);color:var(--text);
                        border-radius:8px;font-size:.9rem;font-family:inherit;
                        width:100%;outline:none;transition:border .15s"
                 onfocus="this.style.borderColor='var(--accent)'"
                 onblur="this.style.borderColor='var(--border)'">
        </div>
        <button onclick="loadProducts()" class="btn btn-ghost" style="padding:.6rem 1rem">
          Show All
        </button>
      </div>

      <!-- Search results -->
      <div id="search-results" style="margin-top:1rem"></div>
    </div>

    <!-- ── Restock form ─────────────────────────────────────────────── -->
    <div id="restock-panel" style="display:{'block' if prefill_pn else 'none'}">
      <div style="background:var(--card);border:1px solid var(--accent2);border-radius:12px;padding:1.2rem 1.5rem">
        <div style="font-weight:600;margin-bottom:.9rem;font-size:.95rem">
          Step 2 — Enter Restock Details
        </div>

        <!-- Selected product info card -->
        <div id="selected-product" style="background:var(--surface);border:1px solid var(--border);
             border-radius:10px;padding:1rem 1.1rem;margin-bottom:1.1rem">
          <div style="display:flex;gap:1rem;align-items:flex-start">
            <!-- Image -->
            <div id="sel-img" style="width:72px;height:72px;border-radius:8px;background:var(--card);
                 border:1px solid var(--border);display:flex;align-items:center;
                 justify-content:center;font-size:2rem;flex-shrink:0">📦</div>
            <!-- Main info -->
            <div style="flex:1;min-width:0">
              <div id="sel-name" style="font-weight:700;font-size:1.05rem">—</div>
              <div id="sel-pn-bc" style="font-family:monospace;font-size:.8rem;color:var(--muted);margin:.2rem 0">—</div>
              <div id="sel-desc" style="font-size:.82rem;color:var(--muted);margin-top:.15rem;
                   white-space:nowrap;overflow:hidden;text-overflow:ellipsis"></div>
            </div>
            <!-- Stock badge -->
            <div style="text-align:right;flex-shrink:0">
              <div style="font-size:2rem;font-weight:700;line-height:1" id="sel-qty">—</div>
              <div style="font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em">In Stock</div>
              <div id="sel-min" style="font-size:.72rem;color:var(--muted);margin-top:.1rem"></div>
            </div>
          </div>
          <!-- Detail chips row -->
          <div style="display:flex;gap:.6rem;flex-wrap:wrap;margin-top:.75rem">
            <span id="sel-cat"  style="background:var(--card);border:1px solid var(--border);
              border-radius:20px;padding:.18rem .6rem;font-size:.75rem;color:var(--muted)"></span>
            <span id="sel-loc"  style="background:var(--card);border:1px solid var(--border);
              border-radius:20px;padding:.18rem .6rem;font-size:.75rem;color:var(--muted)"></span>
            <span id="sel-price" style="background:var(--card);border:1px solid var(--border);
              border-radius:20px;padding:.18rem .6rem;font-size:.75rem;color:var(--muted)"></span>
            <span id="sel-last" style="background:var(--card);border:1px solid var(--border);
              border-radius:20px;padding:.18rem .6rem;font-size:.75rem;color:var(--muted)"></span>
          </div>
        </div>

        <form id="restock-form">
          <input type="hidden" id="f-pn" name="part_number" value="{prefill_pn}">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
            <div style="display:flex;flex-direction:column;gap:.4rem">
              <label style="font-size:.8rem;color:var(--muted);font-weight:500">Qty to Add *</label>
              <input id="f-qty" name="qty" type="number" min="1" value="10" required
                     style="padding:.55rem .8rem;background:var(--surface);border:1px solid var(--border);
                            color:var(--text);border-radius:8px;font-size:.9rem;font-family:inherit">
            </div>
            <div style="display:flex;flex-direction:column;gap:.4rem">
              <label style="font-size:.8rem;color:var(--muted);font-weight:500">Supplier</label>
              <input id="f-supplier" name="supplier" placeholder="e.g. Robu.in, LCSC, Amazon"
                     style="padding:.55rem .8rem;background:var(--surface);border:1px solid var(--border);
                            color:var(--text);border-radius:8px;font-size:.9rem;font-family:inherit">
            </div>
            <div style="display:flex;flex-direction:column;gap:.4rem">
              <label style="font-size:.8rem;color:var(--muted);font-weight:500">PO / Order Number</label>
              <input id="f-po" name="po_number" placeholder="PO-2026-001"
                     style="padding:.55rem .8rem;background:var(--surface);border:1px solid var(--border);
                            color:var(--text);border-radius:8px;font-size:.9rem;font-family:inherit">
            </div>
            <div style="display:flex;flex-direction:column;gap:.4rem">
              <label style="font-size:.8rem;color:var(--muted);font-weight:500">Notes</label>
              <input id="f-notes" name="notes" placeholder="Optional notes…"
                     style="padding:.55rem .8rem;background:var(--surface);border:1px solid var(--border);
                            color:var(--text);border-radius:8px;font-size:.9rem;font-family:inherit">
            </div>
          </div>
          <div style="margin-top:1.1rem;display:flex;gap:.75rem;align-items:center">
            <button type="button" onclick="doRestock()" class="btn btn-success"
                    style="padding:.6rem 1.4rem;font-size:.95rem">
              ✅ Add Stock
            </button>
            <button type="button" onclick="clearSelection()" class="btn btn-ghost">
              ✖ Cancel
            </button>
            <div id="restock-msg" style="font-size:.875rem;margin-left:.5rem"></div>
          </div>
        </form>
      </div>
    </div>

    <!-- ── Restock log (this session) ──────────────────────────────── -->
    <div style="font-weight:600;font-size:.95rem;margin-top:2rem;margin-bottom:.75rem">
      Restocked this session
    </div>
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th>#</th><th>Part No.</th><th>Model</th><th>Added</th>
          <th>New Stock</th><th>Supplier</th><th>PO</th><th>Time</th>
        </tr></thead>
        <tbody id="restock-log-body">
          <tr id="log-placeholder"><td colspan="8"
            style="text-align:center;color:var(--muted);padding:1.5rem">
            No restocks yet this session
          </td></tr>
        </tbody>
      </table>
    </div>

    <script>
    const bcInp     = document.getElementById('bc-input');
    const searchInp = document.getElementById('search-input');
    const results   = document.getElementById('search-results');
    const panel     = document.getElementById('restock-panel');
    let   logCount  = 0;
    let   searchTimer = null;

    // ── Auto-focus barcode input ────────────────────────────────────
    bcInp.focus();
    document.addEventListener('click', e => {{
      const skip = ['search-input','f-qty','f-supplier','f-po','f-notes','f-pn'];
      if (!skip.includes(e.target.id) && e.target.tagName !== 'BUTTON'
          && e.target.tagName !== 'SELECT' && e.target.tagName !== 'INPUT'
          && !e.target.closest('#search-results')
          && !e.target.closest('#restock-panel')) {{
        bcInp.focus();
      }}
    }});

    // ── Barcode scan (LWR201 sends chars + Enter) ───────────────────
    // Use keyup so the full barcode string is already in value when Enter fires
    bcInp.addEventListener('keyup', e => {{
      if (e.key === 'Enter') {{
        e.preventDefault();
        const bc = bcInp.value.trim();
        if (!bc) return;
        bcInp.value = '';
        scanBarcode(bc);
      }}
    }});

    async function scanBarcode(bc) {{
      // Show scanning indicator
      results.innerHTML = `<div style="color:var(--muted);font-size:.875rem;padding:.4rem 0">
        🔄 Looking up <span style="font-family:monospace">${{bc}}</span>…</div>`;

      try {{
        const resp = await fetch('/api/restock_search?barcode=' + encodeURIComponent(bc));
        const rows = await resp.json();

        if (rows.length === 1) {{
          results.innerHTML = '';
          selectProduct(rows[0]);
        }} else {{
          results.innerHTML = `
            <div style="background:#3a1515;border:1px solid var(--danger);border-radius:8px;
                        padding:.7rem 1rem;margin-top:.4rem;font-size:.875rem">
              ❌ Barcode not found in database:
              <span style="font-family:monospace;color:#ff9999">${{bc}}</span><br>
              <span style="color:var(--muted);font-size:.8rem">
                Check the barcode is added under Products first.
              </span>
            </div>`;
        }}
      }} catch(err) {{
        results.innerHTML = `<div style="color:var(--danger)">🔴 Error: ${{err.message}}</div>`;
      }}
      bcInp.focus();
    }}

    // ── Search input with debounce ──────────────────────────────────
    function onSearch() {{
      clearTimeout(searchTimer);
      const q = searchInp.value.trim();
      if (!q) {{ results.innerHTML = ''; return; }}
      searchTimer = setTimeout(() => fetchResults(q, null), 250);
    }}

    function loadProducts() {{
      searchInp.value = '';
      fetchResults('', null);
    }}

    async function fetchResults(q, bc) {{
      const url = bc
        ? `/api/restock_search?barcode=${{encodeURIComponent(bc)}}`
        : `/api/restock_search?q=${{encodeURIComponent(q)}}`;
      const rows = await (await fetch(url)).json();
      if (!rows.length) {{
        results.innerHTML = '<div style="color:var(--muted);font-size:.875rem;padding:.5rem 0">No products found.</div>';
        return;
      }}
      results.innerHTML = `
        <div style="background:var(--surface);border:1px solid var(--border);
                    border-radius:10px;overflow:hidden;max-height:320px;overflow-y:auto">
          <table style="width:100%;border-collapse:collapse;font-size:.85rem">
            <thead><tr style="background:var(--card)">
              <th style="padding:.5rem .8rem;text-align:left;font-size:.72rem;
                         color:var(--muted);text-transform:uppercase;letter-spacing:.04em"></th>
              <th style="padding:.5rem .8rem;text-align:left;font-size:.72rem;
                         color:var(--muted);text-transform:uppercase;letter-spacing:.04em">Part No.</th>
              <th style="padding:.5rem .8rem;text-align:left;font-size:.72rem;
                         color:var(--muted);text-transform:uppercase;letter-spacing:.04em">Model</th>
              <th style="padding:.5rem .8rem;text-align:left;font-size:.72rem;
                         color:var(--muted);text-transform:uppercase;letter-spacing:.04em">Category</th>
              <th style="padding:.5rem .8rem;text-align:left;font-size:.72rem;
                         color:var(--muted);text-transform:uppercase;letter-spacing:.04em">Stock</th>
              <th style="padding:.5rem .8rem;text-align:left;font-size:.72rem;
                         color:var(--muted);text-transform:uppercase;letter-spacing:.04em">Location</th>
              <th></th>
            </tr></thead>
            <tbody>
              ${{rows.map(r => `
                <tr style="border-top:1px solid var(--border);cursor:pointer"
                    onmouseover="this.style.background='rgba(79,142,247,.06)'"
                    onmouseout="this.style.background=''"
                    onclick="selectProduct(${{JSON.stringify(r).replace(/'/g,\"\\\'\")}})">
                  <td style="padding:.5rem .8rem">
                    ${{r.image_path
                      ? `<img src="/${{r.image_path}}" style="width:36px;height:36px;object-fit:cover;border-radius:5px">`
                      : `<div style="width:36px;height:36px;border-radius:5px;background:var(--card);
                              border:1px solid var(--border);display:flex;align-items:center;
                              justify-content:center;font-size:.9rem">📦</div>`}}
                  </td>
                  <td style="padding:.5rem .8rem;font-family:monospace;font-size:.8rem">${{r.part_number}}</td>
                  <td style="padding:.5rem .8rem">${{r.model_name}}</td>
                  <td style="padding:.5rem .8rem;color:var(--muted);font-size:.8rem">${{r.category||'—'}}</td>
                  <td style="padding:.5rem .8rem">
                    ${{r.in_stock === 0
                      ? '<span class="badge badge-out">0</span>'
                      : r.in_stock <= r.min_stock
                        ? `<span class="badge badge-low">${{r.in_stock}}</span>`
                        : `<span class="badge badge-ok">${{r.in_stock}}</span>`}}
                  </td>
                  <td style="padding:.5rem .8rem;color:var(--muted);font-size:.8rem">${{r.location||'—'}}</td>
                  <td style="padding:.5rem .8rem">
                    <button class="btn btn-success btn-sm"
                      onclick="event.stopPropagation();selectProduct(${{JSON.stringify(r).replace(/'/g,\"\\\'"\")}})"
                      >Select</button>
                  </td>
                </tr>`).join('')}}
            </tbody>
          </table>
        </div>`;
    }}

    async function fetchAndSelect(q) {{
      // Used for pre-fill from URL param (?pn=X) and search
      if (!q) return;
      const rows = await (await fetch('/api/restock_search?q=' + encodeURIComponent(q))).json();
      if (rows.length === 1) {{
        selectProduct(rows[0]);
      }} else if (rows.length > 1) {{
        searchInp.value = q;
        await fetchResults(q, null);
        panel.style.display = 'none';
      }} else {{
        results.innerHTML = `<div style="color:var(--muted);font-size:.875rem;padding:.4rem 0">
          No products found for "${{q}}"</div>`;
      }}
    }}

    function selectProduct(r) {{
      // ── Hidden field ────────────────────────────────────────────
      document.getElementById('f-pn').value = r.part_number;

      // ── Product image ───────────────────────────────────────────
      const imgEl = document.getElementById('sel-img');
      imgEl.innerHTML = r.image_path
        ? `<img src="/${{r.image_path}}" style="width:72px;height:72px;object-fit:cover;border-radius:8px">`
        : '📦';

      // ── Main info ───────────────────────────────────────────────
      document.getElementById('sel-name').textContent    = r.model_name;
      document.getElementById('sel-pn-bc').textContent   = r.part_number + '  |  Barcode: ' + (r.barcode||'—');
      document.getElementById('sel-desc').textContent    = r.description || '';

      // ── Stock ───────────────────────────────────────────────────
      const qtyEl = document.getElementById('sel-qty');
      qtyEl.textContent = r.in_stock;
      qtyEl.style.color = r.in_stock === 0 ? 'var(--danger)'
                        : r.in_stock <= r.min_stock ? 'var(--warn)' : 'var(--accent2)';
      document.getElementById('sel-min').textContent = 'Min: ' + r.min_stock;

      // ── Chips ───────────────────────────────────────────────────
      document.getElementById('sel-cat').textContent   = '📂 ' + (r.category  || 'No category');
      document.getElementById('sel-loc').textContent   = '📍 ' + (r.location  || 'No location');
      document.getElementById('sel-price').textContent = '₹'   + (r.unit_price != null ? parseFloat(r.unit_price).toFixed(2) : '—');
      document.getElementById('sel-last').textContent  = r.last_supplier
        ? '🔄 Last: ' + r.last_supplier + (r.last_qty ? ' ×'+r.last_qty : '')
        : '🔄 No previous restock';

      // ── Pre-fill form fields ────────────────────────────────────
      // Qty: suggest same as last restock if available, else 10
      document.getElementById('f-qty').value     = r.last_qty || 10;
      // Supplier & PO: pre-fill from last restock (user can change)
      document.getElementById('f-supplier').value = r.last_supplier || '';
      document.getElementById('f-po').value       = '';   // PO is always fresh
      document.getElementById('f-notes').value    = '';

      // ── Show panel ──────────────────────────────────────────────
      panel.style.display = 'block';
      results.innerHTML   = '';
      searchInp.value     = '';
      document.getElementById('f-qty').focus();
      document.getElementById('f-qty').select();
      panel.scrollIntoView({{behavior:'smooth', block:'nearest'}});
    }}

    function clearSelection() {{
      panel.style.display = 'none';
      results.innerHTML   = '';
      document.getElementById('f-pn').value = '';
      bcInp.focus();
    }}

    async function doRestock() {{
      const pn  = document.getElementById('f-pn').value.trim();
      const qty = parseInt(document.getElementById('f-qty').value) || 0;
      const msg = document.getElementById('restock-msg');

      if (!pn) {{ msg.innerHTML='<span style="color:var(--danger)">Select a product first.</span>'; return; }}
      if (qty < 1) {{ msg.innerHTML='<span style="color:var(--danger)">Qty must be ≥ 1.</span>'; return; }}

      const payload = {{
        part_number: pn,
        qty:         qty,
        supplier:    document.getElementById('f-supplier').value.trim(),
        po_number:   document.getElementById('f-po').value.trim(),
        notes:       document.getElementById('f-notes').value.trim(),
      }};

      const resp = await fetch('/api/do_restock', {{
        method:'POST', headers:{{'Content-Type':'application/json'}},
        body: JSON.stringify(payload)
      }});
      const d = await resp.json();

      if (d.ok) {{
        msg.innerHTML = `<span style="color:var(--accent2)">✅ Done! New stock: ${{d.new_stock}}</span>`;
        document.getElementById('sel-qty').textContent = d.new_stock;
        addLogRow(pn, document.getElementById('sel-name').textContent, qty,
                  d.new_stock, payload.supplier, payload.po_number);
        // Reset form fields but keep product selected
        document.getElementById('f-qty').value = '10';
        document.getElementById('f-supplier').value = '';
        document.getElementById('f-po').value = '';
        document.getElementById('f-notes').value = '';
        setTimeout(() => {{ msg.innerHTML = ''; }}, 3000);
      }} else {{
        msg.innerHTML = `<span style="color:var(--danger)">❌ ${{d.error}}</span>`;
      }}
    }}

    function addLogRow(pn, model, qty, newStock, supplier, po) {{
      logCount++;
      const ph = document.getElementById('log-placeholder');
      if (ph) ph.remove();
      const now = new Date().toLocaleTimeString();
      const tr  = document.createElement('tr');
      tr.innerHTML = `
        <td style="color:var(--muted);font-size:.8rem">${{logCount}}</td>
        <td style="font-family:monospace;font-size:.82rem">${{pn}}</td>
        <td style="font-size:.85rem">${{model}}</td>
        <td style="color:var(--accent2);font-weight:600">+${{qty}}</td>
        <td><span class="badge badge-ok">${{newStock}}</span></td>
        <td style="color:var(--muted);font-size:.82rem">${{supplier||'—'}}</td>
        <td style="color:var(--muted);font-size:.82rem">${{po||'—'}}</td>
        <td style="color:var(--muted);font-size:.78rem">${{now}}</td>`;
      document.getElementById('restock-log-body').insertBefore(tr,
        document.getElementById('restock-log-body').firstChild);
    }}

    // Pre-select if coming from low-stock button (/restock?pn=X)
    const prefillPn = "{prefill_pn}";
    if (prefillPn) {{
      fetchAndSelect(prefillPn);
    }}
    </script>
    """
    return render_template_string(HTML, body=body, page='restock')


# ─── Logs ─────────────────────────────────────────────────────────────────────
@app.route("/logs")
def logs():
    conn = get_conn()
    scans = conn.execute("""
        SELECT s.*,p.model_name,p.part_number as pn FROM scan_log s
        LEFT JOIN products p ON s.barcode=p.barcode
        ORDER BY s.scanned_at DESC LIMIT 50""").fetchall()
    restocks = conn.execute("""
        SELECT r.*,p.part_number,p.model_name FROM restock_log r
        JOIN products p ON r.product_id=p.id
        ORDER BY r.logged_at DESC LIMIT 50""").fetchall()
    conn.close()

    scan_rows = "".join(f"""<tr>
        <td class="mono" style="font-size:.8rem;color:var(--muted)">{r['scanned_at']}</td>
        <td class="mono">{r['barcode']}</td>
        <td>{r['pn'] or '—'}</td>
        <td><span class="badge {'badge-ok' if r['action']=='LOOKUP' else 'badge-low' if r['action']=='CONSUME' else 'badge-out'}">{r['action']}</span></td>
        <td>{r['qty']}</td>
    </tr>""" for r in scans)

    rst_rows = "".join(f"""<tr>
        <td class="mono" style="font-size:.8rem;color:var(--muted)">{r['logged_at']}</td>
        <td class="mono">{r['part_number']}</td>
        <td>{r['model_name']}</td>
        <td style="color:var(--accent2)">+{r['qty_added']}</td>
        <td>{r['supplier'] or '—'}</td>
        <td>{r['po_number'] or '—'}</td>
        <td style="color:var(--muted);font-size:.82rem">{r['notes'] or ''}</td>
    </tr>""" for r in restocks)

    body = f"""
    <div class="page-title">📋 Activity Logs</div>

    <div style="font-weight:600;margin-bottom:.75rem">Scan Log (last 50)</div>
    <div class="tbl-wrap" style="margin-bottom:2rem">
      <table><thead><tr><th>Time</th><th>Barcode</th><th>Part No.</th><th>Action</th><th>Qty</th></tr></thead>
      <tbody>{scan_rows or '<tr><td colspan=5 style="text-align:center;color:var(--muted);padding:1.5rem">No scans yet</td></tr>'}</tbody></table>
    </div>

    <div style="font-weight:600;margin-bottom:.75rem">Restock Log (last 50)</div>
    <div class="tbl-wrap">
      <table><thead><tr><th>Time</th><th>Part No.</th><th>Model</th><th>Qty</th><th>Supplier</th><th>PO</th><th>Notes</th></tr></thead>
      <tbody>{rst_rows or '<tr><td colspan=7 style="text-align:center;color:var(--muted);padding:1.5rem">No restock events yet</td></tr>'}</tbody></table>
    </div>"""
    return render_template_string(HTML, body=body, page='logs')


# ─── API endpoint (JSON) ──────────────────────────────────────────────────────
@app.route("/api/scan/<barcode>")
def api_scan(barcode):
    row = lookup_barcode(barcode)
    if not row:
        return jsonify({"found": False, "barcode": barcode}), 404
    return jsonify({"found": True, **{k: row[k] for k in row.keys()}})


# ─── Serve static images ───────────────────────────────────────────────────────
@app.route("/static/images/<filename>")
def static_images(filename):
    from flask import send_from_directory
    return send_from_directory(IMAGE_DIR, filename)


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    # seed only if db is empty
    conn = get_conn()
    if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        conn.close()
        from inventory import seed_demo
        seed_demo()
    else:
        conn.close()
    print("\n🚀  Inventory Manager running →  http://localhost:5000\n")
    app.run(debug=True, port=5000)
