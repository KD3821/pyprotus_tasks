import sqlite3


conn = sqlite3.connect('backend.db')

cursor = conn.cursor()

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS client_scores
    ([client_id] INTEGER PRIMARY KEY, [score] REAL)
    """
)

cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS client_interests
    ([client_id] INTEGER PRIMARY KEY, [travel] INTEGER, [hi-tech] INTEGER, [sport] INTEGER, [music] INTEGER)
    """
)

score_values = [
    (1, 3.4),
    (2, 4.0),
    (3, 5.0),
    (4, 2.7),
    (5, 3.9)
]

interests_values = [
    (1, 0, 1, 1, 0),
    (2, 1, 0, 1, 0),
    (3, 0, 1, 0, 1),
    (4, 1, 1, 0, 0),
    (5, 0, 0, 1, 1)
]

cursor.executemany("INSERT INTO client_scores VALUES (?, ?)", score_values)
cursor.executemany("INSERT INTO client_interests VALUES (?, ?, ?, ?, ?)", interests_values)

conn.commit()
conn.close()
