stations = [
    {"station_id": "BLR001", "location": "Bengaluru", "pollutant": "PM2.5", "value": 42.5},
    {"station_id": "BLR002", "location": "Whitefield", "pollutant": "PM10", "value": 85},
    {"station_id": "BLR003", "location": "Electronic City", "pollutant": "PM2.5", "value": 31.2}
]

for station in stations:
    pollutant = station["pollutant"]
    if pollutant == 'PM2.5':
        print(station["location"], " - ", station["pollutant"], ": ", station["value"])

def greet():
    print("Welcome to TerraPulse AI")

greet()

def greetUser(name):
    print("Welcome,",name,"!")

greetUser("Sachetan")

def calculateAvg(a,b):
    result = (a+b)/2
    return result

average = calculateAvg(30,40)
print(average)

print("---------------------------------")
def filter_stations(stations, pollutant_name):
    x = []
    for station in stations:
        pollutant = station["pollutant"]
        if pollutant == pollutant_name:
            x.append(station)
    return x

ans = filter_stations(stations,'PM2.5')
print(ans)

def filter_high_pollution(stations,pollutant,threshold):
    x = []
    for s in stations:
        if s["pollutant"] == pollutant and s["value"] >= threshold:
            x.append(s)
    return x

print("\n",filter_high_pollution(stations,'PM2.5',31.2))



test = {
    "location": "Bengaluru",
    "value": "2.5"
}

try:
    print(test["unknown_type"])
except KeyError:
    print("Measurement data unavailable")

value = test.get("ID",'ID_DEF')
print(value)

print(type(station))
print(type(value))

for value in test.values():
    print(value)

