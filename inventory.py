#!/usr/bin/env python3
"""
Inventory Management System with Barcode Scanner (LWR201)
SQLite backend, Image upload with auto-resize, Restock management
"""

import sqlite3
import os
import shutil
import sys
from datetime import datetime
from PIL import Image

# ── Config ──────────────────────────────────────────────────────────────────
DB_PATH       = "inventory.db"
IMAGE_DIR     = "static/images"
THUMB_SIZE    = (200, 200)   # stored thumbnail dimensions
LOW_STOCK_QTY = 5            # highlight threshold

os.makedirs(IMAGE_DIR, exist_ok=True)


# ── Database ─────────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode       TEXT    UNIQUE NOT NULL,
            part_number   TEXT    UNIQUE NOT NULL,
            model_name    TEXT    NOT NULL,
            description   TEXT,
            category      TEXT    DEFAULT 'General',
            unit_price    REAL    DEFAULT 0.0,
            in_stock      INTEGER DEFAULT 0,
            min_stock     INTEGER DEFAULT 5,
            location      TEXT,
            image_path    TEXT,
            created_at    TEXT    DEFAULT (datetime('now')),
            updated_at    TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS restock_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id  INTEGER NOT NULL REFERENCES products(id),
            qty_added   INTEGER NOT NULL,
            supplier    TEXT,
            po_number   TEXT,
            notes       TEXT,
            logged_at   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS scan_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode     TEXT NOT NULL,
            action      TEXT NOT NULL,   -- LOOKUP / CONSUME / NOT_FOUND
            qty         INTEGER DEFAULT 1,
            scanned_at  TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()
    print("✅  Database initialised →", DB_PATH)


# ── Image helpers ─────────────────────────────────────────────────────────────
def save_image(src_path: str, part_number: str) -> str | None:
    """Resize & save product image; returns relative path or None."""
    if not src_path or not os.path.exists(src_path):
        return None
    ext = os.path.splitext(src_path)[1].lower() or ".jpg"
    dest_name = f"{part_number.replace('/', '_')}{ext}"
    dest_path = os.path.join(IMAGE_DIR, dest_name)
    try:
        img = Image.open(src_path).convert("RGB")
        img.thumbnail(THUMB_SIZE, Image.LANCZOS)
        img.save(dest_path, quality=85, optimize=True)
        print(f"  🖼  Image saved → {dest_path}  ({img.size[0]}×{img.size[1]}px)")
        return dest_path
    except Exception as e:
        print(f"  ⚠️  Image error: {e}")
        return None


# ── Product CRUD ──────────────────────────────────────────────────────────────
def add_product(barcode, part_number, model_name, description="",
                category="General", unit_price=0.0, in_stock=0,
                min_stock=5, location="", image_src=None):
    image_path = save_image(image_src, part_number) if image_src else None
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO products
              (barcode, part_number, model_name, description, category,
               unit_price, in_stock, min_stock, location, image_path)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (barcode, part_number, model_name, description, category,
              unit_price, in_stock, min_stock, location, image_path))
        conn.commit()
        print(f"✅  Product added → {part_number}  |  {model_name}")
    except sqlite3.IntegrityError as e:
        print(f"❌  Duplicate barcode or part number: {e}")
    finally:
        conn.close()


def update_product(part_number, **kwargs):
    """Update any field(s) by part_number."""
    if "image_src" in kwargs:
        kwargs["image_path"] = save_image(kwargs.pop("image_src"), part_number)
    kwargs["updated_at"] = datetime.now().isoformat(sep=" ", timespec="seconds")
    sets   = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [part_number]
    conn = get_conn()
    conn.execute(f"UPDATE products SET {sets} WHERE part_number=?", values)
    conn.commit()
    conn.close()
    print(f"✅  Updated → {part_number}")


def delete_product(part_number):
    conn = get_conn()
    row = conn.execute("SELECT image_path FROM products WHERE part_number=?",
                       (part_number,)).fetchone()
    if row and row["image_path"] and os.path.exists(row["image_path"]):
        os.remove(row["image_path"])
    conn.execute("DELETE FROM products WHERE part_number=?", (part_number,))
    conn.commit()
    conn.close()
    print(f"🗑  Deleted → {part_number}")


# ── Lookup / scanning ─────────────────────────────────────────────────────────
def lookup_barcode(barcode: str) -> sqlite3.Row | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM products WHERE barcode=?",
                       (barcode,)).fetchone()
    action = "LOOKUP" if row else "NOT_FOUND"
    conn.execute("INSERT INTO scan_log (barcode, action) VALUES (?,?)",
                 (barcode, action))
    conn.commit()
    conn.close()
    return row


def consume_stock(barcode: str, qty: int = 1):
    """Decrease stock by qty after scanning (e.g. pick/dispatch)."""
    conn = get_conn()
    row = conn.execute("SELECT id, in_stock, part_number FROM products WHERE barcode=?",
                       (barcode,)).fetchone()
    if not row:
        print(f"❌  Barcode not found: {barcode}")
        conn.execute("INSERT INTO scan_log (barcode, action, qty) VALUES (?,?,?)",
                     (barcode, "NOT_FOUND", qty))
        conn.commit()
        conn.close()
        return
    new_qty = max(0, row["in_stock"] - qty)
    conn.execute("UPDATE products SET in_stock=?, updated_at=datetime('now') WHERE id=?",
                 (new_qty, row["id"]))
    conn.execute("INSERT INTO scan_log (barcode, action, qty) VALUES (?,?,?)",
                 (barcode, "CONSUME", qty))
    conn.commit()
    conn.close()
    print(f"📦  {row['part_number']}  stock: {row['in_stock']} → {new_qty}")
    if new_qty <= LOW_STOCK_QTY:
        print(f"  ⚠️  LOW STOCK ALERT  (≤ {LOW_STOCK_QTY} units)")


# ── Restock ───────────────────────────────────────────────────────────────────
def restock(part_number: str, qty: int, supplier="", po_number="", notes=""):
    conn = get_conn()
    row = conn.execute("SELECT id, in_stock FROM products WHERE part_number=?",
                       (part_number,)).fetchone()
    if not row:
        print(f"❌  Part not found: {part_number}")
        conn.close()
        return
    new_qty = row["in_stock"] + qty
    conn.execute("UPDATE products SET in_stock=?, updated_at=datetime('now') WHERE id=?",
                 (new_qty, row["id"]))
    conn.execute("""
        INSERT INTO restock_log (product_id, qty_added, supplier, po_number, notes)
        VALUES (?,?,?,?,?)
    """, (row["id"], qty, supplier, po_number, notes))
    conn.commit()
    conn.close()
    print(f"✅  Restocked {part_number}  +{qty}  →  total {new_qty}")


# ── Reports ───────────────────────────────────────────────────────────────────
def _row_line(row, fields, widths):
    parts = []
    for f, w in zip(fields, widths):
        val = str(row[f] if row[f] is not None else "")
        parts.append(val[:w].ljust(w))
    return "  ".join(parts)


def list_all(low_stock_only=False):
    conn = get_conn()
    where = "WHERE in_stock <= min_stock" if low_stock_only else ""
    rows  = conn.execute(f"SELECT * FROM products {where} ORDER BY part_number").fetchall()
    conn.close()

    fields = ["part_number", "model_name", "category", "in_stock", "min_stock",
              "unit_price", "location", "barcode"]
    widths = [14, 20, 12, 8, 9, 9, 12, 14]
    header = "  ".join(f.upper()[:w].ljust(w) for f, w in zip(fields, widths))
    sep    = "-" * len(header)

    title = "⚠️  LOW / OUT-OF-STOCK ITEMS" if low_stock_only else "📦  ALL PRODUCTS"
    print(f"\n{title}  ({len(rows)} rows)")
    print(sep)
    print(header)
    print(sep)
    for r in rows:
        flag = "  ⚠️" if r["in_stock"] <= r["min_stock"] else ""
        print(_row_line(r, fields, widths) + flag)
    print(sep)


def show_product(part_number):
    conn = get_conn()
    row = conn.execute("SELECT * FROM products WHERE part_number=?",
                       (part_number,)).fetchone()
    conn.close()
    if not row:
        print(f"❌  Not found: {part_number}")
        return
    print("\n" + "─" * 50)
    for key in row.keys():
        print(f"  {key:<15} {row[key]}")
    print("─" * 50)


def restock_history(part_number):
    conn = get_conn()
    rows = conn.execute("""
        SELECT r.*, p.part_number, p.model_name
          FROM restock_log r
          JOIN products p ON r.product_id = p.id
         WHERE p.part_number = ?
         ORDER BY r.logged_at DESC
    """, (part_number,)).fetchall()
    conn.close()
    print(f"\n📋  Restock history for {part_number}  ({len(rows)} entries)")
    for r in rows:
        print(f"  {r['logged_at']}  +{r['qty_added']:>4}  "
              f"Supplier: {r['supplier'] or '—'}  "
              f"PO: {r['po_number'] or '—'}  "
              f"Notes: {r['notes'] or '—'}")


def scan_history(limit=20):
    conn = get_conn()
    rows = conn.execute("""
        SELECT s.*, p.part_number, p.model_name
          FROM scan_log s
          LEFT JOIN products p ON s.barcode = p.barcode
         ORDER BY s.scanned_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    print(f"\n🔍  Last {limit} scan events")
    for r in rows:
        part = r["part_number"] or "UNKNOWN"
        print(f"  {r['scanned_at']}  [{r['action']:<10}]  "
              f"{r['barcode']:<18}  {part}")


# ── Seed / demo data ──────────────────────────────────────────────────────────
def seed_demo():
    """Insert sample data including the LWR201 scanner itself."""
    products = [
        # barcode           part_number    model_name                  desc                          cat          price   qty  min  loc
        ("LWR201-0001",    "LWR201",      "LWR201 Barcode Scanner",   "1D/2D USB barcode reader",   "Scanners",  45.00,  12,   3,  "Shelf-A1"),
        ("ESP32S3-0001",   "ESP32-S3",    "ESP32-S3 DevKit",          "Dual-core 240MHz WiFi+BT",   "MCU",       8.50,    4,   5,  "Bin-B2"),
        ("PN532-I2C-001",  "PN532-MOD",   "PN532 NFC/RFID Module",    "I2C/SPI/HSU NFC reader",     "NFC",       6.75,    7,   3,  "Bin-B3"),
        ("RPICM4-0001",    "RPI-CM4",     "Raspberry Pi CM4",         "4GB RAM, 32GB eMMC",         "SBC",      75.00,    2,   2,  "Shelf-C1"),
        ("AMS1117-3V3",    "AMS1117-ADJ", "AMS1117 LDO Regulator",    "1A adjustable LDO, SOT-223", "IC",        0.35,   50,  10,  "Drawer-D1"),
        ("MAX98357A-001",  "MAX98357A",   "MAX98357A I2S Amp",        "3W Class D, no heatsink",    "Audio",     1.20,    8,   5,  "Bin-B5"),
        ("RC522-SPI-001",  "RC522-MOD",   "RC522 RFID Module",        "13.56MHz SPI RFID reader",   "NFC",       2.50,    3,   5,  "Bin-B3"),
        ("CH224K-USB-PD",  "CH224K",      "CH224K USB-PD Sink",       "100W PD trigger IC",         "IC",        0.90,   25,  10,  "Drawer-D2"),
        ("DAC8760-SPI",    "DAC8760",     "DAC8760 Industrial DAC",   "16-bit industrial output",   "IC",        9.80,    5,   3,  "Drawer-D3"),
        ("TCRT1000-S",     "TCRT1000",    "TCRT1000 Reflex Sensor",   "Opto-reflective IR sensor",  "Sensors",   0.55,   30,  10,  "Drawer-D4"),
    ]
    for (bc, pn, mn, desc, cat, price, qty, min_s, loc) in products:
        add_product(bc, pn, mn, desc, cat, price, qty, min_s, loc)


# ── CLI entry-point ───────────────────────────────────────────────────────────
def interactive_menu():
    while True:
        print("""
╔══════════════════════════════════════════╗
║     INVENTORY MANAGER  (LWR201 ready)    ║
╠══════════════════════════════════════════╣
║  1  Scan barcode (lookup)                ║
║  2  Scan barcode (consume stock)         ║
║  3  Restock a part                       ║
║  4  Add new product                      ║
║  5  List all products                    ║
║  6  Low-stock report                     ║
║  7  Show product detail                  ║
║  8  Restock history                      ║
║  9  Scan log                             ║
║  0  Exit                                 ║
╚══════════════════════════════════════════╝""")
        choice = input("  Choice → ").strip()

        if choice == "1":
            bc = input("  Scan barcode: ").strip()
            row = lookup_barcode(bc)
            if row:
                print(f"\n  ✅ {row['model_name']}  ({row['part_number']})")
                print(f"     In stock : {row['in_stock']}")
                print(f"     Location : {row['location']}")
                print(f"     Price    : ₹{row['unit_price']:.2f}")
            else:
                print("  ❌ Barcode not found in database.")

        elif choice == "2":
            bc  = input("  Scan barcode : ").strip()
            qty = int(input("  Qty to consume [1]: ").strip() or "1")
            consume_stock(bc, qty)

        elif choice == "3":
            pn  = input("  Part number  : ").strip()
            qty = int(input("  Qty to add   : ").strip())
            sup = input("  Supplier     : ").strip()
            po  = input("  PO number    : ").strip()
            nt  = input("  Notes        : ").strip()
            restock(pn, qty, sup, po, nt)

        elif choice == "4":
            bc   = input("  Barcode      : ").strip()
            pn   = input("  Part number  : ").strip()
            mn   = input("  Model name   : ").strip()
            desc = input("  Description  : ").strip()
            cat  = input("  Category [General]: ").strip() or "General"
            pr   = float(input("  Unit price   : ").strip() or "0")
            qty  = int(input("  Initial qty  : ").strip() or "0")
            mins = int(input("  Min stock    : ").strip() or "5")
            loc  = input("  Location     : ").strip()
            img  = input("  Image path (Enter to skip): ").strip() or None
            add_product(bc, pn, mn, desc, cat, pr, qty, mins, loc, img)

        elif choice == "5":
            list_all()

        elif choice == "6":
            list_all(low_stock_only=True)

        elif choice == "7":
            pn = input("  Part number: ").strip()
            show_product(pn)

        elif choice == "8":
            pn = input("  Part number: ").strip()
            restock_history(pn)

        elif choice == "9":
            scan_history()

        elif choice == "0":
            print("  Bye!")
            break


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()

    arg = sys.argv[1] if len(sys.argv) > 1 else ""

    if arg == "seed":
        print("\n── Seeding demo data ──")
        seed_demo()

    elif arg == "test":
        print("\n── Running quick tests ──")
        seed_demo()

        print("\n[TEST] Lookup existing barcode (LWR201-0001)")
        row = lookup_barcode("LWR201-0001")
        assert row and row["model_name"] == "LWR201 Barcode Scanner", "Lookup failed"
        print("  PASS")

        print("\n[TEST] Lookup unknown barcode")
        row = lookup_barcode("UNKNOWN-9999")
        assert row is None, "Should return None"
        print("  PASS")

        print("\n[TEST] Consume stock")
        consume_stock("LWR201-0001", 3)
        conn = get_conn()
        qty = conn.execute("SELECT in_stock FROM products WHERE barcode='LWR201-0001'").fetchone()[0]
        conn.close()
        assert qty == 9, f"Expected 9, got {qty}"
        print("  PASS")

        print("\n[TEST] Restock")
        restock("LWR201", 10, "Honeywell", "PO-2026-001", "Annual restock")
        conn = get_conn()
        qty = conn.execute("SELECT in_stock FROM products WHERE part_number='LWR201'").fetchone()[0]
        conn.close()
        assert qty == 19, f"Expected 19, got {qty}"
        print("  PASS")

        print("\n[TEST] Low stock detection (ESP32-S3 has 4, min 5)")
        list_all(low_stock_only=True)

        print("\n[TEST] Restock history")
        restock_history("LWR201")

        print("\n[TEST] Scan log")
        scan_history()

        print("\n✅  All tests passed!")

    else:
        interactive_menu()
