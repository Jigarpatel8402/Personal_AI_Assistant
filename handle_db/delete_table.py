import sqlite3

connection = sqlite3.connect("C:\\Users\\JIGAR\\OneDrive\\Documents\\@Pycharm_WS\\NovaAI\\db\\database.db")
cursor = connection.cursor()

cursor.execute("DROP TABLE IF EXISTS commands")

connection.commit()
connection.close()
print("deleted")
