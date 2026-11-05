stations = [
    {
        "station_id": "BLR001",
        "location": "Bengaluru",
        "pollutant": "PM2.5",
        "value": 42.5
    },
    {
        "station_id": "BLR002",
        "location": "Whitefield",
        "pollutant": "PM10",
        "value": 85
    },
    {
        "station_id": "BLR003",
        "location": "Electronic City",
        "pollutant": "PM2.5",
        "value": 31.2
    }
]

# list
cities = ["Bengaluru","Dehli","Mumbai"]


print(stations[0])
print(stations[1])

print("\n\n")

for station in stations:
    print(station["location"]," - ", station["pollutant"], ":", station["value"]) 

pollution_value = 85
if pollution_value > 100:
    print("High pollution")
elif pollution_value > 50:
    print("Moderate pollution")
else:
    print("Low pollution")
