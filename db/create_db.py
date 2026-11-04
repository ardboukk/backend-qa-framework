import sqlite3

db = sqlite3.connect("hotel.db")
db.executescript("""
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS guests;

CREATE TABLE guests (
    id    INTEGER PRIMARY KEY,
    name  TEXT,
    email TEXT
);

CREATE TABLE bookings (
    id          INTEGER PRIMARY KEY,
    guest_id    INTEGER,
    checkin     TEXT,
    checkout    TEXT,
    totalprice  REAL
);

CREATE TABLE payments (
    id          INTEGER PRIMARY KEY,
    booking_id  INTEGER,
    amount      REAL
);

INSERT INTO guests VALUES
  (1, 'Abed',  'abed@example.com'),
  (2, 'Sara',  'sara@example.com'),
  (3, 'Omar',  'omar@example.com'),
  (4, 'Lina',  'abed@example.com');

INSERT INTO bookings VALUES
  (101, 1, '2026-11-01', '2026-11-05', 400),
  (102, 2, '2026-11-03', '2026-11-04', 100),
  (103, 1, '2026-12-10', '2026-12-12', 200),
  (104, 9, '2026-11-20', '2026-11-22', 250),
  (105, 3, '2026-11-15', '2026-11-10', -100);

INSERT INTO payments VALUES
  (1, 101, 400),
  (2, 102, 100),
  (3, 103, 150),
  (4, 999, 80);
""")
db.commit()
print("hotel.db created")