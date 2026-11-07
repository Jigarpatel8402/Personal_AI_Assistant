import sqlite3

db_path = "db\\database.db"

tables = {"commands", "open_targets", "robotics_commands", "power_commands"}

def get_data_by_spaces(data_name, spaces = None, category = None):
    if data_name not in tables:
        return ValueError("Invalid data_name")

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    if spaces is not None:
        if data_name != "open_targets":
            query = f"SELECT command, value FROM {data_name} WHERE spaces = ?"
            cursor.execute(query, (spaces, ))
            rows = {command: (value, None) for command, value in cursor.fetchall()}
        else :
            if category is not None:
                queue = f"SELECT command, value, category FROM {data_name} WHERE spaces = ? AND category = ?"
                cursor.execute(queue, (spaces, category))
            else :
                query = f"SELECT command, value, category FROM {data_name} WHERE spaces = ?"
                cursor.execute(query, (spaces, ))
            rows = {command: (value, category) for command, value, category in cursor.fetchall()}
    else :
        if data_name != "open_targets":
            query = f"SELECT command, value FROM {data_name}"
            cursor.execute(query)
            rows = {command: (value, None) for command, value in cursor.fetchall()}
        else :
            if category is not None:
                queue = f"SELECT command, value, category FROM {data_name} WHERE category = ?"
                cursor.execute(queue, (category,))
            else:
                query = f"SELECT command, value, category FROM {data_name}"
                cursor.execute(query)
            rows = {command: (value, category) for command, value, category in cursor.fetchall()}

    connection.close()
    return rows

if __name__ == "__main__":
    data = get_data_by_spaces("commands")
    print(data)
    print(f"Total results: {len(data)}")
