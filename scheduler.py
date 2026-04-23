import re
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
from mysql.connector import Error

from db import get_connection

VALID_SLOTS = [
    ("09:00", "10:00"), ("10:00", "11:00"), ("11:30", "12:30"),
    ("13:30", "14:30"), ("14:30", "15:30"), ("15:30", "16:30"),
    ("17:00", "18:00"),
]




def banner(title: str, width: int = 54):
    border = "=" * width
    print(f"\n{border}\n{title.center(width)}\n{border}\n")


def section(title: str):
    print(f"\n--- {title} ---")

def ok(msg: str): print(f"  [OK]  {msg}")

def warn(msg: str): print(f"  [!]   {msg}")

def err(msg: str): print(f"  [ERR] {msg}")

def info(msg: str): print(f"  [i]   {msg}")

def pause(): input("\n  Press Enter to continue...")


def prompt(label: str) -> str:
    while True:
        val = input(f"  {label}: ").strip()
        if val: return val
        err("This field cannot be empty.")


def prompt_email(label: str = "Email") -> str:
    pattern = r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$"
    while True:
        val = input(f"  {label}: ").strip()
        if re.match(pattern, val): return val
        err("Invalid email address. Try again.")


def prompt_date(label = "Date (YYYY-MM-DD)"):
    while True:
        raw = input(f"  {label}: ").strip()
        try:
            d = datetime.strptime(raw, "%Y-%m-%d").date()
            if d >= date.today(): return d
            warn("Date is in the past. Please enter today or a future date.")
        except ValueError:
            err("Invalid format. Use YYYY-MM-DD")


def prompt_date_any(label = "Date (YYYY-MM-DD)"):
    while True:
        raw = input(f"  {label}: ").strip()
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            err("Invalid format. Use YYYY-MM-DD")


def fmt_time(t) -> str:
    if isinstance(t, timedelta):
        total = int(t.total_seconds())
        h, rem = divmod(total, 3600)
        return f"{h:02d}:{rem // 60:02d}"
    if isinstance(t, str): return t[:5]
    return t.strftime("%H:%M")


def print_df(df: pd.DataFrame): print(f"\n{df.to_string(index=False)}\n")


def make_df(headers: list[str], rows: list[list]) -> pd.DataFrame:
    arr = np.array(rows, dtype=object) if rows else np.empty((0, len(headers)), dtype=object)
    return pd.DataFrame(arr, columns=headers)


def print_all_slots(all_slots: list[tuple], free_slots: list[tuple]):
    numbers = list(range(1, len(all_slots) + 1)) + [0]
    slot_labels = [f"{fmt_time(s)} - {fmt_time(e)}" for s, e in all_slots] + ["Cancel"]
    statuses = ["Available" if (s, e) in free_slots else "Booked" for s, e in all_slots] + [""]
    print_df(pd.DataFrame({"No.": numbers, "Slot": slot_labels, "Status": statuses}))


def print_free_slots(free_slots: list[tuple]):
    numbers = list(range(1, len(free_slots) + 1)) + [0]
    slot_labels = [f"{fmt_time(s)} - {fmt_time(e)}" for s, e in free_slots] + ["Cancel"]
    print_df(pd.DataFrame({"No.": numbers, "Slot": slot_labels}))


def menu(title: str, options: list[str]) -> int:
    section(title)
    for i, opt in enumerate(options, 1): print(f"  [{i}]  {opt}")
    print(f"  [0]  {'Exit' if title == 'Main Menu' else 'Back'}\n")
    while True:
        raw = input("  Your choice: ").strip()
        if raw.isdigit() and 0 <= int(raw) <= len(options): return int(raw)
        err(f"Enter a number between 0 and {len(options)}.")



def login():
    print("\n  Enter your Trainer ID to continue (or 0 to exit).")
    while True:
        raw = input("  Trainer ID: ").strip()
        if raw == "0": return None
        if not raw.isdigit():
            err("Trainer ID must be a number.")
            continue

        trainer_id = int(raw)
        trainer = _find_by_id(trainer_id)

        if trainer:
            ok(f"Welcome back, {trainer['name']}!")
            return trainer

        info("New ID detected. Let's get you registered.")
        return _register(trainer_id)


def _find_by_id(trainer_id) -> dict | None:
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT trainer_id, name, email FROM trainers WHERE trainer_id = %s", (trainer_id,))
    row = cur.fetchone()
    cur.close()
    return row


def _register(trainer_id) -> dict | None:
    name = prompt("Your name")
    email = prompt_email("Your email address")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT trainer_id FROM trainers WHERE email = %s", (email,))
    if cur.fetchone():
        cur.close()
        err(f"Email '{email}' is already registered to another trainer.")
        pause()
        return None
    try:
        cur.execute("INSERT INTO trainers (trainer_id, name, email) VALUES (%s, %s, %s)", (trainer_id, name, email))
        conn.commit()
        ok(f"Registered successfully! Welcome, {name}.")
        return {"trainer_id": trainer_id, "name": name, "email": email}
    except Error as e:
        conn.rollback()
        err(f"Database error: {e}")
        return None
    finally:
        cur.close()


def get_trainer_name(trainer_id):
    row = _find_by_id(trainer_id)
    return row["name"] if row else "Unknown"




def _get_all_batches() -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT batch_id, batch_name, course FROM batches ORDER BY batch_id")
    rows = cur.fetchall()
    cur.close()
    return rows


def get_batch_name(batch_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT batch_name FROM batches WHERE batch_id = %s", (batch_id,))
    row = cur.fetchone()
    cur.close()
    return row[0] if row else "Unknown"


def select_batch() -> int | None:
    rows = _get_all_batches()
    if not rows:
        warn("No batches exist in the system.")
        pause()
        return None
    print("\n--- Select Batch ---")
    print_df(make_df(["ID", "Batch Name", "Course"], [list(r) for r in rows]))
    while True:
        raw = input("  Enter Batch ID (or 0 to cancel): ").strip()
        if raw == "0": return None
        if raw.isdigit() and any(r[0] == int(raw) for r in rows): return int(raw)
        err("Invalid ID. Choose from the table above.")




def _to_td(hhmm: str) -> timedelta:
    h, m = map(int, hhmm.split(":"))
    return timedelta(hours=h, minutes=m)


VALID_SLOT_TD = [(_to_td(s), _to_td(e)) for s, e in VALID_SLOTS]


def _is_slot_taken(date, start_td, end_td, trainer_id, batch_id, exclude_session_id=None) -> tuple[bool, str]:
    conn = get_connection()
    cur = conn.cursor()
    base_q = "SELECT session_id FROM sessions WHERE session_date = %s AND start_time < %s AND end_time > %s AND {col} = %s {excl}"
    excl = f" AND session_id != {exclude_session_id}" if exclude_session_id else ""

    cur.execute(base_q.format(col="trainer_id", excl=excl), (date, str(end_td), str(start_td), trainer_id))
    if cur.fetchone():
        cur.close()
        return True, "trainer"

    cur.execute(base_q.format(col="batch_id", excl=excl), (date, str(end_td), str(start_td), batch_id))
    if cur.fetchone():
        cur.close()
        return True, "batch"

    cur.close()
    return False, ""


def _free_slots(date, trainer_id, batch_id, exclude_session_id=None) -> list[tuple]:
    return [(s, e) for s, e in VALID_SLOT_TD if
            not _is_slot_taken(date, s, e, trainer_id, batch_id, exclude_session_id)[0]]


def _pick_slot(date, trainer_id, batch_id, exclude_session_id=None) -> tuple | None:
    free = _free_slots(date, trainer_id, batch_id, exclude_session_id)
    print_all_slots(VALID_SLOT_TD, free)
    while True:
        raw = input("  Enter slot number: ").strip()
        if raw == "0": return None
        if not (raw.isdigit() and 1 <= int(raw) <= len(VALID_SLOT_TD)):
            err(f"Enter a number between 0 and {len(VALID_SLOT_TD)}.")
            continue
        chosen = VALID_SLOT_TD[int(raw) - 1]
        if chosen in free: return chosen
        print()
        err(f"Slot unavailable  --  {fmt_time(chosen[0])} - {fmt_time(chosen[1])} is already booked!")
        if not free:
            warn("No available slots remain for this date.")
            return None
        warn("Please choose from the available slots below:")
        print_free_slots(free)
        while True:
            raw2 = input("  Enter slot number (or 0 to cancel): ").strip()
            if raw2 == "0": return None
            if raw2.isdigit() and 1 <= int(raw2) <= len(free): return free[int(raw2) - 1]
            err(f"Enter a number between 0 and {len(free)}.")


def book_session(trainer: dict):
    banner("BOOK SESSION", width=30)
    batch_id = select_batch()
    if batch_id is None: return
    session_date = prompt_date("Session date (YYYY-MM-DD)")
    free = _free_slots(session_date, trainer["trainer_id"], batch_id)
    if not free:
        section("Time Slots")
        print_all_slots(VALID_SLOT_TD, [])
        err("All slots are fully booked for this trainer / batch on this date.")
        pause()
        return
    section("Select a Time Slot")
    chosen = _pick_slot(session_date, trainer["trainer_id"], batch_id)
    if chosen is None:
        info("Booking cancelled.")
        pause()
        return
    start_td, end_td = chosen
    conflict, reason = _is_slot_taken(session_date, start_td, end_td, trainer["trainer_id"], batch_id)
    if conflict:
        err(f"Slot unavailable -- {reason} conflict (concurrent booking).")
        pause()
        return
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO sessions (trainer_id, batch_id, session_date, start_time, end_time) VALUES (%s, %s, %s, %s, %s)",
            (trainer["trainer_id"], batch_id, session_date, str(start_td), str(end_td))
        )
        conn.commit()
        ok(f"Session booked successfully! (Session ID: {cur.lastrowid})")
        print_df(pd.DataFrame({"Field": ["Trainer", "Batch", "Date", "Time"],
                               "Value": [trainer["name"], get_batch_name(batch_id), str(session_date),
                                         f"{fmt_time(start_td)} - {fmt_time(end_td)}"]}))
    except Error as e:
        conn.rollback()
        err(f"Database error: {e}")
    finally:
        cur.close()
    pause()


def reschedule_session(trainer: dict):
    banner("RESCHEDULE SESSION", width=30)
    session_date = prompt_date_any("Session date to look up (YYYY-MM-DD)")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT s.session_id, b.batch_name, b.course, s.start_time, s.end_time FROM sessions s JOIN batches b ON s.batch_id = b.batch_id WHERE s.trainer_id = %s AND s.session_date = %s ORDER BY s.start_time",
        (trainer["trainer_id"], session_date)
    )
    sessions = cur.fetchall()
    cur.close()
    if not sessions:
        warn("No sessions found for that date.")
        pause()
        return
    section(f"Your Sessions on {session_date}")
    print_df(make_df(["Session ID", "Batch", "Course", "Start", "End"],
                     [[s[0], s[1], s[2], fmt_time(s[3]), fmt_time(s[4])] for s in sessions]))
    while True:
        raw = input("  Enter Session ID to reschedule (or 0 to cancel): ").strip()
        if raw == "0":
            info("Reschedule cancelled.")
            pause()
            return
        if raw.isdigit() and any(s[0] == int(raw) for s in sessions):
            match = next(s for s in sessions if s[0] == int(raw))
            break
        err("Invalid Session ID.")
    session_id, batch_name, course, old_start, old_end = match

    cur = conn.cursor()
    cur.execute("SELECT batch_id FROM sessions WHERE session_id = %s", (session_id,))
    batch_id = cur.fetchone()[0]
    cur.close()

    section("Select New Time Slot")
    chosen = _pick_slot(session_date, trainer["trainer_id"], batch_id, exclude_session_id=session_id)
    if chosen is None:
        info("Reschedule cancelled.")
        pause()
        return
    new_start, new_end = chosen
    conflict, reason = _is_slot_taken(session_date, new_start, new_end, trainer["trainer_id"], batch_id, session_id)
    if conflict:
        err(f"Slot unavailable -- {reason} conflict.")
        pause()
        return

    cur = conn.cursor()
    try:
        cur.execute("UPDATE sessions SET start_time = %s, end_time = %s WHERE session_id = %s",
                    (str(new_start), str(new_end), session_id))
        conn.commit()
        ok("Session rescheduled successfully!")
        print_df(pd.DataFrame({"": ["Old time", "New time"], "Time": [f"{fmt_time(old_start)} - {fmt_time(old_end)}",
                                                                      f"{fmt_time(new_start)} - {fmt_time(new_end)}"]}))
    except Error as e:
        conn.rollback()
        err(f"Database error: {e}")
    finally:
        cur.close()
    pause()


def view_daily_schedule(trainer: dict):
    banner("VIEW MY DAY", width=30)
    session_date = prompt_date_any("Date to view (YYYY-MM-DD)")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT s.session_id, b.batch_name, b.course, s.start_time, s.end_time FROM sessions s JOIN batches b ON s.batch_id = b.batch_id WHERE s.trainer_id = %s AND s.session_date = %s ORDER BY s.start_time",
        (trainer["trainer_id"], session_date)
    )
    sessions = cur.fetchall()
    cur.close()
    print(f"\n  Trainer : {trainer['name']}\n  Date    : {session_date}")
    if not sessions:
        warn("No sessions scheduled for this day.")
    else:
        print_df(make_df(["Session ID", "Start", "End", "Batch", "Course"],
                         [[s[0], fmt_time(s[3]), fmt_time(s[4]), s[1], s[2]] for s in sessions]))
        info(f"Total sessions: {len(sessions)}")
    pause()
