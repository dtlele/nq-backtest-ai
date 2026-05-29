import csv
import os
from datetime import datetime, timedelta
import pytz

class NewsManager:
    def __init__(self):
        self.events = []
        self._load_events()
        
    def _load_events(self):
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        csv_path = os.path.join(data_dir, 'economic_calendar.csv')
        
        if not os.path.exists(csv_path):
            print(f"[NEWS MANAGER] Warning: {csv_path} not found. No news data loaded.")
            return
            
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse datetime string (assumed UTC format 'YYYY-MM-DDTHH:MM:SSZ')
                try:
                    dt = datetime.strptime(row['datetime'], '%Y-%m-%dT%H:%M:%SZ')
                    dt = dt.replace(tzinfo=pytz.UTC)
                    self.events.append({
                        'timestamp': dt,
                        'event': row['event'],
                        'impact': row['impact']
                    })
                except Exception as e:
                    print(f"[NEWS MANAGER] Error parsing date {row.get('datetime')}: {e}")
                    
        self.events.sort(key=lambda x: x['timestamp'])
        print(f"[NEWS MANAGER] Loaded {len(self.events)} high-impact events.")
        
    def get_upcoming_news(self, current_time: datetime, window_mins: int = 30) -> str:
        """
        Checks if there are any high-impact events within window_mins (before or after).
        Returns a descriptive string for Fabio's prompt, or None.
        """
        # Ensure current_time is UTC aware
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=pytz.UTC)
            
        upcoming = []
        for ev in self.events:
            diff = ev['timestamp'] - current_time
            diff_mins = diff.total_seconds() / 60.0
            
            if -window_mins <= diff_mins <= window_mins:
                if diff_mins > 0:
                    time_str = f"in {int(diff_mins)} minutes"
                elif diff_mins < 0:
                    time_str = f"{abs(int(diff_mins))} minutes ago"
                else:
                    time_str = "RIGHT NOW"
                    
                upcoming.append(f"{ev['event']} ({time_str})")
                
        if upcoming:
            return "HIGH IMPACT NEWS: " + " | ".join(upcoming)
        return "No high-impact news in the vicinity."

    def is_blackout_day(self, date_str: str) -> tuple[bool, str]:
        """
        Checks if the given day (YYYY-MM-DD) contains a Tier 1 event that warrants skipping the whole day.
        Tier 1 events: FOMC, NFP, CPI, Elections.
        Returns (is_blackout, reason).
        """
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return False, ""
            
        for ev in self.events:
            if ev['timestamp'].date() == target_date:
                event_name = ev['event'].lower()
                if any(kw in event_name for kw in ['fomc', 'nfp', 'nonfarm', 'cpi', 'election']):
                    return True, ev['event']
                    
        return False, ""
