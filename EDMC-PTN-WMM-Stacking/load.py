import datetime
import glob
import math
import json
import logging
import os
import tkinter as tk
from pathlib import Path
from typing import Optional, Any

from theme import theme
import myNotebook as nb
from config import config, appname
from journal_lock import JournalLock
from dataclasses import dataclass, field


# Logger per found plugin, so the folder name is included in
# the logging format.
plugin_name = Path(__file__).resolve().parent.name
logger = logging.getLogger(f'{appname}.{plugin_name}')
if not logger.hasHandlers():
    level = logging.INFO  # So logger.info(...) is equivalent to print()
    logger.setLevel(level)
    logger_channel = logging.StreamHandler()
    logger_channel.setLevel(level)
    logger_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d:%(funcName)s: %(message)s')  # noqa: E501
    logger_formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
    logger_formatter.default_msec_format = '%s.%03d'
    logger_channel.setFormatter(logger_formatter)
    logger.addHandler(logger_channel)

first_event: bool = True
parent_frame: Optional[tk.Frame]
this_frame: Optional[tk.Frame] = None
hauling_widget = Optional[tk.Label]
advert_widget = Optional[tk.Label]
advert_btn = Optional[tk.Button]

class CargoMissionDeliveryUpdate:
    # MissionID: int
    # event: str
    # UpdateType: str
    # timestamp: datetime.datetime
    # CargoType: str
    # Count: int
    # StartMarketID: int
    # EndMarketID: int
    # ItemsCollected: int
    # ItemsDelivered: int
    # TotalItemsToDeliver: int
    # Progress: float

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        required_fields = [
            "Count",
            "MissionID",
            "event",
            "timestamp",
            "UpdateType",
            "CargoType",
            "StartMarketID",
            "EndMarketID",
            "ItemsCollected",
            "ItemsDelivered",
            "TotalItemsToDeliver",
            "Progress",
        ]
        missing_required_fields = [k for k in required_fields if k not in kwargs]
        if len(missing_required_fields) > 0:
            raise ValueError(f"Required fields missing: {missing_required_fields}")

        dt_fields = ["timestamp", "Expiry"]
        for k, v in kwargs.items():
            if isinstance(v, str) and k in dt_fields:
                v = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%SZ')
            setattr(self, k, v)


class MissionAccepted:
    # MissionID: int
    # event: str
    # timestamp: datetime.datetime
    # Faction: str
    # Name: str
    # LocalisedName: str
    # Commodity: str
    # Commodity_Localised: str
    # Count: int
    # DestinationSystem: str
    # DestinationStation: str
    # Expiry: datetime.datetime
    # Wing: bool
    # Influence: Optional[str] = None
    # Reputation: Optional[str] = None
    # Reward: Optional[int] = None
    # Accepted: Optional[dict] = None
    # profit: Optional[int] = None
    # mission_open: Optional[bool] = True
    # last_update: Optional[CargoMissionDeliveryUpdate|MissionCompleted|MissionAbandoned] = None


    def __init__(self, **kwargs: dict[str, Any]) -> None:
        required_fields = [
            "Commodity",
            "Commodity_Localised",
            "Count",
            "DestinationStation",
            "DestinationSystem",
            "Expiry",
            "MissionID",
            "Wing",
            "event",
            "timestamp",
        ]
        default_none_fields = [
            "Accepted",
            "Influence",
            "Reputation",
            "Reward",
            "last_update",
            "profit",
        ]
        missing_required_fields = [k for k in required_fields if k not in kwargs]
        if len(missing_required_fields) > 0:
            raise ValueError(f"Required fields missing: {missing_required_fields}")
        if not kwargs["Wing"]:
            raise ValueError("Wing must be True")

        for k in [k for k in default_none_fields if k not in kwargs.keys()]:
            setattr(self, k, None)
        if "mission_open" not in kwargs:
            setattr(self, "mission_open", True)

        dt_fields = ["timestamp", "Expiry"]
        for k, v in kwargs.items():
            if isinstance(v, str) and k in dt_fields:
                v = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%SZ')
            setattr(self, k, v)

    @property
    def remaining_haul(self) -> int:
        if not getattr(self, "mission_open"):
            return 0

        last_update = getattr(self, "last_update")
        if last_update is None:
            return getattr(self, "Count")
        elif isinstance(last_update, CargoMissionDeliveryUpdate):
            return getattr(last_update, "TotalItemsToDeliver") - getattr(last_update, "ItemsDelivered")
        else:
            return getattr(self, "Count")


class MissionAbandoned:
    # MissionID: int
    # event: str
    # timestamp: datetime.datetime
    # Name: str
    # LocalisedName: str

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        required_fields = [
            "MissionID",
            "event",
            "timestamp",
            "Name",
            "LocalisedName",
        ]
        missing_required_fields = [k for k in required_fields if k not in kwargs]
        if len(missing_required_fields) > 0:
            raise ValueError(f"Required fields missing: {missing_required_fields}")

        for k, v in kwargs.items():
            if isinstance(v, str) and k == "timestamp":
                v = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%SZ')
            setattr(self, k, v)


class MissionCompleted:
    # MissionID: int
    # event: str
    # timestamp: datetime.datetime
    # Faction: str
    # Name: str
    # LocalisedName: str
    # Commodity: str
    # Commodity_Localised: str
    # Count: int
    # DestinationSystem: str
    # DestinationStation: str
    # Reward: int
    # FactionEffects: list[dict[str, Any]]

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        required_fields = [
            "MissionID",
            "event",
            "timestamp",
            "Commodity",
            "Commodity_Localised",
            "Count",
            "DestinationStation",
            "DestinationSystem",
        ]
        missing_required_fields = [k for k in required_fields if k not in kwargs]
        if len(missing_required_fields) > 0:
            raise ValueError(f"Required fields missing: {missing_required_fields}")

        for k, v in kwargs.items():
            if isinstance(v, str) and k == "timestamp":
                v = datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%SZ')
            setattr(self, k, v)


events_to_care_about = [
    "MissionAccepted",
    "MissionCompleted",
    "MissionAbandoned",
    "CargoDepot",
    "StartUp",
    "Docked",
    "Undocked",
    "Cargo",
    "Outfitting"
]


@dataclass
class This:
    accepted_missions: list[MissionAccepted] = field(default_factory=lambda: [])
    cargo_max: int = 0

    @property
    def open_missions(self) -> list[MissionAccepted]:
        return [i for i in self.accepted_missions if getattr(i, "mission_open")]

    @property
    def item_summary(self) -> dict[str, int]:
        return {}

    def hauling_summary(self, state: dict[str, Any] | None) -> (dict[str, Any], str):
        totals = {}
        if state is not None:
            calculate_cargo_max(state)
        for mission in self.open_missions:
            if mission.DestinationSystem not in totals:
                totals[mission.DestinationSystem] = {}
            if mission.DestinationStation not in totals[mission.DestinationSystem]:
                totals[mission.DestinationSystem][mission.DestinationStation] = {}
            if mission.Commodity_Localised not in totals[mission.DestinationSystem][mission.DestinationStation]:
                totals[mission.DestinationSystem][mission.DestinationStation][mission.Commodity_Localised] = 0
            totals[mission.DestinationSystem][mission.DestinationStation][mission.Commodity_Localised] += mission.remaining_haul

        hauling_str = "Hauling Summary:\n"
        for system in totals:
            hauling_str += f" {system}\n"
            for station in totals[system]:
                hauling_str += f"  {station}\n"
                for commodity in totals[system][station]:
                    if this.cargo_max == 0:
                        trips = 999
                    else:
                        trips = math.ceil(totals[system][station][commodity] / this.cargo_max)
                    hauling_str += f"   {commodity}: {totals[system][station][commodity]} [{trips} trips]\n"
                hauling_str += '\n'
        return totals, hauling_str

    @property
    def advertisement(self):
        if len(self.open_missions) <= 0:
            return "None"
        systems = list(set([i.DestinationSystem for i in self.open_missions]))
        system_missions = {k: [] for k in systems}
        for mission in self.open_missions:
            system_missions[mission.DestinationSystem].append(mission)
        advert = "@LFW-WMM "
        for system in system_missions:
            stack_size = len(system_missions[system])
            total_profit = math.ceil(
                sum([i.Reward for i in system_missions[system] if i.Reward is not None]) / 1000000)
            rep5s = sum([1 for i in system_missions[system] if i.Reputation == '+++++'])
            stations = {k.DestinationStation: None for k in system_missions[system]}
            for station in stations:
                stations[station] = sum([1 for i in system_missions[system] if i.DestinationStation == station])
            station_tag = ""
            for station in stations:
                if len(station_tag) > 0:
                    station_tag += ", "
                station_tag += f"{station}: {stations[station]}"
            # advert = f"@LFW-WMM [{system}] [Stack: {stack_size}] [Profit: {total_profit} M] [Reputation 5s: {rep5s}]"
            advert += f"[{system}] [Stack: {stack_size}; {station_tag}] [Profit: {total_profit} M]\n"
        return advert


this = This()
def set_clipboard():
    this_frame.clipboard_clear()
    this_frame.clipboard_append(this.advertisement)
    pass

def update_tk_widgets(state: dict[str, Any] | None) -> None:
    global this_frame
    global hauling_widget
    global advert_widget
    global advert_btn
    new_advert = this.advertisement.replace("] [", "]\n[")
    new_hauling = this.hauling_summary(state)[1]

    hauling_widget["text"] = this.hauling_summary(state)[1]
    advert_widget["text"] = this.advertisement

def plugin_app(inc_parent: tk.Frame) -> (tk.Label, tk.Label):
    global this_frame
    global hauling_widget
    global advert_widget
    global advert_btn
    this_frame = tk.Frame(inc_parent)
    row = this_frame.grid_size()[1]

    hauling_widget = tk.Label(this_frame, text="")
    advert_widget = tk.Label(this_frame, text="")
    advert_btn = tk.Button(this_frame, text="Copy ad", command=set_clipboard)

    advert_widget.grid(row=row, rowspan=1, column=0, columnspan=2, sticky=tk.W)
    hauling_widget.grid(row=row+1, rowspan=1, column=0, columnspan=1, sticky=tk.W)
    advert_btn.grid(row=row+1, rowspan=1, column=1, columnspan=1, sticky=tk.W)

    update_tk_widgets(state=None)

    return this_frame


def get_valid_logfiles():
    valid_files = []
    game_dir = config.get_str("journaldir")
    if game_dir is None:
        game_dir = config.default_journal_dir_path
    game_dir = os.path.expanduser(game_dir)

    current_date = datetime.datetime.now()
    max_days_ago = 7
    earliest_date = current_date - datetime.timedelta(days=max_days_ago)
    check_date = earliest_date
    while check_date <= current_date:
        globpattern = f"Journal.{str(check_date.year)}"
        globpattern += f"-{str(check_date.month).zfill(2)}"
        globpattern += f"-{str(check_date.day).zfill(2)}T*.log"
        glob_match = glob.glob(pathname=globpattern, root_dir=game_dir)
        if glob_match:
            for logfile in glob_match:
                fullpath = os.path.join(game_dir, logfile)
                if fullpath not in valid_files:
                    valid_files.append(fullpath)
        check_date += datetime.timedelta(days=1)
    return valid_files


def process_event_message(current_entry: dict[str, Any]) -> None:
    events_to_keep = {
        "MissionAccepted": MissionAccepted,
        "MissionCompleted": MissionCompleted,
        "MissionAbandoned": MissionAbandoned,
        "CargoDepot": CargoMissionDeliveryUpdate,
    }
    current_obj = None
    try:
        current_obj = events_to_keep[current_entry["event"]](**current_entry)
    except ValueError as e:
        raise ValueError(f"Could not match event with correct event type: {current_entry['event']}")
    except KeyError as e:
        pass

    if current_obj is None:
        return

    if isinstance(current_obj, MissionAccepted):
        if current_obj.MissionID not in [i.MissionID for i in this.accepted_missions]:
            this.accepted_missions.append(current_obj)
    elif isinstance(current_obj, MissionCompleted) or isinstance(current_obj, MissionAbandoned):
        matching_missions = [i for i in this.accepted_missions if current_obj.MissionID == i.MissionID]
        for matching_mission in matching_missions:
            matching_mission.last_update = current_obj
            matching_mission.mission_open = False
    elif isinstance(current_obj, CargoMissionDeliveryUpdate):
        matching_missions = [i for i in this.accepted_missions if current_obj.MissionID == i.MissionID]
        for matching_mission in matching_missions:
            if matching_mission.mission_open:
                if matching_mission.last_update is None:
                    matching_mission.last_update = current_obj
                elif current_obj.timestamp > matching_mission.last_update.timestamp:
                    matching_mission.last_update = current_obj


def load_existing_missions() -> None:
    accepted_missions = []
    accepted_mission_ids = []
    abandoned_missions = []
    completed_missions = []
    delivery_messages = []
    entry_events_to_keep = [
        "MissionAccepted",
        "MissionCompleted",
        "MissionAbandoned",
        "CargoDepot",
    ]
    for logfile in get_valid_logfiles():
        with open(logfile, "r") as fp:
            # log file entries are json, log file itself is missing the list brackets to make it properly json formatted
            # so this reads the log line by line and reads each line as an individual json document
            all_lines = fp.readlines()
            for line in all_lines:
                try:
                    current_entry = json.loads(line)
                except json.decoder.JSONDecodeError:
                    continue
                try:
                    process_event_message(current_entry)
                except ValueError as e:
                    continue


def calculate_cargo_max(state: dict[str, Any]) -> None:
    cargo_max = 0
    if "Modules" in state:
        for module in state["Modules"]:
            if "Item" in state["Modules"][module] and "cargorack" in state["Modules"][module]["Item"]:
                try:
                    cargo_item_str = state["Modules"][module]["Item"]
                    cargo_size = cargo_item_str.split('_')[2]
                    size = int(cargo_size[-1:])
                    cargo_max += pow(2,size)
                except (ValueError, KeyError, IndexError):
                    pass
    this.cargo_max = cargo_max


def journal_entry(
    cmdr: str, is_beta: bool, system: str, station: str, entry: dict[str, Any], state: dict[str, Any]
) -> Optional[str]:
    global first_event
    if first_event:
        update_tk_widgets(state)
        first_event = False

    if entry["event"] in events_to_care_about:
        calculate_cargo_max(state)
        process_event_message(entry)
        update_tk_widgets(state)


def plugin_start3(plugin_dir: str) -> str:
    load_existing_missions()
    return "EDMCPTNWMMS"
