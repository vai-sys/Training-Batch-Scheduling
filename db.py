import sys
try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    print("[ERROR] mysql-connector-python is not installed.")
    sys.exit(1)

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "root",
    "database": "scheduler_db",
    "autocommit": False,
}

_connection = None

def get_connection():
    global _connection
    if _connection is None or not _connection.is_connected():
        try:
            init_cfg = {k: v for k, v in DB_CONFIG.items() if k != "database"}
            tmp = mysql.connector.connect(**init_cfg)
            cur = tmp.cursor()
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}`")
            cur.close()
            tmp.close()

            _connection = mysql.connector.connect(**DB_CONFIG)
            _connection.autocommit = False
        except Error as e:
            print(f"\n[DB ERROR] Could not connect to MySQL: {e}")
            sys.exit(1)
    return _connection

def initialise_schema():
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS trainers (
            trainer_id  INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(100) NOT NULL,
            email       VARCHAR(100) NOT NULL UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS batches (
            batch_id    INT AUTO_INCREMENT PRIMARY KEY,
            batch_name  VARCHAR(100) NOT NULL,
            course      VARCHAR(100) NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id   INT AUTO_INCREMENT PRIMARY KEY,
            trainer_id   INT  NOT NULL,
            batch_id     INT  NOT NULL,
            session_date DATE NOT NULL,
            start_time   TIME NOT NULL,
            end_time     TIME NOT NULL,
            FOREIGN KEY (trainer_id) REFERENCES trainers(trainer_id),
            FOREIGN KEY (batch_id)   REFERENCES batches(batch_id)
        )
    """)

    cur.execute("SELECT COUNT(*) FROM batches")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO batches (batch_name, course) VALUES
            ('Python Batch', 'Python'),
            ('Java Batch', 'Java'),
            ('DotNet Batch', 'DotNet')
        """)

    conn.commit()
    cur.close()

def close_connection():
    global _connection
    if _connection and _connection.is_connected():
        _connection.close()
        _connection = None
