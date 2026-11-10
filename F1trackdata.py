import sys
import time
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

BASE = "https://api.openf1.org/v1"

def get(endpoint, query):
    """Ask the API for data and return it as a table."""
    url = f"{BASE}/{endpoint}?{query}"
    for _ in range(5):
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            time.sleep(0.5)
            return pd.DataFrame(r.json())
        time.sleep(2)
    raise RuntimeError(f"Request failed: {url} (status {r.status_code})")

# 1. Ask the user for a year and show that year's qualifying sessions
year = int(input("Which year? (2023 or later): "))
sessions = get("sessions", f"year={year}&session_name=Qualifying")
if sessions.empty:
    sys.exit("No qualifying sessions found for that year.")

sessions = sessions.sort_values("date_start").reset_index(drop=True)
print("\nRaces available:")
for i, row in sessions.iterrows():
    print(f"  {i + 1}. {row['circuit_short_name']} ({row['country_name']})")

choice = int(input("\nEnter the number of the race: ")) - 1
if choice < 0 or choice >= len(sessions):
    sys.exit("That number isn't in the list.")
chosen = sessions.iloc[choice]
session_key = int(chosen["session_key"])

# 2. Show the drivers in that session and ask for one
drivers = get("drivers", f"session_key={session_key}")
print("\nDrivers:")
for _, d in drivers.iterrows():
    print(f"  {d['name_acronym']}  -  {d['full_name']} ({d['team_name']})")

code = input("\nType a driver code (e.g. VER): ").strip().upper()
match = drivers[drivers["name_acronym"] == code]
if match.empty:
    sys.exit("That driver code isn't in the list.")
driver_number = int(match.iloc[0]["driver_number"])

# 3. Find the fastest lap
laps = get("laps", f"session_key={session_key}&driver_number={driver_number}")
laps = laps.dropna(subset=["lap_duration", "date_start"])
if laps.empty:
    sys.exit("No timed laps found for this driver.")
best = laps.loc[laps["lap_duration"].idxmin()]
start = pd.to_datetime(best["date_start"], utc=True)
end = start + pd.to_timedelta(best["lap_duration"], unit="s")

# 4. Download telemetry and positions for that lap
fmt = "%Y-%m-%dT%H:%M:%S.%f"
q = (f"session_key={session_key}&driver_number={driver_number}"
     f"&date>={start.strftime(fmt)}&date<={end.strftime(fmt)}")
print("\nDownloading lap data...")
car = get("car_data", q)
loc = get("location", q)
if car.empty or loc.empty:
    sys.exit("No telemetry or position data available for this lap.")

# 5. Line the two tables up in time
car["t"] = (pd.to_datetime(car["date"], utc=True) - start).dt.total_seconds()
loc["t"] = (pd.to_datetime(loc["date"], utc=True) - start).dt.total_seconds()
car = car.sort_values("t")
loc = loc.sort_values("t")

t = car["t"].to_numpy()
x = np.interp(t, loc["t"], loc["x"])
y = np.interp(t, loc["t"], loc["y"])
speed = car["speed"].to_numpy()
brake = (car["brake"].to_numpy() > 0).astype(int)

# 6. Coloured segments
points = np.array([x, y]).T.reshape(-1, 1, 2)
segments = np.concatenate([points[:-1], points[1:]], axis=1)

fig, ax = plt.subplots(figsize=(9, 9))
lc = LineCollection(segments, cmap='plasma', linewidth=4)
lc.set_array(speed)
ax.add_collection(lc)
ax.autoscale()
ax.set_aspect('equal')
ax.axis('off')
cbar = fig.colorbar(lc, ax=ax, shrink=0.7)
cbar.set_label('Speed (km/h)')

# 7. Braking zones
brake_starts = np.where(np.diff(brake) == 1)[0] + 1
ax.scatter(x[brake_starts], y[brake_starts], color='red', s=60,
           zorder=5, label='Braking starts')

# 8. High-speed markers
top_i = speed.argmax()
ax.scatter(x[top_i], y[top_i], marker='*', s=300, color='cyan',
           edgecolor='black', zorder=6,
           label=f'Top speed: {speed[top_i]:.0f} km/h')
fast = speed > 0.9 * speed.max()
ax.scatter(x[fast], y[fast], s=8, color='white', zorder=4,
           label='Above 90% of top speed')

ax.legend(loc='lower right')
ax.set_title(f"{chosen['circuit_short_name']} {year} Qualifying: "
             f"{code} fastest lap ({best['lap_duration']:.3f} s)")
plt.savefig(f"{chosen['circuit_short_name']}_{year}_{code}.png",
            dpi=200, bbox_inches='tight')
plt.show()
