from opensky_api import OpenSkyApi
import urllib.request 
from random import randint
from time import sleep
from datetime import datetime
import csv
import os

dbpath = "resources/aircraftDatabase.csv"

def map_box(sbox, dbox, v):
    """
    sbox is (lat1, lat2, long1, long2),
    dbox is (x1, x2, y1, y2),
    v is (lat, long).
    result is (x, y)
    """

    xscale = abs(dbox[1]-dbox[0])/abs(sbox[3]-sbox[2])
    yscale = abs(dbox[3]-dbox[2])/abs(sbox[1]-sbox[0])
    x = (v[1]-sbox[2]+dbox[0])*xscale
    y = (v[0]-sbox[0]+dbox[2])*yscale

    return x,y

def print_display(bbox, points, labels, you=None, airports=None, time=None):
    """Prints a border of size bbox and plots points inside"""

    legend = dict(zip(range(len(labels)), labels))
    points=list(zip(points, legend))

    print('_'*(bbox[1]-bbox[0]+3))
    printed=False

    # TODO make display a 2d grid, loop thru points and set values, rather than this malarkey

    for y in range(bbox[3]-bbox[2],-1,-1):
        print('|', end='')
        for x in range(bbox[1]-bbox[0]+1):
#            print(f"x, y: {x}, {y}")
            if you and (int(you[0]) == x and int(you[1]) == y):
                print('X', end='')
                printed=True
            if airports:
                for ap in airports:
                    if int(ap[0][0]) == x and int(ap[0][1]) == y:
                        print(ap[1][0], end='')
                        printed=True
                        break
            for p in points:
                if int(p[0][0]) == x and int(p[0][1]) == y:
                    print(p[1], end='')
                    printed=True
                    break
            if not printed:
                print(' ', end='')
            printed=False
        print('|', end='')

        i = bbox[3] - bbox[2] - y
        if i < len(legend):
            print(f" {i}: {legend[i]}")
        elif i == len(legend) + 2:
            print(" ^")
        elif i == len(legend) + 3:
            print(" N")
        elif i == len(legend) + 5:
            print(f" {time}")
        elif you and (airports and len(airports) - y == 0):
            print(" X : You")
        elif you and not airports and y == 0:
            print(" X : You")
        elif airports and (i := len(airports) - y - 1) >= 0:
            print(f" {airports[i][1][0]} : {airports[i][1]}")
        else:
            print('')

    print('-'*(bbox[1]-bbox[0]+3))

def random_test():
    width = 80
    height = 20

    num = 5
    points = []

    for i in range(num):
        points.append((randint(0, width), randint(0, height)))

    bbox = (0, width, 0, height)

    print_display(bbox, points, list(range(len(points))))


def make_label(state, atts):
    label = ""
    for attr in atts:
        if (a := getattr(state, attr, None)):
            label = f"{label} {a:6}"
            if attr == "velocity":
                label = f"{label}kts"
            if attr == "geo_altitude":
                label = f"{label}ft"
        else:
            label = f"{label} {'UNK':4}"


    return label

def display_planes(time, bbox_world, bbox_display, states, you=None, airports=None, atts=["callsign"]):
    """Map coordinates to display space, create labels, and print"""

    if you:
      you = map_box(bbox_world, bbox_display, you)

    aps = []
    for airport in airports:
        aps.append((map_box(bbox_world, bbox_display, airport[0]), airport[1]))


    points = [map_box(bbox_world, bbox_display, (state.latitude, state.longitude))
              for state in states]



    labels = [make_label(state, atts) for state in states]

    print_display(bbox_display, points, labels, you=you, airports=aps, time=time)

def query_csv(icao24s):
    ret = {}
    with open(dbpath, newline='') as db:
        reader = csv.DictReader(db)
        for row in reader:
            if row["icao24"] in icao24s:
                ret[row["icao24"]] = row

    return ret

def test_query_csv():
    icao24s=['a3ecc8','a863a3']
    print(query_csv(icao24s))

def deg_to_cardinal(deg):
    if not deg:
        return "?"

    bounds = [(i * 22.5, (i+1) * 22.5) for i in range(16)]
    bounds = list(zip(bounds, ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]))

    for i in range(len(bounds)):
        if deg > bounds[i][0][0] and deg < bounds[i][0][1]:
            return bounds[i][1]

if __name__ == "__main__":
    airports=[((28.4311, -81.3083), "MCO"), ((28.5462, -81.3322), "ORL")]

    #default lat/long
    long_start = -81.506882
    long_end   = -81.112747
    lat_start  = 28.386568
    lat_end    = 28.671913

    you = None # Put your coords here to display X where you are
    display = (0, 60, 0, 20)

    username=None
    password=None

    import sys
    if "-u" in sys.argv:
        username=sys.argv[sys.argv.index("-u")+1]
        password=sys.argv[sys.argv.index("-p")+1]
    if "-x" in sys.argv:
        long_start=float(sys.argv[sys.argv.index("-x")+1])
        long_end=float(sys.argv[sys.argv.index("-x")+2])
    if "-y" in sys.argv:
        lat_start=float(sys.argv[sys.argv.index("-y")+1])
        lat_end=float(sys.argv[sys.argv.index("-y")+2])
    if "-s" in sys.argv:
        you = (float(sys.argv[sys.argv.index("-s")+1]), float(sys.argv[sys.argv.index("-s")+2]))

    bbox_world=(lat_start, lat_end, long_start, long_end) # lamin, lamax, lomin, lomax
    print("Connecting to OpenSky API")

    api = None
    if username:
      api = OpenSkyApi(username, password)
    else:
      api = OpenSkyApi()
    
    use_db = True

    try:
        if not os.path.exists(dbpath):
            print("Downloading aircraftDatabase.csv from OpenSky...", end='', flush=True)
            urllib.request.urlretrieve("https://opensky-network.org/datasets/metadata/aircraftDatabase.csv", dbpath)
            print("Done")

    except Exception as e:
        print(f"Could not download aircraftDatabase, cannot display additional aircraft details")
        use_db = False

    while True:
        try:
            states = api.get_states(bbox=bbox_world)
            if not states:
                continue
            time = datetime.fromtimestamp(states.time)
            states = states.states
            
            if use_db:
                icao24s = list(map(lambda s: s.icao24, states))

                details = query_csv(icao24s)

                for state in states:
                    detail = details.get(state.icao24, None)
                    if detail:
                        for k, v in detail.items():
                            state.__setattr__(k, v) 

                    # Override getters so values stay
                    state.__setattr__("cardinal_heading", deg_to_cardinal(state.heading))
                    state.__setattr__("velocity", int(state.velocity * 1.944))
                    state.__setattr__("geo_altitude",  int(state.geo_altitude * 3.2808))

            attributes = [
                "callsign",
                "geo_altitude",
                "cardinal_heading",
            ]

            if use_db:
                attributes.extend(["operatorcallsign", "model"])

            display_planes(time, bbox_world, display, states, you=you, airports=airports, atts=attributes)
        except Exception as e:
            print(f"Had an error: {e}\nContinuing...")

        sleep(2)
