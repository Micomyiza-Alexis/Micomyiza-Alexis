import json
import os
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = "Micomyiza-Alexis"
TOKEN = os.environ.get("GH_CONTRIBUTIONS_TOKEN")

if not TOKEN:
    raise SystemExit("ERROR: GH_CONTRIBUTIONS_TOKEN is not set.")

today = date.today()
start = today - timedelta(days=364)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

payload = {
    "query": query,
    "variables": {
        "login": USERNAME,
        "from": datetime.combine(start, datetime.min.time()).isoformat() + "Z",
        "to": datetime.combine(today + timedelta(days=1), datetime.min.time()).isoformat() + "Z",
    },
}

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "contribution-graph-generator",
    },
)

with urllib.request.urlopen(request, timeout=30) as response:
    result = json.load(response)

if result.get("errors"):
    raise SystemExit("GitHub GraphQL error: " + json.dumps(result["errors"]))

user = result.get("data", {}).get("user")
if not user:
    raise SystemExit(f"GitHub user not found: {USERNAME}")

calendar = user["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]
total = calendar["totalContributions"]

cell = 11
gap = 4
left = 42
top = 70
right = 18
bottom = 34

grid_width = len(weeks) * (cell + gap) - gap
width = left + grid_width + right
height = top + 7 * (cell + gap) - gap + bottom

colors = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
days = ["Mon", "Wed", "Fri"]
months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
    '<rect width="100%" height="100%" rx="10" fill="#0d1117"/>',
    '<g font-family="Arial, Helvetica, sans-serif" fill="#e6edf3">',
    f'<text x="{left}" y="29" font-size="16" font-weight="600">Contribution Activity</text>',
    f'<text x="{left}" y="49" font-size="11" fill="#8b949e">{total:,} contributions in the last year</text>',
]

# Day labels on the left.
for label, day_index in zip(days, [0, 2, 4]):
    y = top + day_index * (cell + gap) + cell - 1
    parts.append(
        f'<text x="8" y="{y}" font-size="10" fill="#8b949e">{label}</text>'
    )

# Contribution squares and month labels.
previous_month = None

for week_index, week in enumerate(weeks):
    week_days = week["contributionDays"]

    if not week_days:
        continue

    first_day = date.fromisoformat(week_days[0]["date"])

    if first_day.month != previous_month:
        x = left + week_index * (cell + gap)
        parts.append(
            f'<text x="{x}" y="{top - 12}" font-size="10" fill="#8b949e">'
            f'{months[first_day.month - 1]}</text>'
        )
        previous_month = first_day.month

    for item in week_days:
        day_date = date.fromisoformat(item["date"])
        day_index = day_date.weekday()
        count = item["contributionCount"]

        if count == 0:
            level = 0
        elif count < 3:
            level = 1
        elif count < 6:
            level = 2
        elif count < 10:
            level = 3
        else:
            level = 4

        x = left + week_index * (cell + gap)
        y = top + day_index * (cell + gap)
        tooltip = escape(f"{count} contributions on {day_date.isoformat()}")

        parts.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
            f'rx="2" fill="{colors[level]}">'
            f'<title>{tooltip}</title></rect>'
        )

# Legend.
legend_y = height - 14
parts.append(
    f'<text x="{left}" y="{legend_y}" font-size="10" fill="#8b949e">Less</text>'
)

legend_x = left + 34
for level, color in enumerate(colors):
    parts.append(
        f'<rect x="{legend_x + level * 15}" y="{legend_y - 9}" '
        f'width="10" height="10" rx="2" fill="{color}"/>'
    )

parts.extend([
    f'<text x="{legend_x + 86}" y="{legend_y}" font-size="10" fill="#8b949e">More</text>',
    '</g>',
    '</svg>',
])

output = Path("assets/contribution-graph.svg")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text("\n".join(parts), encoding="utf-8")

print(f"Generated {output} with {total:,} contributions.")
