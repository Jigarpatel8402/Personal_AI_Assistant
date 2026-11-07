import sqlite3

connection = sqlite3.connect("C:\\Users\\JIGAR\\OneDrive\\Documents\\@Pycharm_WS\\NovaAI\\db\\database.db")
cursor = connection.cursor()

cursor.execute("""
SELECT command, value, spaces
FROM commands
""")

rows = cursor.fetchall()
connection.close()

for row in rows:
    print(row)

print(f"Total rows: {len(rows)}")
