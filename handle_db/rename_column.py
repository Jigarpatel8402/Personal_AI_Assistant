import sqlite3

connection = sqlite3.connect("C:\\Users\\JIGAR\\OneDrive\\Documents\\@Pycharm_WS\\NovaAI\\db\\database.db")
cursor = connection.cursor()

cursor.execute("""
    ALTER TABLE commands RENAME COLUMN action TO value
""")

connection.close()
print("renamed")
