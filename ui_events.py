import queue

ui_command_queue = queue.PriorityQueue() # UI commands from AI
ui_command = False # open window
ui_running = False # ui is running or not
ui_monitor = False # starts ui_monitor in bridge at the stating of AI

ai_command_queue = queue.Queue() # AI command from UI
mic_command = True # mic command (False when window is running)
