# -*- coding: utf-8 -*-
"""
Created on Sun Jan 18 17:51:27 2026

@author: devli
"""

## Python!
import sys
import pytz
import datetime
import os.path
import requests

## PyQt5
from PyQt5.QtWidgets import QApplication, QWidget, QGridLayout, QVBoxLayout, QLabel, QFrame, QSizePolicy
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

## Google API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build

# /////////////////////////////////////////////////////////////////////////// #
# /////////////////////////////  CONFIGURATION  ///////////////////////////// #
# /////////////////////////////////////////////////////////////////////////// #

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = '/app/service_account.json'

event_size = '14px'
date_size = '18px'
moon_size = '20px'
LAT = 30.438
LONG = -84.280

# =========================================================================== #
# ============================== HELPERS ==================================== #
# =========================================================================== #

def paint_smart(hex_code):
    
    hex_code = hex_code.lstrip("#")
    
    try:
        r, g, b = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
        
        luminance = (0.299 * r + 0.587 * g + 0.144 * b) / 255
        
        if luminance > 0.5:
            return '#000000'
        else:
            return '#ffffff'
        
    except:
        return '#ffffff'
    
    
def howl_at_the_moon(date_obj):
    
    comp_date = date_obj.date()
    ref_date = datetime.date(2000, 1, 6)
    delta = (comp_date - ref_date).days
   
    lunar_age = delta % 29.530588
   
    if lunar_age < 0.5 or lunar_age > 29.03:
        return "○"
   
    if 14.26 < lunar_age < 15.26:
        return "●"
    
    return ""

def temp_gauge(HIGH, LOW, default = "#777", scale = (90, 20)):
    avgt = (HIGH + LOW) / 2
    
    score = (avgt - min(scale)) / (max(scale) - min(scale))
    score = min(max(score, 0), 1)
    score = round(score, 1) * 10
    
    ## Old Scale
    # heat_scale = {10: '#d83636',
    #               9: '#D5585E',
    #               8: '#CF6E78',
    #               7: '#C7808D',
    #               6: '#BC91A1',
    #               5: '#AF9EB1',
    #               4: '#A0A9BE',
    #               3: '#8FB1C8',
    #               2: '#7DB7CE',
    #               1: '#5CBBD3',
    #               0: '#5CBBD3'
    #               }
    
    heat_scale = {
        10: '#FF5252', 
        9:  '#FF7043',
        8:  '#FFA726', 
        7:  '#FFD740',
        6:  '#69F0AE',
        5:  '#00E676',
        4:  '#26C6DA',
        3:  '#42A5F5',
        2:  '#5C6BC0',
        1:  '#7986CB',
        0:  '#E8EAF6'
    }
    
    return heat_scale.get(score, default)

def humbug(humidity):
    
    if humidity <= 40:
        return "🟢"
    elif humidity <= 70:
        return "🟡"
    elif humidity <= 90:
        return "🔴"
    else:
        return "❗"
    
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>> WEATHER WORKER >>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #

class WeatherWorker(QThread):
    
    weather_loaded = pyqtSignal(dict)
    
    def run(self):
        url = "https://api.open-meteo.com/v1/forecast"
        
        params = {
            "latitude": LAT,
            "longitude": LONG,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode,sunrise,sunset",
            "hourly": "relative_humidity_2m",
            "temperature_unit": "fahrenheit",
            "timezone": "auto",
            "forecast_days": 14,
            "past_days": 3
            }
        
        try:
            r = requests.get(url, params = params)
            data = r.json()
            
            weather_map = {}
            daily = data.get('daily', {})
            humid = data.get('hourly', {}).get('relative_humidity_2m', [])
            count = len(daily.get('time', []))
            
            for i in range(count):
                date_str = daily['time'][i]
                
                rise_raw = daily['sunrise'][i]
                set_raw = daily['sunset'][i]
                
                rise_dt = datetime.datetime.fromisoformat(rise_raw)
                set_dt = datetime.datetime.fromisoformat(set_raw)
                
                rise_fmt = rise_dt.strftime('%I:%M%p').lstrip('0')
                set_fmt = set_dt.strftime('%I:%M%p').lstrip('0')
                
                start_index = i * 24
                slice_start = start_index + 9
                slice_end = start_index + 19
                daytime_slice = humid[slice_start:slice_end]
                valid_humid = [h for h in daytime_slice if h is not None]
                if valid_humid:
                    avg_humidity = round(sum(valid_humid) / len(valid_humid))
                else:
                    avg_humidity = 0
                
                weather_map[date_str] = {
                    'high': round(daily['temperature_2m_max'][i]),
                    'low': round(daily['temperature_2m_min'][i]),
                    'rain': daily['precipitation_probability_max'][i],
                    'humidity': avg_humidity,
                    'code': daily['weathercode'][i],
                    'sunrise': rise_fmt,
                    'sunset': set_fmt
                    }
                
            self.weather_loaded.emit(weather_map)
        
        except Exception as e:
            print(f"Weather Error: {e}")
            
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# <<<<<<<<<<<<<<<<<<<<<<<<<<< DATA WORKER <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< #
    
class DataWorker(QThread):
    
    data_loaded = pyqtSignal(dict)
    
    def run(self):
        print('--- WORKER STARTED --')
        
        try:
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, 
                scopes=SCOPES
            )
        except Exception as e:
            print(f"CRITICAL AUTH ERROR: {e}")
            return

        try:
            service = build('calendar', 'v3', credentials=creds)
            
            TARGET_CALENDARS = [
                'devlin.irwin@gmail.com',  
                'en.usa#holiday@group.v.calendar.google.com',
                'f93d340i0ti366p4kif5hou9edmudvsj@import.calendar.google.com'
            ]
            
            DEFAULT_COLORS = ['#7986CB', '#D81B60', '#8E24AA', '#E67C73']

            now = datetime.datetime.now(datetime.UTC)
            start = (now - datetime.timedelta(days=7)).isoformat()
            end = (now + datetime.timedelta(days=40)).isoformat()
            
            all_events = []
            
            for index, cal_id in enumerate(TARGET_CALENDARS):
                print(f"Checking calendar: {cal_id}")
                
                try:
                    events_result = service.events().list(
                        calendarId=cal_id,
                        timeMin=start,
                        timeMax=end,
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()
                    
                    items = events_result.get('items', [])
                    print(f"Found {len(items)} events in {cal_id}")
                    
                    color = DEFAULT_COLORS[index % len(DEFAULT_COLORS)]

                    for item in items:
                        item['color'] = color
                        all_events.append(item)
                        
                except Exception as e:
                    print(f"Could not read calendar {cal_id}: {e}")
                    
            all_events.sort(key=lambda x: x['start'].get('dateTime', x['start'].get('date')))
            
            organized_data = {}
            for event in all_events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                date_key = start.split('T')[0]
                
                if date_key not in organized_data:
                    organized_data[date_key] = []
                
                organized_data[date_key].append(event)
            
            self.data_loaded.emit(organized_data)
            
        except Exception as e:
            print(f"API Error: {e}")

# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ #
# $$$$$$$$$$$$$$$$$$$$$$$$$$$  CALENDAR CELL $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ #
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ #

class CalendarCell(QFrame):
    def __init__(self, r, c):
        super().__init__()
        self.grid_pos = (r, c)
        
        ## STYLE
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        self.setProperty("class", "normal")
        
        self.style_normal = """
            CalendarCell {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                }
        """
        
        self.style_today = """
            CalendarCell {
                background-color: #2b2b2b;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                }
        """
        
        self.setStyleSheet(self.style_normal)
                          
        ## LAYOUT
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(2)
        self.setLayout(self.layout)
        
        ## DATE HEADER
        self.date_lbl = QLabel('--')
        self.date_lbl.setFixedHeight(30)
        self.date_lbl.setAlignment(Qt.AlignLeft)
        self.layout.addWidget(self.date_lbl)
        
        ##SPACER
        self.spacer = QLabel("")
        self.spacer.setSizePolicy(QSizePolicy.Preferred, 
                                  QSizePolicy.Expanding)
        
        self.layout.addWidget(self.spacer)
        
        ## FOOTER
        self.footer_lbl = QLabel('')
        self.footer_lbl.setAlignment(Qt.AlignCenter)
        self.footer_lbl.hide()
        self.layout.addWidget(self.footer_lbl)

    def set_content(self, date_obj, is_anchor = False, events = [], weather_data = None):
                
        date_str = date_obj.strftime('%a %b %d')
        moon = howl_at_the_moon(date_obj)
        
        base_bg = "#222"
        border_color = "#444"
        text_color = "#888"
        specials = ""
        is_weekend = date_obj.weekday() >= 5
        
        if is_weekend:
            text_color = "#bd6f60"
            
        if is_anchor:
            text_color = "#64b56f"
            specials = " border: none; background: transparent;"
            
        style_date = f"font-weight: bold; font-size: {date_size}; color: {text_color}; padding-left: 4px;{specials}"
            
        header_html = f"""
        <table width="100%" border="0" cellspacing="0" cellpadding="0">
            <tr>
                <td align="left" style="{style_date}">
                    {date_str}
                </td>
                <td align="right" style="font-size: {moon_size}; color: #FFD700; vertical-align: top;">
                    {moon}
                </td>
            </tr>
        </table>
        """
            
        self.date_lbl.setText(header_html)
        
        row = self.grid_pos[0]
            
        if row in [1, 2] and weather_data:
            
            rain_icon = "💧" if weather_data['rain'] > 20 else ""
            separator = "//"

            temp_str = f"{weather_data['high']}°/{weather_data['low']}°  {separator}  {rain_icon}{weather_data['rain']}%"
            hum_str = f"{humbug(weather_data['humidity'])}  {weather_data['humidity']}%"
            sun_str = f"☀️ {weather_data['sunrise']}  {weather_data['sunset']} ☾"

            footer_text = f"{temp_str}\n{hum_str}\n{sun_str}"
            self.footer_lbl.setText(footer_text)
            self.footer_lbl.show()

            footer_color = temp_gauge(weather_data['high'], weather_data['low'])

            self.footer_lbl.setStyleSheet(f"""
                color: #bbb; 
                font-size: 12px; 
                background-color: rgba(0, 0, 0, 0.2);
                border-top: 3px solid {footer_color};
                border-radius: 0px 0px 4px 4px; 
                padding: 4px;
            """)
        
        else:
            self.footer_lbl.hide()
        
        while True:
            if self.layout.count() <= 3:
                break
            
            item = self.layout.itemAt(1)
            if item.widget() == self.spacer:
                break
            
            self.layout.takeAt(1).widget().deleteLater()
        
        if events:
            
            n_events = {1: 10, 2: 5}
            max_events = n_events.get(row, 2)
            
            spacer_index = self.layout.indexOf(self.spacer)
            
            for event in events[:max_events]:
                summary = event['summary']
                bg_color = event.get('color', '#555555')
                evt_text_color = paint_smart(bg_color)
                
                start_raw = event['start'].get('dateTime', event['start'].get('date'))
                
                if 'T' in start_raw:
                    
                    dt = datetime.datetime.fromisoformat(start_raw.replace('Z', '+00:00'))
                    
                    local_tz = pytz.timezone("America/New_York")
                    local_dt = dt.astimezone(local_tz)
                    
                    time_str = local_dt.strftime("%H:%M")
                    display_str = f"<b>{time_str}</b> {summary}"
                
                else:
                    display_str = summary
                
                evt_lbl = QLabel(display_str)
                evt_lbl.setWordWrap(True)
                evt_lbl.setStyleSheet(f"""
                    background-color: {bg_color};
                    color: {evt_text_color};
                    border-radius: 4px;
                    padding: 2px 4px;
                    font-size: {event_size};
                    """)
                                      
                self.layout.insertWidget(spacer_index, evt_lbl)
                spacer_index += 1
                
        if is_anchor:
            self.setStyleSheet("""
                CalendarCell {
                    background-color: #37474f;
                    border: 2px solid #64b5f6;
                    border-radius: 4px
                    }
                """)
                               
        else:
            self.setStyleSheet(f"""
                CalendarCell {{
                    background-color: {base_bg};
                    border: 1px solid {border_color};
                    border-radius: 4px;
                    }}
                """)
                
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ #
# +++++++++++++++++++++++++++++ WALL CALENDAR +++++++++++++++++++++++++++++++ #
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ #
                                                                        
class WallCalendar(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("COMMAND CENTER")
        self.resize(1920, 1200)
        self.setStyleSheet("""
            background-color: #121212;
            """)
                           
        self.layout = QGridLayout()
        self.layout.setSpacing(10)
        self.setLayout(self.layout)
        
        self.event_cache = {}
        self.weather_cache = {}
        self.cells = {}
        
        self.init_grid()
        self.populate_dates()
        
        self.init_timer()
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            time.sleep(10)
        
    def init_timer(self):
        
        self.refresh_calendar()
        self.refresh_weather()
        
        self.cal_timer = QTimer(self)
        self.cal_timer.timeout.connect(self.refresh_calendar)
        self.cal_timer.start(600000)
        
        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.refresh_weather)
        self.weather_timer.start(3600000)
        
    def refresh_calendar(self):
        print(f"Refreshing data @ {datetime.datetime.now()}")
        self.worker = DataWorker()
        self.worker.data_loaded.connect(self.handle_data_update)
        self.worker.start()
        
    def handle_data_update(self, data):
        print(f"Data Recieved @ {datetime.datetime.now()}")
        self.event_cache = data
        self.populate_dates()
        
    def refresh_weather(self):
        self.weather_worker = WeatherWorker()
        self.weather_worker.weather_loaded.connect(self.handle_weather)
        self.weather_worker.start()
    
    def handle_weather(self, data):
        self.weather_cache = data
        self.populate_dates()
        
    def init_grid(self):
        
        for r in range(5):
            for c in range(7):
                cell = CalendarCell(r, c)
                self.layout.addWidget(cell, r, c)
                self.cells[(r, c)] = cell
                
        self.layout.setRowStretch(0, 1)
        self.layout.setRowStretch(1, 3)
        self.layout.setRowStretch(2, 2)
        self.layout.setRowStretch(3, 1)
        self.layout.setRowStretch(4, 1)
        
    def populate_dates(self):
        
        today = datetime.datetime.today()
        anchor_r, anchor_c = 1, 1
        
        print('UPDATING CELLS')
        
        for r in range(5):
            for c in range(7):
                
                row_diff = r - anchor_r
                col_diff = c - anchor_c
                
                days_offset = (row_diff * 7) + col_diff
                
                target_date = today + datetime.timedelta(days = days_offset)
                date_key = target_date.strftime('%Y-%m-%d')
                
                day_events = self.event_cache.get(date_key, [])
                day_weather = self.weather_cache.get(date_key, None)
                
                is_today = (r == anchor_r and c == anchor_c)
                
                self.cells[(r, c)].set_content(target_date, 
                                               is_today, 
                                               day_events, 
                                               day_weather)
                
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~  MAIN BLOCK  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
                
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WallCalendar()
    #window.show()
    window.showFullScreen()
    sys.exit(app.exec_())
