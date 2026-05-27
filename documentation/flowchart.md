"""
Queue Management System
Priority Lanes: Regular | Priority | VIP
"""

import sqlite3
import os
import sys
from datetime import datetime
from collections import deque

# ─── ANSI COLORS ────────────────────────────────────────────────────────────

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"

    # Lane colors
    REGULAR  = "\033[94m"   # blue
    PRIORITY = "\033[93m"   # amber/yellow
    VIP      = "\033[95m"   # magenta/purple

    # UI colors
    GREEN    = "\033[92m"
    RED      = "\033[91m"
    CYAN     = "\033[96m"
    WHITE    = "\033[97m"
    GREY     = "\033[90m"

LANE_COLOR = {"Regular": C.REGULAR, "Priority": C.PRIORITY, "VIP": C.VIP}
LANE_PREFIX = {"Regular": "R", "Priority": "P", "VIP": "V"}
LANE_ORDER  = ["VIP", "Priority", "Regular"]   # serving priority


# ─── DATABASE ────────────────────────────────────────────────────────────────

DB_FILE = "queue_system.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket      TEXT    NOT NULL UNIQUE,
            name        TEXT    NOT NULL,
            lane        TEXT    NOT NULL,
            status      TEXT    NOT NULL DEFAULT 'Waiting',
            joined_at   TEXT    NOT NULL,
            served_at   TEXT,
            done_at     TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB_FILE)


# ─── TICKET COUNTER ──────────────────────────────────────────────────────────

def next_ticket_number(lane: str) -> str:
    prefix = LANE_PREFIX[lane]
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT COUNT(*) FROM customers WHERE lane = ?", (lane,)
    )
    count = c.fetchone()[0]
    conn.close()
    return f"{prefix}-{count + 1:03d}"


# ─── DISPLAY HELPERS ─────────────────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def banner():
    print(f"""
{C.BOLD}{C.CYAN}╔══════════════════════════════════════════════╗
║       QUEUE  MANAGEMENT  SYSTEM              ║
║  {C.REGULAR}■ Regular{C.CYAN}  {C.PRIORITY}▲ Priority{C.CYAN}  {C.VIP}★ VIP{C.CYAN}               ║
╚══════════════════════════════════════════════╝{C.RESET}
""")

def lane_tag(lane: str) -> str:
    col = LANE_COLOR.get(lane, C.WHITE)
    icon = {"Regular": "■", "Priority": "▲", "VIP": "★"}.get(lane, "?")
    return f"{col}{C.BOLD}{icon} {lane}{C.RESET}"

def ticket_tag(ticket: str) -> str:
    lane = {"R": "Regular", "P": "Priority", "V": "VIP"}.get(ticket[0], "Regular")
    col  = LANE_COLOR.get(lane, C.WHITE)
    return f"{col}{C.BOLD}[{ticket}]{C.RESET}"

def status_tag(status: str) -> str:
    colors = {"Waiting": C.GREY, "Serving": C.GREEN, "Done": C.DIM}
    return f"{colors.get(status, C.WHITE)}{status}{C.RESET}"

def divider(char="─", width=48):
    print(f"{C.GREY}{char * width}{C.RESET}")

def pause():
    print(f"\n{C.GREY}Press Enter to return to menu…{C.RESET}", end="")
    input()


# ─── CORE ACTIONS ────────────────────────────────────────────────────────────

def join_queue():
    clear(); banner()
    print(f"{C.BOLD}  JOIN QUEUE{C.RESET}\n")

    name = input(f"  Customer name: ").strip()
    if not name:
        print(f"\n  {C.RED}✗ Name cannot be empty.{C.RESET}")
        pause(); return

    print(f"\n  Select lane:")
    for i, lane in enumerate(["Regular", "Priority", "VIP"], 1):
        print(f"    {lane_tag(lane)}  [{i}]")

    choice = input("\n  Enter 1 / 2 / 3: ").strip()
    lanes = {"1": "Regular", "2": "Priority", "3": "VIP"}
    lane  = lanes.get(choice)
    if not lane:
        print(f"\n  {C.RED}✗ Invalid choice.{C.RESET}")
        pause(); return

    ticket = next_ticket_number(lane)
    now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_conn()
    conn.execute(
        "INSERT INTO customers (ticket, name, lane, status, joined_at) VALUES (?,?,?,?,?)",
        (ticket, name, lane, "Waiting", now)
    )
    conn.commit(); conn.close()

    print(f"\n  {C.GREEN}✓ Added!{C.RESET}  {ticket_tag(ticket)}  {C.WHITE}{name}{C.RESET}  → {lane_tag(lane)}")
    pause()


def call_next():
    clear(); banner()
    print(f"{C.BOLD}  CALL NEXT{C.RESET}\n")

    conn = get_conn()

    # Check if someone is already being served
    serving = conn.execute(
        "SELECT ticket, name, lane FROM customers WHERE status='Serving'"
    ).fetchone()

    if serving:
        t, n, l = serving
        print(f"  {C.PRIORITY}⚠ Counter busy:{C.RESET} {ticket_tag(t)} {C.WHITE}{n}{C.RESET} ({lane_tag(l)}) is being served.")
        conn.close(); pause(); return

    # Find next by priority order
    called = None
    for lane in LANE_ORDER:
        row = conn.execute(
            "SELECT id, ticket, name FROM customers WHERE lane=? AND status='Waiting' ORDER BY id ASC LIMIT 1",
            (lane,)
        ).fetchone()
        if row:
            called = (row[0], row[1], row[2], lane)
            break

    if not called:
        print(f"  {C.GREY}No customers waiting in any queue.{C.RESET}")
        conn.close(); pause(); return

    cid, ticket, name, lane = called
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE customers SET status='Serving', served_at=? WHERE id=?",
        (now, cid)
    )
    conn.commit(); conn.close()

    print(f"  {C.GREEN}📢 Now serving:{C.RESET}  {ticket_tag(ticket)}  {C.WHITE}{name}{C.RESET}  ({lane_tag(lane)})")
    pause()


def mark_done():
    clear(); banner()
    print(f"{C.BOLD}  MARK AS DONE{C.RESET}\n")

    conn = get_conn()
    row = conn.execute(
        "SELECT id, ticket, name, lane FROM customers WHERE status='Serving'"
    ).fetchone()

    if not row:
        print(f"  {C.GREY}No customer is currently being served.{C.RESET}")
        conn.close(); pause(); return

    cid, ticket, name, lane = row
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE customers SET status='Done', done_at=? WHERE id=?",
        (now, cid)
    )
    conn.commit(); conn.close()

    print(f"  {C.GREEN}✓ Done:{C.RESET}  {ticket_tag(ticket)}  {C.WHITE}{name}{C.RESET}  ({lane_tag(lane)}) — counter is free.")
    pause()


def view_queue():
    clear(); banner()
    print(f"{C.BOLD}  CURRENT QUEUE{C.RESET}\n")

    conn = get_conn()

    # Show currently serving first
    serving = conn.execute(
        "SELECT ticket, name, lane, served_at FROM customers WHERE status='Serving'"
    ).fetchone()
    if serving:
        t, n, l, sa = serving
        print(f"  {C.GREEN}● NOW SERVING{C.RESET}  {ticket_tag(t)}  {C.WHITE}{n}{C.RESET}  ({lane_tag(l)})")
        print(f"    {C.GREY}Since {sa}{C.RESET}")
        divider()

    # Show waiting per lane
    any_waiting = False
    for lane in LANE_ORDER:
        rows = conn.execute(
            "SELECT ticket, name, joined_at FROM customers WHERE lane=? AND status='Waiting' ORDER BY id ASC",
            (lane,)
        ).fetchall()
        if rows:
            any_waiting = True
            print(f"  {lane_tag(lane)}  ({len(rows)} waiting)")
            for pos, (ticket, name, joined) in enumerate(rows, 1):
                print(f"    {C.GREY}{pos:>2}.{C.RESET}  {ticket_tag(ticket)}  {C.WHITE}{name:<20}{C.RESET}  {C.GREY}{joined}{C.RESET}")
            print()

    if not serving and not any_waiting:
        print(f"  {C.GREY}All queues are empty.{C.RESET}")

    conn.close(); pause()


def view_history():
    clear(); banner()
    print(f"{C.BOLD}  FULL HISTORY{C.RESET}\n")

    conn = get_conn()
    rows = conn.execute(
        "SELECT ticket, name, lane, status, joined_at, served_at, done_at FROM customers ORDER BY id ASC"
    ).fetchall()
    conn.close()

    if not rows:
        print(f"  {C.GREY}No records found.{C.RESET}")
        pause(); return

    header = f"  {'Ticket':<8} {'Name':<20} {'Lane':<10} {'Status':<9} {'Joined':<20}"
    print(f"{C.GREY}{header}{C.RESET}")
    divider()

    for ticket, name, lane, status, joined, served, done in rows:
        col = LANE_COLOR.get(lane, C.WHITE)
        scol = {"Waiting": C.GREY, "Serving": C.GREEN, "Done": C.DIM}.get(status, C.WHITE)
        print(f"  {col}{ticket:<8}{C.RESET} {C.WHITE}{name:<20}{C.RESET} {col}{lane:<10}{C.RESET} {scol}{status:<9}{C.RESET} {C.GREY}{joined}{C.RESET}")

    pause()


def view_statistics():
    clear(); banner()
    print(f"{C.BOLD}  STATISTICS{C.RESET}\n")

    conn = get_conn()

    total = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    print(f"  Total records : {C.WHITE}{C.BOLD}{total}{C.RESET}")
    divider()

    for lane in LANE_ORDER:
        waiting  = conn.execute("SELECT COUNT(*) FROM customers WHERE lane=? AND status='Waiting'",  (lane,)).fetchone()[0]
        serving  = conn.execute("SELECT COUNT(*) FROM customers WHERE lane=? AND status='Serving'",  (lane,)).fetchone()[0]
        done     = conn.execute("SELECT COUNT(*) FROM customers WHERE lane=? AND status='Done'",     (lane,)).fetchone()[0]
        subtotal = conn.execute("SELECT COUNT(*) FROM customers WHERE lane=?", (lane,)).fetchone()[0]

        col = LANE_COLOR.get(lane, C.WHITE)
        print(f"\n  {lane_tag(lane)}")
        print(f"    Waiting  : {C.GREY}{waiting}{C.RESET}")
        print(f"    Serving  : {C.GREEN}{serving}{C.RESET}")
        print(f"    Done     : {C.DIM}{done}{C.RESET}")
        print(f"    Total    : {col}{subtotal}{C.RESET}")

    conn.close()
    divider()
    pause()


def delete_record():
    clear(); banner()
    print(f"{C.BOLD}  DELETE RECORD{C.RESET}\n")

    ticket = input("  Enter ticket number to delete (e.g. R-001): ").strip().upper()
    if not ticket:
        pause(); return

    conn = get_conn()
    row = conn.execute(
        "SELECT id, name, lane, status FROM customers WHERE ticket=?", (ticket,)
    ).fetchone()

    if not row:
        print(f"\n  {C.RED}✗ Ticket {ticket} not found.{C.RESET}")
        conn.close(); pause(); return

    cid, name, lane, status = row
    print(f"\n  Found: {ticket_tag(ticket)}  {C.WHITE}{name}{C.RESET}  ({lane_tag(lane)})  [{status_tag(status)}]")
    confirm = input(f"\n  {C.RED}Delete this record? (y/N):{C.RESET} ").strip().lower()

    if confirm == "y":
        conn.execute("DELETE FROM customers WHERE id=?", (cid,))
        conn.commit()
        print(f"\n  {C.GREEN}✓ Record deleted.{C.RESET}")
    else:
        print(f"\n  {C.GREY}Cancelled.{C.RESET}")

    conn.close(); pause()


# ─── MAIN MENU ────────────────────────────────────────────────────────────────

MENU_ITEMS = [
    ("1", "Join Queue",       join_queue),
    ("2", "Call Next",        call_next),
    ("3", "Mark as Done",     mark_done),
    ("4", "View Queue",       view_queue),
    ("5", "View History",     view_history),
    ("6", "View Statistics",  view_statistics),
    ("7", "Delete Record",    delete_record),
    ("0", "Exit",             None),
]

def main_menu():
    while True:
        clear(); banner()

        # Quick status bar
        conn = get_conn()
        serving = conn.execute("SELECT ticket, name FROM customers WHERE status='Serving'").fetchone()
        waiting_counts = {
            lane: conn.execute(
                "SELECT COUNT(*) FROM customers WHERE lane=? AND status='Waiting'", (lane,)
            ).fetchone()[0]
            for lane in LANE_ORDER
        }
        conn.close()

        if serving:
            t, n = serving
            print(f"  {C.GREEN}● Serving:{C.RESET} {ticket_tag(t)} {C.WHITE}{n}{C.RESET}")
        else:
            print(f"  {C.GREY}● Counter free{C.RESET}")

        print(f"  Waiting — "
              f"{C.REGULAR}Regular:{C.RESET} {waiting_counts['Regular']}  "
              f"{C.PRIORITY}Priority:{C.RESET} {waiting_counts['Priority']}  "
              f"{C.VIP}VIP:{C.RESET} {waiting_counts['VIP']}")
        print()
        divider()
        print()

        for key, label, _ in MENU_ITEMS:
            if key == "0":
                print(f"  {C.GREY}[{key}]{C.RESET}  {C.GREY}{label}{C.RESET}")
            else:
                print(f"  {C.CYAN}[{key}]{C.RESET}  {label}")

        print()
        choice = input("  Choose: ").strip()

        for key, _, fn in MENU_ITEMS:
            if choice == key:
                if fn is None:
                    clear()
                    print(f"\n  {C.GREY}Goodbye.{C.RESET}\n")
                    sys.exit(0)
                fn()
                break
        else:
            pass  # invalid choice — just redraw


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    main_menu()
