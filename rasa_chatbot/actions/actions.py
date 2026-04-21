"""
Rasa Custom Actions
Calls the AutoGate Flask backend to fetch real data.
"""
import os
import requests
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

BACKEND_URL = os.getenv('BACKEND_API_URL', 'http://localhost:5000/api')
# Internal token for Rasa → backend calls (set in backend env)
INTERNAL_TOKEN = os.getenv('RASA_INTERNAL_TOKEN', '')

HEADERS = {'Authorization': f'Bearer {INTERNAL_TOKEN}'} if INTERNAL_TOKEN else {}


def _get(endpoint: str, params: dict = None) -> dict:
    try:
        resp = requests.get(f'{BACKEND_URL}{endpoint}', headers=HEADERS, params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {'error': str(e)}


class ActionGetAvailability(Action):
    def name(self) -> Text:
        return 'action_get_availability'

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        data = _get('/parking/availability')

        if 'error' in data:
            dispatcher.utter_message(text="Sorry, I couldn't fetch parking availability right now.")
            return []

        msg = (
            f"🅿️  **Parking Availability**\n"
            f"• Total spots: {data.get('total', '?')}\n"
            f"• Available: {data.get('available', '?')}\n"
            f"• Occupied: {data.get('occupied', '?')}\n"
            f"• Occupancy: {data.get('occupancy_percentage', '?')}%"
        )
        dispatcher.utter_message(text=msg)
        return []


class ActionGetVehicleStatus(Action):
    def name(self) -> Text:
        return 'action_get_vehicle_status'

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        plate = tracker.get_slot('plate_number')
        if not plate:
            dispatcher.utter_message(response='utter_ask_plate')
            return []

        plate = plate.upper().strip()

        # Check currently parked
        parked_data = _get('/parking/currently-parked', params={'search': plate})
        vehicles    = parked_data.get('vehicles', [])
        match       = next((v for v in vehicles if v['plate_number'] == plate), None)

        if match:
            duration = match.get('duration_minutes', 0)
            hours    = duration // 60
            mins     = duration % 60
            msg = (
                f"🚗 **{plate}** is currently parked.\n"
                f"• Owner: {match.get('owner_name', 'N/A')}\n"
                f"• Entry time: {match.get('entry_time', 'N/A')}\n"
                f"• Duration: {hours}h {mins}m\n"
                f"• Gate: {match.get('gate', 'N/A')}"
            )
        else:
            msg = f"🚗 **{plate}** is not currently in the parking lot."

        dispatcher.utter_message(text=msg)
        return []


class ActionGetEntryExit(Action):
    def name(self) -> Text:
        return 'action_get_entry_exit'

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        plate = tracker.get_slot('plate_number')
        if not plate:
            dispatcher.utter_message(response='utter_ask_plate')
            return []

        plate = plate.upper().strip()
        logs_data = _get('/logs', params={'search': plate, 'per_page': 5})
        logs      = logs_data.get('logs', [])

        if not logs:
            dispatcher.utter_message(text=f"No recent logs found for **{plate}**.")
            return []

        lines = [f"📋 **Recent logs for {plate}:**"]
        for log in logs[:5]:
            icon = "🟢" if log['event_type'] == 'entry' else "🔴"
            lines.append(
                f"{icon} {log['event_type'].capitalize()} — "
                f"{log['timestamp'][:16].replace('T', ' ')} "
                f"({log['status']})"
            )

        dispatcher.utter_message(text='\n'.join(lines))
        return []


class ActionGetDailySummary(Action):
    def name(self) -> Text:
        return 'action_get_daily_summary'

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        data = _get('/dashboard/stats')

        if 'error' in data:
            dispatcher.utter_message(text="Sorry, couldn't fetch today's summary.")
            return []

        msg = (
            f"📊 **Today's Parking Summary**\n"
            f"• Entries: {data.get('entries_today', 0)}\n"
            f"• Exits: {data.get('exits_today', 0)}\n"
            f"• Currently parked: {data.get('currently_parked', 0)}\n"
            f"• Denied entries: {data.get('denied_today', 0)}\n"
            f"• Occupancy: {data.get('occupancy_percentage', 0)}%\n"
            f"• Active anomalies: {data.get('active_anomalies', 0)}"
        )
        dispatcher.utter_message(text=msg)
        return []
