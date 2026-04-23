from db import initialise_schema, close_connection
from scheduler import (
    login, book_session, reschedule_session, view_daily_schedule, menu, banner
)

def main():
    banner("TRAINER SESSION SCHEDULER", width=50)
    print("  Initialising database...")
    initialise_schema()
    print("  Database ready.\n")

    trainer = login()
    if trainer is None:
        print("\n  Goodbye!\n")
        return

    try:
        while True:
            print(f"\n  Logged in as: {trainer['name']}  (ID: {trainer['trainer_id']})")
            choice = menu("Main Menu", [
                "Book a Session",
                "Reschedule a Session",
                "View My Day",
            ])

            if choice == 0:
                break
            elif choice == 1:
                book_session(trainer)
            elif choice == 2:
                reschedule_session(trainer)
            elif choice == 3:
                view_daily_schedule(trainer)

    except KeyboardInterrupt:
        print("\n\n  Interrupted. Goodbye!\n")
    finally:
        close_connection()

    print("\n  Goodbye!\n")

if __name__ == "__main__":
    main()
