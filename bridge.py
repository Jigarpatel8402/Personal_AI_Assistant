import webview
import socket
import threading
import time
import socket
import main
import queue
import ui_events
import config
priority = config.Priority()
print(priority.warning)
print(priority.critical)
print(priority.normal)

# bridge between AI and UI
class API:
    def __init__(self):
        self.ui = main.UI()
        self.running = False

    def start(self):
        if self.running:
            return
        self.running = True

    def stop(self):
        self.running = False

    # receive entered text in chat
    def receive_text(self, text):
        if text:
            return ui_events.ai_command_queue.put(f"Jarvis {text}")
        return None

    # add text in chat
    def print_text(self):
        messages = []
        try:
            while True:
                priority, text = ui_events.ui_command_queue.get_nowait()
                messages.append((priority, text))
        except queue.Empty:
            pass
        if not messages:
            return {"source": None, "messages": []}
        result = []
        for priority, msg in messages:
            if priority == 10:
                src = 'user'
            elif priority == 5:
                src = 'ai'
            else :
                src = 'warning'
            result.append({
                "source": src,
                "text": msg,
            })
        return {"messages": result}

    # start mic if requested
    def mic_start(self):
        ui_events.mic_command = True
        print("Mic started...")

    # stop mic if requested
    def mic_stop(self):
        ui_events.mic_command = False
        print("Mic stopped...")

# create UI window
class Window:
    def __init__(self, api: API):
        self.api = api
        self.window = None

    # monitor ui request
    def monitor_api(self):
        while ui_events.ui_monitor:
            if ui_events.ui_command and not ui_events.ui_running:
                ui_events.ui_running = True
                ui_events.mic_command = False
                self.api.start()
                self.window = webview.create_window(
                    "AI Assistant",
                    "gui/index.html",
                    width=500,
                    height=450,
                    js_api=api
                )
                webview.start(gui='edgechromium', debug=False)
                ui_events.ui_running = False
                ui_events.ui_command = False
                ui_events.mic_command = True
                print(f"Chat box closed")


if __name__ == "__main__":
    print("Starting...")
    ui_events.ui_monitor = True
    threading.Thread(target = main.start_main, daemon = True).start()
    api = API()
    window = Window(api)
    window.monitor_api()
