import sqlite3

connection = sqlite3.connect("C:\\Users\\JIGAR\\OneDrive\\Documents\\@Pycharm_WS\\NovaAI\\db\\database.db")
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT NOT NULL UNIQUE,
    value INTEGER NOT NULL,
    spaces INTEGER NOT NULL
)
""")

# index for fast lookup (IMPORTANT)
cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_commands_spaces
ON commands (spaces);
""")

connection.commit()
connection.close()

print("commands table created")
