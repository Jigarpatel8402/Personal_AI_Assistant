import os
import sys
import platform
import queue
import numpy as np
import subprocess
import socket # internet availability
import speech_recognition as sr # detect speech and recognize
import openai
import wikipedia
import webbrowser # open webbrowser
import win32com.client  # speaking command
import pythoncom # handle AI speaking
import tempfile
# import pygame # audio with piper
from piper.voice import PiperVoice # piper voice
from piper.config import SynthesisConfig # piper voice config
import sounddevice as sd    # sound device
import pyaudio
import pyautogui  # pressing keys and typing
import json # read json files
from datetime import datetime # read date and time
import time # time
import re # split string with multi operator
import serial # serial ports and communication
import serial.tools.list_ports # serial ports list
import psutil # Battery Information
import threading # open threading
from queue import PriorityQueue # handles priority queue
from queue import Queue # handle simple queue
from pyttsx3 import speak
from db import read_db # handle the dada base
from robotics.robo import ESPPort # robotics methods
import ui_events
import config
from ui_events import ai_command_queue

# from llm_helper import ask_local_llm # LLM Helper
# _ = ask_local_llm("Hello")
# print("Model Ready!")
AI_name = config.AI_name
priority = config.Priority()

speech_queue = PriorityQueue()

exit_event = threading.Event()

with open("db\\memory.json", "r") as file:    # todo: replace full .json file with SQLite
    data = json.load(file)
keymaps = data["keymaps"]
confirm_commands = set(data["confirm_commands"])
cancel_commands = set(data["cancel_commands"])
esp_commands = data["esp_commands"]

# Extract any command from the database tables
def extract_target(query, data_name, category=None):
    words = query.split()
    n = len(words)
    for spaces in range(n - 1, -1, -1):
        data_dict = read_db.get_data_by_spaces(data_name, spaces, category)
        size = spaces + 1
        for i in range(n - size + 1):
            phrase = " ".join(words[i:i + size])
            if phrase in data_dict:
                value = data_dict[phrase][0]
                category = data_dict[phrase][1]
                extra = query.replace(f"{phrase} ", "").strip()
                return phrase, value, extra, category
    return None, None, None, None

# def binary_search(items, target, low, high):
#     while low <= high:
#         mid = (low + high) // 2
#         name = items[mid]["name"]
#         if name == target:
#             return items[mid]
#         elif target < name:
#             return binary_search(items, target, low, mid - 1)
#         else:
#             return binary_search(items, target, mid + 1, high)
#     return None

### Internet Availability
class InternetConnection:
    def __init__(self):
        self.running = False
        self.Internet_Available = True
        self.Threading = None
        self.Threading =  None

    def start(self):
        if self.running:
            return
        self.running = True
        self.Threading = threading.Thread(target = self.network_checker, daemon = False)
        self.Threading.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.Threading and self.Threading.is_alive():
            self.Threading.join(timeout = 1)
        self.Threading = None
        return

    def network_checker(self):
        while self.running:
            self.is_internet_available()
            time.sleep(1)

    def is_internet_available(self, timeout = 2):
        try :
            socket.create_connection(("8.8.8.8", 53), timeout)
            self.Internet_Available = True
            return True
        except OSError:
            self.Internet_Available = False
            return False

### Handle GUI
class UI:
    def print_query(self, priority, query):
        if query:
            ui_events.ui_command_queue.put((priority, query))
        return

    def get_query(self):
            return ui_events.ai_command_queue.get(timeout = 0.3)

### Speaker Service
class SpeakerService:
    def __init__(self, ui: UI):
        self.ui = ui
        self.running = False
        self.queue = PriorityQueue()
        self.speech_done = threading.Event()
        self.speech_done.set()
        self.can_listen = threading.Event()
        self.can_listen.set()
        self.speaker = None
        self.speaker_threading = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.speaker_threading = threading.Thread(target = self.speak_worker, daemon = False)
        self.speaker_threading.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.queue.put((10, None))
        if self.speaker_threading and self.speaker_threading.is_alive():
            self.speaker_threading.join(timeout = 1)
        self.speaker_threading = None
        return

    def say(self, priority, text):
        self.speech_done.clear()
        self.queue.put((priority, text))
        self.speech_done.wait()

    # def speak_worker(self):
    #     pythoncom.CoInitialize()
    #     self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
    #     while self.running:
    #         p, text = self.queue.get()
    #         if not text:
    #             return
    #         if ui_events.ui_command:
    #             self.ui.print_query(p, text)
    #         else :
    #             self.speaker.speak(text)
    #         self.speech_done.set()
    
    def speak_worker(self):
        voice = PiperVoice.load("voices/en_US-amy-medium.onnx")
        syn_config = SynthesisConfig(
            length_scale=0.75,
            noise_scale=0.667,
            noise_w_scale=0.8
        )
        while self.running: 
            p, text = self.queue.get()
            if not text:
                return
            if ui_events.ui_command:
                self.ui.print_query(p, text)
            else :
                audio = bytearray()
                # print("TTS TEXT:", repr(text))
                for chunk in voice.synthesize(
                    text,
                    syn_config=syn_config
                ):
                    audio.extend(chunk.audio_int16_bytes)
                audio_np = np.frombuffer(
                    audio,
                    dtype=np.int16
                )
                sd.play(
                    audio_np,
                    samplerate=22050
                )
                sd.wait()
            self.speech_done.set()


### Robotics Integration
class RoboticsIntegration:
    def __init__(self, speaker: SpeakerService):
        self.speaker = speaker
        # self.net = net
        # self.ui = ui
        self.ESP = ESPPort()
        self.ESP_baud = 115200

    def start(self):
        self.ESP.start()

    def stop(self):
        self.ESP.stop()

    def send_to_esp(self, value: int):
        ESP_port  = self.ESP.get_active_port()
        if not ESP_port:
            return False
        try:
            with serial.Serial(ESP_port, self.ESP_baud, timeout = 1) as esp:
                time.sleep(1)
                esp.write(f"{value}\n".encode())
                return True
        except serial.SerialException as e:
            print(e)
            return False

    def handle_command(self, query):
        if not self.ESP.scanned:
            self.speaker.say(priority.warning, "Wait for port scanning sir...")
            while not self.ESP.scanned:
                time.sleep(1)
        if not bool(self.ESP.esp_ports):
            self.speaker.say(priority.warning, "ESP not found sir...")
            return False
        phrase, value, extra, category = extract_target(query, "robotics_commands")
        self.speaker.say(priority.warning, f"Sending {value} sir...")
        status = self.send_to_esp(value)
        if status:
            return True
        else :
            self.speaker.say(priority.warning, "Failed to send command sir...")
            return False

### System Monitor
class SystemMonitor:
    def __init__(self, speaker: SpeakerService):
        self.speaker = speaker
        self.running  = False
        self.Thread = None
        self.last_warning_level = None
        self.percent = None
        self.count = 0

    def start(self):
        if self.running:
            return
        self.running = True
        self.Thread = threading.Thread(target = self.monitor_loop, daemon = False)
        self.Thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.Thread and self.Thread.is_alive():
            self.Thread.join(timeout = 1)
        self.Thread = None
        return

    def monitor_loop(self, interval = 60):
        while self.running:
            self.battery_check()
            for _ in range(interval):
                if not self.running:
                    return
                time.sleep(1)

    # converts seconds into minutes and hours
    def formate_time(self, seconds):
        if seconds in (psutil.POWER_TIME_UNKNOWN, psutil.POWER_TIME_UNLIMITED, None):
            return None
        minutes = seconds // 60
        hours = minutes // 60
        minutes = minutes % 60
        if hours > 0:
            print(f"{hours} hours, {minutes} minutes")
            return f"{hours} hours, {minutes} minutes"
        print(f"{minutes} minutes")
        return f"{minutes} minutes"

    # get battery status
    def get_battery_status(self):
        battery = psutil.sensors_battery()
        if battery is None:
            return None
        return (
            battery.percent,
            battery.power_plugged,
            battery.secsleft
        )

    # hibernate the system
    def hibernate_system(self):
        system = platform.system()
        if system == "Windows":
            os.system("shutdown /h")
        else :
            self.speaker.say(
                priority.critical,
                "Automatic hibernation is not supported on this system."
            )

    # checks battery
    def battery_check(self, low = 25, critical = 15, very_low = 5):
        status = self.get_battery_status()
        if status is None:
            return
        percent, plugged, secsleft = status
        time_text = self.formate_time(secsleft)
        if plugged:
            self.last_warning_level = None
            return
        if percent <= very_low and self.last_warning_level != "hibernate":
            self.last_warning_level = "hibernate"
            msg = f"Battery at extremely low level. at {percent} percent. "
            msg += "Your system will hibernated in only five seconds."
            self.speaker.say(priority.critical, msg)
            time.sleep(10)
            self.hibernate_system()
            return
        if percent <= critical and self.last_warning_level not in ("critical", "hibernate"):
            self.last_warning_level = "critical"
            msg = f"Battery at critical level. {percent} percent. "
            if time_text:
                msg += f"{time_text} remaining."
            self.speaker.say(priority.warning, msg)
            return
        elif percent <= low and self.last_warning_level not in ("low", "critical", "hibernate"):
            self.last_warning_level = "low"
            msg = f"Battery at low level. at {percent} percent. "
            if time_text:
                msg += f"{time_text} remaining."
            self.speaker.say(priority.warning, msg)
            return

## AI Assistant
class AIAssistant:
    def __init__(self,
                 speaker: SpeakerService,
                 robot: RoboticsIntegration,
                 net: InternetConnection,
                 ui: UI,
                 system: SystemMonitor):
        self.speaker = speaker
        self.robot = robot
        self.net = net
        self.ui = ui
        self.system = system
        self.recognizer = sr.Recognizer()
        self.data = read_db.tables

        ### Handle Action Map dictionary
        self.ACTION_MAP = {
            "open_query": self.open_query,
            "repeat": self.repeat,
            "submit": self.submit,
            "typing": self.typing,
            "timeDayDate": self.timeDayDate,
            "tell_name": self.tell_name,
            "pressing": self.pressing,
            "close_query": self.close_query,
            "restart": self.restart,
            "power_query": self.power_query,
            "robotics_command": self.robot.handle_command,
            "open_chatbox": self.open_chatbox,
            "close_chatbox": self.close_chatbox
        }

    ### Start AI Assistant
    def run_AI(self):
        print(f"Hello, I am {AI_name} AI.")
        self.speaker.say(0, f"Hello, I am {AI_name} AI.")
        while True:
            if not ui_events.ui_command and not self.net.Internet_Available:
                self.speaker.say(priority.warning, f"Internet is not available sir...")
                ans = input("Do you want to open ChatBox or want to exit? : ")
                if ans == "exit":
                    self.exit_AI()
                    break
                elif ans in confirm_commands:
                    self.speaker.say(priority.normal, f"opening chat box sir...")
                    ui_events.ui_command = True
                else :
                    continue
            # if ui_events.ui_command and self.net.Internet_Available:                      # todo: modify this block
            #     self.speaker.say(priority.normal,
            #                      f"Internet is available sir... Do you want to close the chatbox?")
            #     print("ui_events.ui_command: ", ui_events.ui_command)
            #     try :
            #         ans = self.ui.get_query()
            #     except queue.Empty as e:
            #         continue
            #     if ans == "exit":
            #         self.exit_AI()
            #         break
            #     elif ans in confirm_commands:
            #         self.speaker.say(priority.normal, "closing chat box sir...")
            #         ui_events.ui_command = False
            #     else :
            #         continue
            if ui_events.mic_command:
                query = self.takeCommand()
                if query and ui_events.ui_command:
                    self.ui.print_query(10, query)
                    time.sleep(0.5)
            else :
                try:
                    query = self.ui.get_query()
                    print(f"User said: {query}")
                except queue.Empty:
                    continue
            if not query:
                continue
            self.run_commands(query.lower())

    def exit_AI(self):
        self.speaker.say(priority.normal, f"Exiting {AI_name} AI.")
        ui_events.ui_command = False
        ui_events.ui_monitor = False
        self.robot.stop()
        self.system.stop()
        self.net.stop()
        self.speaker.stop()
        exit_event.set()
        sys.exit(0)

    ## Take Commands
    def takeCommand(self, timeout = None, phrase_time_limit=None):
        self.speaker.can_listen.wait()
        with sr.Microphone() as source:
            self.recognizer.pause_threshold = 0.5
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                query = self.recognizer.recognize_google(audio, language="en-IN")
                print(f"User said: {query}")
                return query
            except sr.WaitTimeoutError:
                return None
            except Exception as e:
                return None

    def run_commands(self, query):
        if f"{AI_name} exit".lower() in query:
            self.exit_AI()
            return None
        if self.wakeupCall(query):
            query = self.removeStr(query, AI_name.lower())
            if not query:
                return None
            phrase, action, extra, category = extract_target(query, "commands")
            if action:
                return self.ACTION_MAP[action](extra)
            else:
                # reply = ask_local_llm(query)
                # self.speaker.say(priority.normal, reply)
                return self.speaker.say(priority.normal, "Sorry, I didn't get it.")
        return None

    def wakeupCall(self, query):
        return AI_name.lower() == query.split()[0]

    def tell_name(self, query):
        self.speaker.say(priority.normal, f"My name is Jarvis, an AI.")

    def removeStr(self, query, string):
        return query[len(string):].strip()

    def repeat(self, query):
        self.speaker.say(priority.normal, f"Repeating sir..., {query}")

    ### Open (Apps/Sites) Query
    def open_query(self, query):
        phrase, value, extra, category = extract_target(query, "open_targets")
        if category == "sites":
            self.speaker.say(priority.normal, f"Opening {phrase} sir...")
            webbrowser.open_new_tab(value)
        elif category == "desktop_apps":
            self.speaker.say(priority.normal, f"Opening {phrase} sir...")
            os.startfile(value)
        elif category == "store_apps":
            self.speaker.say(priority.normal, f"Opening {phrase} sir...")
            subprocess.Popen(f'explorer shell:AppsFolder\\{value}', shell=True)
        else:
            self.speaker.say(priority.normal, f"{query} not found sir...")

    def open_chatbox(self, query):
        self.speaker.say(priority.normal, f"Opening chat box sir...")
        ui_events.ui_command = True
        return

    def close_chatbox(self, query):
        self.speaker.say(priority.normal, f"Closing chat box sir...")
        ui_events.ui_command = False
        return

    ### Typing Query
    def typing(self, query):
        self.speaker.say(priority.normal, f"Typing {query}")
        time.sleep(1)
        pyautogui.write(query.capitalize(), interval=0.05)

    ### Date and Time Query
    def timeDayDate(self, query):
        now = datetime.now()
        if "Time".lower() in query:
            time_12 = now.strftime("%I:%M %p")
            self.speaker.say(priority.normal, f"It's {time_12}")
        elif "Date".lower() in query:
            date = now.strftime("%d %B %Y")
            self.speaker.say(priority.normal, f"Today is {date}")
        else:
            day = now.strftime("%A")
            self.speaker.say(priority.normal, f"Today is {day}")

    ### Submit Query
    def submit(self, query):
        self.speaker.say(priority.normal, "Submitting sir...")
        time.sleep(1)
        pyautogui.press("enter")

    ### Site Close Query
    def close_query(self, query):
        if "The site".lower() in query:
            self.speaker.say(priority.normal, "Closing site sir...")
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "w")
        else:
            self.speaker.say(priority.normal, "Close not found sir...")

    ### Restart AI
    def restart(self, query):
        self.speaker.say(priority.normal, "Restarting sir...")
        time.sleep(0.5)
        pyautogui.hotkey("shift", "f10")

    ### Pressing Keys
    def pressing(self, query):
        parts = re.split(r" plus | \+ ", query)
        time.sleep(1)
        keys = []
        for part in parts:
            if part in keymaps:
                keys.append(keymaps[part])
            else:
                self.speaker.say(priority.normal, "Sorry, key not found.")
                return
        self.speaker.say(priority.normal, f"Pressing {query}")
        pyautogui.hotkey(*keys)

    ## Handle Power Queries
    def confirmWithTimeOut(self, timeout=5):
        end_time = time.time() + timeout
        while time.time() < end_time:
            response = self.takeCommand(timeout=10, phrase_time_limit=2)
            if not response:
                continue
            response = response.lower().strip()
            if any(word in response for word in cancel_commands):
                return False
            elif any(word in response for word in confirm_commands):
                return True
            else:
                self.speaker.say(priority.normal, "Request cancelled sir...")
                return self.run_commands(response)
        self.speaker.say(priority.normal, "No response, request cancelled sir...")
        return False

    def power_query(self, query):
        phrase, value, extra, category = extract_target(query, "power_commands")
        self.speaker.say(priority.normal, f"Are you sure you want to {phrase} the PC?")
        confirmation = self.confirmWithTimeOut()
        if not confirmation:
            self.speaker.say(priority.normal, "Request cancelled sir...")
            return
        elif confirmation:
            self.speaker.say(priority.normal, "Conformed sir...")
            time.sleep(0.5)
            os.system(value)
            return
        else:
            return

# todo: add mobile phone control

# todo: add the AI into my mobile and something new gadget

def start_main():
    net = InternetConnection()
    net.start()
    ui = UI()
    speaker = SpeakerService(ui)
    speaker.start()
    robot = RoboticsIntegration(speaker)
    robot.start()
    system = SystemMonitor(speaker)
    system.start()
    assistant = AIAssistant(
        speaker, 
        robot, 
        net, 
        ui, 
        system
    )

    threading.Thread(target=assistant.run_AI, daemon = True).start()

    while not exit_event.is_set():
        time.sleep(1)

    # print(f"Alive threads: threading.enumerate()")
    print("Exiting...")

start_main()
