import json
from datetime import datetime, timedelta
from twc_modules.configuration import *
import requests
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from PyQt5 import QtCore, QtWidgets, QtGui
import sys
import base64
from uuid import getnode as get_mac
import os

twc_version = VERSION
timenow = datetime.utcnow()

class GetDataThread(QtCore.QThread):
    newValue = QtCore.pyqtSignal(str)
    addList = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        QtCore.QThread.__init__(self, parent)

    def __del__(self):
        self.wait()

    def get_heroku_last_seen(self):
        self.newValue.emit("Getting Heroku data...")
        url = "http://releng-hardware.herokuapp.com/machines"
        headers = {"user-agent": "ciduty-twc/{}".format(twc_version)}
        data = json.loads(requests.get(url, headers=headers).text)
        heroku_machines = {}
        for value in data:
            idle = timenow - datetime.strptime(value["lastseen"], "%Y-%m-%dT%H:%M:%S.%f")
            _idle = int(idle.total_seconds())
            heroku_machines.update({value["machine"].lower(): {"lastseen": value["lastseen"], "idle": _idle,
                                                               "datacenter": value["datacenter"]}})
        save_json("heroku_dict.json", heroku_machines)
        return heroku_machines

    def get_google_spreadsheet_data(self):
        self.newValue.emit("Getting Google spreadsheet data...")
        # Define READONLY scopes needed for the CLI
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly",
                  "https://www.googleapis.com/auth/drive.readonly"]
        # Setup Credentials
        ENV_CREDS = "ciduty-twc.json"
        login_info = ServiceAccountCredentials.from_json_keyfile_name(ENV_CREDS, scopes)
        # Authenticate / Login
        auth_token = gspread.authorize(login_info)
        # Choose which sheets from the SpreadSheet we will work with.
        moonshots_sheet_mdc1 = auth_token.open("Moonshot Master Inventory").worksheet("MDC_1")
        moonshots_sheet_mdc2 = auth_token.open("Moonshot Master Inventory").worksheet("MDC_2")
        osx_sheet_all_mdc = auth_token.open("Moonshot Master Inventory").worksheet("OSX")
        # Read the Data from the sheets
        moonshots_mdc1 = moonshots_sheet_mdc1.get_all_records()
        moonshots_mdc2 = moonshots_sheet_mdc2.get_all_records()
        osx_all_mdc = osx_sheet_all_mdc.get_all_records()
        # Construct dictionaries with all data that we need.
        moonshots_google_data_mdc1 = {entry["Hostname"]:
            {
                "prefix": entry["Hostname prefix"],
                "chassis": entry["Chassis"],
                "serial": entry["Cartridge Serial"],
                "cartridge": entry["Cartridge #"],
                "ilo": entry["ilo ip:port"],
                "owner": entry["Ownership"],
                "reason": entry["Ownership Reason"],
                "notes": entry["NOTES"],
                "ignore": entry["CiDuty CLI Ignore"]
            } for entry in moonshots_mdc1}
        moonshots_google_data_mdc2 = {entry["Hostname"]:
            {
                "prefix": entry["Hostname prefix"],
                "chassis": entry["Chassis"],
                "serial": entry["Cartridge Serial"],
                "cartridge": entry["Cartridge #"],
                "ilo": entry["ilo ip:port"],
                "owner": entry["Ownership"],
                "reason": entry["Ownership Reason"],
                "notes": entry["NOTES"],
                "ignore": entry["CiDuty CLI Ignore"]
            } for entry in moonshots_mdc2}
        osx_google_data = {entry["Hostname"]:
            {
                "serial": entry["Serial"],
                "warranty": entry["Warranty End Date"],
                "owner": entry["Ownership"],
                "reason": entry["Ownership Reason"],
                "notes": entry["Notes"],
                "ignore": entry["CiDuty CLI Ignore"]
            } for entry in osx_all_mdc}
        all_google_machine_data = {**moonshots_google_data_mdc1, **moonshots_google_data_mdc2, **osx_google_data}
        save_json('google_dict.json', all_google_machine_data)
        return all_google_machine_data

    def add_idle_to_google_dict(self):
        self.newValue.emit("Adding 'idle' to google dict data...")
        heroku_data = open_json("heroku_dict.json")
        google_data = open_json("google_dict.json")
        shared_keys = set(heroku_data).intersection(google_data)
        for key in shared_keys:
            machine_idle = {"idle": heroku_data.get(key)["idle"]}
            google_data[key].update(machine_idle)
        save_json("google_dict.json", google_data)

    def run(self):
        self.get_heroku_last_seen()
        self.get_google_spreadsheet_data()
        self.add_idle_to_google_dict()
        self.newValue.emit("Done importing new data.")
        self.addList.emit()
        self.finished.emit()


class Machine(QtCore.QObject):
    def __init__(self, hostname):
        QtCore.QObject.__init__(self)
        if hostname == "":
            self.hostname = "NoName"
        else:
            self.hostname = hostname
        self.ignore = ""
        self.notes = ""
        self.serial = ""
        self.owner = ""
        self.reason = ""
        self.idle = ""
        self.ilo = ""

    def __repr__(self):
        return "Hostname: {},Ignore: {},Notes: {},SN: {},Owner: {},Reason: {},Idle: {},Ilo: {}".format(self.hostname,
                                                                                                       self.ignore,
                                                                                                       self.notes,
                                                                                                       self.serial,
                                                                                                       self.owner,
                                                                                                       self.reason,
                                                                                                       self.idle,
                                                                                                       self.ilo)

    def insert_data(self, ignore, notes, serial, owner, reason, ilo):
        if ignore == "":
            self.ignore = "N/A"
        else:
            self.ignore = ignore
        if notes == "":
            self.notes = "N/A"
        else:
            self.notes = notes
        if serial == "":
            self.serial = "N/A"
        else:
            self.serial = serial
        if owner == "":
            self.owner = "N/A"
        else:
            self.owner = owner
        if reason == "":
            self.reason = "N/A"
        else:
            self.reason = reason
        if self.get_idle(self.hostname) is None:
            self.idle = 1
        else:
            self.idle = self.get_idle(self.hostname)
        self.ilo = ilo

    def get_idle(self, name):
        idle_data = open_json("heroku_dict.json")
        for member in idle_data:
            if str(name).partition('.')[0] == member:
                return idle_data.get(member)["idle"]
                break


class Cryptograph(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.mac_addr = str(get_mac())

    def encode(self, key, clear):
        """Encode a string based on a key, in this case mac address"""
        enc = []
        for i in range(len(clear)):
            self.mac_addr_c = self.mac_addr[i % len(self.mac_addr)]
            enc_c = chr((ord(clear[i]) + ord(self.mac_addr_c)) % 256)
            enc.append(enc_c)
        return base64.urlsafe_b64encode("".join(enc).encode()).decode()

    def decode(self, key, enc):
        """Decode a string based on a key, in this case mac address"""
        dec = []
        enc = base64.urlsafe_b64decode(enc).decode()
        for i in range(len(enc)):
            self.mac_addr_c = self.mac_addr[i % len(self.mac_addr)]
            dec_c = chr((256 + ord(enc[i]) - ord(self.mac_addr_c)) % 256)
            dec.append(dec_c)
        return "".join(dec)

    def encoding(self, value):
        """Returns encoded string"""
        return self.encode(str(self.mac_addr),value)

    def decoding(self, value):
        """Returns decoded string"""
        return self.decode(str(self.mac_addr), value)


class Settings(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.type = type
        self.filename = 'settings.json'
        self.json_create()

    def get_property(self, type, search):
        data = self.get_data_json()
        for member in data[type]:
            if search in member['name']:
                return member
                break
        else:
            return {"active": "No", "name": "", "value": "/path/to/file"}

    def get_data_json(self):
        with open(self.filename, 'r') as f:
            data = json.load(f)
        return data

    def set_data_json(self, data):
        with open(self.filename, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)
        f.close()

    def is_json(self):
        """Check if json properties files exist"""
        return os.path.isfile(self.filename)

    def json_create(self):
        """If no json file present, create one time only"""
        if self.is_json() is False:
            data = {'ui_properties':[{
                    'name': '',
                    'active': "No",
                    'value': ''}],
                    'theme': {
                        'type': '',
                        'code': 1
                    },
                    'backend':[{
                        'name': '',
                        'active': "No",
                        'value': ''}
                    ]}
            with open(self.filename, 'w') as f:
                json.dump(data, f, indent=2, sort_keys=True)
        else:
            pass


class UiProperties(Settings):
    def __init__(self, name, value, active):
        Settings.__init__(self)
        self.name = name
        self.value = value
        self.active = active

    def update_property(self):
        data = self.get_data_json()
        for member in data['ui_properties']:
            if self.name == member['name']:
                data['ui_properties'][data['ui_properties'].index(member)]['value'] = self.value
                data['ui_properties'][data['ui_properties'].index(member)]['active'] = self.active
                self.set_data_json(data)
                break
        else:
            self.add_property()

    def add_property(self):
        data = self.get_data_json()
        _property = {'name': self.name,
                     'active': self.active,
                     'value': self.value}
        data['ui_properties'].append(_property)
        self.set_data_json(data)


class BackendProperties(Settings):
    def __init__(self, name, value, active):
        Settings.__init__(self)
        self.name = name
        self.value = value
        self.active = active

    def update_property(self):
        data = self.get_data_json()
        for member in data['backend']:
            if self.name in member['name']:
                data['backend'][data['backend'].index(member)]['value'] = self.value
                data['backend'][data['backend'].index(member)]['active'] = self.active
                self.set_data_json(data)
                break
        else:
            self.add_property()

    def add_property(self):
        data = self.get_data_json()
        _property = {'name': self.name,
            'active': self.active,
            'value': self.value}
        data['backend'].append(_property)
        self.set_data_json(data)


class ThemeSet(Settings):
    def __init__(self, code, type):
        Settings.__init__(self)
        self.code = code
        self.type = type

    def update_theme(self):
        data = self.get_data_json()
        data['theme']['code'] = self.code
        data['theme']['type'] = self.type
        self.set_data_json(data)


class TrayIcon(QtWidgets.QSystemTrayIcon):
    def __init__(self):
        QtWidgets.QSystemTrayIcon.__init__(self)
        self.tray = QtWidgets.QSystemTrayIcon()
        icon = QtGui.QIcon("DevOps-Gear.png")
        self.tray.setIcon(icon)
        menu = QtWidgets.QMenu()
        exit_action = menu.addAction("Exit")
        settings_action = menu.addAction("Settings")
        self.tray.setContextMenu(menu)
        exit_action.triggered.connect(sys.exit)
        # settings_action.triggered.connect(self.run_settings)
        self.tray.show()

    def messageInfo(self, title, line, option):
        """System tray messageInfo system showing Informative icon and Informative level"""
        if Settings().get_property('ui_properties', 'Notifier')['value']:
            if option == 1:
                self.tray.showMessage(title, line, QtWidgets.QSystemTrayIcon.Information)
        else:
            pass
        if option == 0:
            QtWidgets.QMessageBox.information(None, title, line, QtWidgets.QMessageBox.Yes)

    def messageWarning(self, title, line, option):
        """System tray messageInfo system showing Warning icon and Warning level"""
        if Settings().get_property('ui_properties', 'Notifier')['value']:
            if option == 1:
                self.tray.showMessage(title, line, QtWidgets.QSystemTrayIcon.Warning)
        else:
            pass
        if option == 0:
            QtWidgets.QMessageBox.warning(None, title, line, QtWidgets.QMessageBox.Yes)

    def messageCritical(self, title, line, option):
        """System tray messageInfo system showing Critical icon and Critical level"""
        if Settings().get_property('ui_properties', 'Notifier')['value']:
            if option == 1:
                self.tray.showMessage(title, line, QtWidgets.QSystemTrayIcon.Critical)
        else:
            pass
        if option == 0:
            QtWidgets.QMessageBox.critical(None, title, line, QtWidgets.QMessageBox.Yes)


def open_json(file_name):
    try:
        with open("json_data/{}".format(file_name)) as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        TrayIcon().messageWarning("Error", "Data files not found. Please import data to create the work files.", 0)
        return {}

def save_json(file_name, data):
    with open("json_data/{}".format(file_name), 'w') as f:
        json.dump(data, f, indent=2, sort_keys=True)
    f.close()

def remove_fqdn_from_machine_name(hostname):
    if len(hostname) > 1:
        if "t-linux64-ms-" in hostname:
            return hostname[:16]
        elif "t-w1064-ms-" in hostname:
            return hostname[:14]
        else:
            return hostname[:17]

def save_logs(intext):
    with open("taskcluster.log", 'a') as f:
        f.write(intext)
    f.close()
    TrayIcon().messageInfo("Log Info.", "Log file saved.", 1)