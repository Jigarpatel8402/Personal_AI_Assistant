import json
import sqlite3

# with open("C:\\Users\\JIGAR\\OneDrive\\Documents\\@Pycharm_WS\\NovaAI\\db\\memory.json", "r") as file:
#     data = json.load(file)

connection = sqlite3.connect("C:\\Users\\JIGAR\\OneDrive\\Documents\\@Pycharm_WS\\NovaAI\\db\\database.db")
cursor = connection.cursor()


# for command, value in data["commands"].items():
#     spaces = command.count(" ")
#     cursor.execute(
#         """
#         INSERT INTO commands (command, value, spaces)
#         VALUES (?, ?, ?)
#         """,
#         (command, value, spaces)
#     )

cursor.execute(
        """
        INSERT INTO commands (id, command, value, spaces)
        VALUES (?, ?, ?, ?)
        """,
        (1, "close", "close_query", 0)
    )

connection.commit()
connection.close()

print("All targets imported successfully")
