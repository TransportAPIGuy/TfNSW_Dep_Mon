import requests
import time
from datetime import datetime, timezone
import json
import pprint

# Variables to be set by the user
API_KEY = "put your API key here"

# You can hardcode stops instead of using the user input
# 1 = Train, 2 = Metro, 4 = Light Rail, 5 = Bus, 7 = Coach, 9 = Ferry, 11 = School Bus
preconfigured_stops = None # comment out if you wan't to hard code in stops
# preconfigured_stops = [
#     {
#         "station_name": "Parramatta",
#         "stop_id": "10101229",
#         "modes": [
#             {
#                 "mode_name": "train",
#                 "mode_number": 1,
#             },
#             {
#                 "mode_name": "bus",
#                 "mode_number": 5,
#                 "routes_to_exclude": ["520", "521", "523", "524", "546", "549", "600", "601", "603", "604", "606", "609", "660", "661", "662", "663", "700", "705", "706", "707", "711", "802", "804", "806", "810X", "811X", "824", "906", "907", "909", "920"]
#             },
#             {
#                 "mode_name": "coach",
#                 "mode_number": 7,
#             }
#         ]
#     },
#     {   
#         "station_name": "Parramatta Square",
#         "stop_id": "10101710",
#         "modes": [
#             {
#                 "mode_name": "light_rail",
#                 "mode_number": 4,
#             }
#         ]
#     },
#     {
#         "station_name": "Parramatta Wharf",
#         "stop_id": "10102032",
#         "modes": [
#             {
#                 "mode_name": "ferry",
#                 "mode_number": 9,
#             }
#         ]
#     }
# ]


#######################################################################################################################################

def get_station_ids_from_station_names_and_modes(user_input):
    """
    
    user input will be in the format: "{station name} ({mode as string}, {mode as string}); {station name} ({mode as string}, {mode as string})"
    e.g., "Parramatta (train, bus); Parramatta Square (light_rail); Parramatta Wharf (ferry)"
    
    Stations are separated by semicolons and always outside of brackets.
    Modes - for each station - are separated by commas and always inside brackets following the station name.
    
    We will take the user input and make it look like the below schema:
    
    [
        {
            "station_name": "Parramatta",
            "stop_id": None,
            "modes": [
                {
                    "mode_name": "train",
                    "mode_number": 1,
                }
            ]
        }
    ]
    
    stop_id will be None for now, as we will get it from the API later.
    We will use a lookup table to map the mode numbers to the mode names so the user doesn't have to remember them.
    
    We'll need to take into account the confidence of the API response - e.g., might just use the best match.
    """
    
    # Step 0 - set up
    
    # Map mode numbers to transport types
    mode_to_transport = {
        "train": 1,
        "metro": 2,
        "light_rail": 4,
        "bus": 5,
        "coach": 7,
        "ferry": 9,
        "school_bus": 11,
    }
    
    # Step 1 - break down the user input
    
    # stations separated by semicolons
    list_of_stations_with_modes = user_input.split(";")
    # remove leading and trailing whitespace from each station
    list_of_stations_with_modes = [station.strip() for station in list_of_stations_with_modes]
    # print(f"List of provided stations with modes: {list_of_stations_with_modes}")
    
    # for each station inside list_of_stations_with_modes, get the modes of transport inside the brackets
    for i, station in enumerate(list_of_stations_with_modes):
        # split the station name and modes by the first opening bracket
        station_name, modes = station.split("(", 1)
        # remove the closing bracket and any leading/trailing whitespace from the modes
        modes = modes.replace(")", "").strip()
        # split the modes by commas and remove leading/trailing whitespace from each mode
        modes = [mode.strip() for mode in modes.split(",")]
        
        # Now we have the station name and modes, we can create a dictionary for each station
        list_of_stations_with_modes[i] = {
            "station_name": station_name.strip(),
            "stop_id": None, # We'll fill this stop_id in later using the API
            "modes": [
                {
                    "mode_name": mode,
                    "mode_number": mode_to_transport.get(mode, None)  # Get the mode number from the lookup table, or None if not found
                } for mode in modes
            ]
        }
        # print(f"Station: {station_name.strip()}, Modes: {modes}")
    
    # Step 2 - call the API to get the stop IDs for each station
    
    # Define the API endpoint and headers
    endpoint = "https://api.transport.nsw.gov.au/v1/tp/stop_finder"
    headers = {
        "Authorization": f"apikey {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # pprint the list_of_stations_with_modes to check structure
    # print(f"List of stations with modes:")
    # pprint.pprint(list_of_stations_with_modes)

    # Step 3 - transform the data

    # for each station in the list, get the stop_id using the API
    for station in list_of_stations_with_modes:
        # Define the query parameters
        params = {
            "outputFormat": "rapidJSON",
            "type_sf": "stop",
            "name_sf": station["station_name"],
            "coordOutputFormat": "EPSG:4326",
            "TfNSWSF": "true",
            "version": "10.2.1.42"
        }

        try:
            # print(f"****************************************")
            
            # Make the API request
            # print(f"Fetching information for  IDs for '{station['station_name']}'...")
            response = requests.get(endpoint, headers=headers, params=params)

            # Check if the response is successful
            if response.status_code != 200:
                print(f"Error: {response.status_code} for station '{station['station_name']}'")
                print(response.text)
                continue

            # Parse the JSON response
            stop_finder_data = response.json()
            
            # print(f"Stop finder data for '{station['station_name']}'")
            # pprint.pprint(stop_finder_data)
            
            '''
            {
                'locations': [
                    {
                        'isBest': True,
                        'matchQuality': 100000,
                        'modes': [1, 5, 7, 11],
                        'parent': {'id': '95346013|1',
                            'name': 'Parramatta',
                            'type': 'locality'},
                    'properties': {'stopId': '10101229'},
                    'type': 'stop'},
                    "assignedStops: [{
                        "id": "10101708",
                        "type": "stop",
                        "modes": [
                            4
                        ],
                ]
            }
            '''
            
            for location in stop_finder_data["locations"]:
                
                # print(f"Location: {location['name']}")
            
                # modes_in_this_stop
                modes_in_this_stop = location["modes"]
                # print(f"Modes in this stop: {modes_in_this_stop}")
                
                # TODO - only skip the modes which aren't available, not all modes if one of them isn't available
                # # if the modes of transport I want aren't available at this stop, then skip it and move to the next
                # if station["modes"][0]["mode_number"] not in modes_in_this_stop:
                #     print(f"Skipping '{station['station_name']}' as mode {station['modes'][0]['mode_number']} is not available at this stop")
                #     continue

                # troubleshooting info
                # print match quality
                # print(f"Match quality: {stop_finder_data['locations'][0]['matchQuality']}")
                # isBest? Print that value for now
                # print(f"Is best match? {location['isBest']}")
                # get stop name for printing
                # print(f"Stop name: {location['parent']['name']}")
                
                # try to get the stop_id from the properties
                try:
                    stop_id = location["properties"]["stopId"]
                    # print(f"Stop ID: {stop_id} from properties")
                except KeyError:
                    # otherwise get the stop_id from the 1st result in assignedStops
                    stop_id = location["assignedStops"][0]["id"]
                    # print(f"Stop ID: {stop_id} from assignedStops")
                
                # for this current station, update it's stop_id with the stop_id from the API
                # print(f"Updating stop ID for '{station['station_name']}' to '{stop_id}'")
                station["stop_id"] = stop_id


        except Exception as e:
            print(f"Error fetching station IDs for '{station['station_name']}': {e}")

    # print(f"\n\n\n\n\n\n****************************************")
    # print(f"List of stations with modes after API call:")
    # pprint.pprint(list_of_stations_with_modes)
    return list_of_stations_with_modes


# Supplementary functions

def format_platforms(platform, type_of_transport, service, platform_return_raw, platform_raw):
    '''
    Platform formats change depending on the mode of transport, so we need to handle them differently.
    
    Args:
        platform (str): The platform number or identifier.
        service (dict): The service information containing the location and other details.
        type (str): The type of transport (e.g., "train", "bus", "ferry", "light_rail", as defined by me).
    
    Returns:
        str: The formatted platform string. E.g., "Platform 1", "Stand J", "Wharf 5 Side A", etc.
    
    
    This function could be replaced if you were to lookup the platform code using the GTFS data - but this way also works. I don't know why the departure monitor API doesn't just give the Platform in plain text; why make you look up the code ina  lookup table?
    
    '''
    
    if platform_return_raw:
        # print(f"Using raw platform name: {platform_raw}")
        return platform_raw
    
    if type_of_transport == "train" or type_of_transport == "metro":
        # print(f"Train Platform before formatting: {platform}")
        # Train & metro platforms are in the format CE18 or PTA, so we need to remove the first 2-3 letters and keep the rest. Keep just the digits.
        platform_display = ''.join(filter(str.isdigit, platform))
        
        # If the platform is a number less than 10, remove the leading 0
        # Check if the first character is '0', and if so, remove it
        if platform_display.startswith("0") and len(platform_display) > 1:
            platform_display = platform_display[1:]
            
        platform_display = f"Platform {platform_display}" if platform_display else platform_display
        # print(f"Train Platform after formatting: {platform_display}")
    
    elif type_of_transport == "ferry":
        # print(f"Ferry Wharf before formatting: {platform}")
        
        # If the platform is in the format F5A (letter, number, letter), 
        if len(platform) > 1 and platform[0] == "F" and platform[1].isdigit():
            # Ferry wharfs are in the format F5A, so we need to remove the first letter and keep the rest
            # Format should be "Wharf {platform_number} Side {platform_side}"
            platform_display = platform[1:] if len(platform) > 1 else platform
            if platform_display and len(platform_display) > 1:
                # Split the platform into number and side (if available)
                platform_number = platform_display[:-1]
                platform_side = platform_display[-1]
                platform_display = f"Wharf {platform_number} Side {platform_side}"
        # If the platform is in any other form, don't return it
        else:
            platform_display = ""
            # print(f"Ferry Wharf: {platform} - not in the correct format")
            
        # If at this point the Ferry Wharf/platform is just 1, then don't return it (most Ferry stops are just a single wharf with a single side)
        if platform_display == "1":
            platform_display = ""
            
        # print(f"Ferry Wharf after formatting: {platform_display}")
                
    elif type_of_transport == "light_rail":
        # print(f"Light Rail Platform before formatting: {platform}")

        # Extract the numeric part of the platform string
        platform_display = ''.join(filter(str.isdigit, platform))
        
        # Add "Side" to the platform number
        platform_display = f"Platform {platform_display}" if platform_display else platform_display
        
        # Out of preference, we might not want to show a light rail platform
        # platform_display = ""
        
        # print(f"Light Rail Platform after formatting: {platform_display}")
        
    elif type_of_transport == "bus":
        # print(f"Bus Stand before formatting: {platform}")
        
        # Bus platforms are in the format J, so we need to keep the first letter and remove the rest
        # Format should be "Stand {platform_display}"
        platform_display = platform[0] if len(platform) > 0 else platform
        platform_display = f"Stand {platform_display}" if platform_display else platform_display
        
        # print(f"Bus Stand after formatting: {platform_display}")
        
        # print(f"Bus Stand after formatting: {platform_display}")
        
    elif type_of_transport == "coach":
        # print(f"Coach Stand before formatting: {platform}")
        
        # Coach locations are a bit different, we'll need to dig into location > parent > name
        # Format should just be returned unchanged
        platform_display = service["location"]["parent"].get("name", "")
        
        # print(f"Coach Stand after formatting: {platform_display}")
        
    else:
        # For any other mode, just keep the platform as is
        platform_display = platform
        # print(f"Unknown platform format: {platform}")
    
    # print(f"Platform after formatting: {platform_display}")
    return platform_display

def colour_codes(line, type_of_transport):
    """
    Determine the color codes for a given line and type of transport, with dynamic transparency.
    
    You can use the GTFS data to get the colour codes for each line, but that requires extra files to do a lookup.
    """
    # Define the base color codes
    base_colour_codes = {
        "M1": "#168388", "T1": "#F99D1C", "T2": "#0098CD", "T3": "#F37021", "T4": "#005AA3", "T5": "#C4258F", "T6": "#7D3F21", "T7": "#6F818E", "T8": "#00954C", "T9": "#D11F2F",
        "BMT": "#F99D1C", "CCN": "#D11F2F", "HUN": "#833134", "SHL": "#00954C", "SCO": "#005AA3", "Regional": "#F6891F",
        "L1": "#BE1622", "L2": "#DD1E25", "L3": "#781140", "L4": "#CD0D4D", "NLR": "#EE343F",
        "F1": "#00884B", "F2": "#144734", "F3": "#648C3C", "F4": "#BFD730", "F5": "#286142", "F6": "#00AB51", "F7": "#00B189", "F8": "#55622B", "F9": "#65B32E", "F10": "#5AB031",
        "STKN": "#5AB031", "MFF": "#0693E3", "CCWB": "#2349E5", "CCWM": "#2349E5",
        "Bus": "#83D0F5",
        "B1": "#FFB81C", "Night_Bus": "#001b3d", "Train_replacement_bus": "#808080",
        "coach": "#732A82",
        "Default": "#000000"
    }

    # Determine the line type
    if type_of_transport == "coach":
        line = "Coach" # Coach 'lines' are always different, but they all just get the same colour codes. S make line == type; don't bother doing anything fancy with the line variable.
    
    elif len(line) >= 3:
        # Can just check if the type is a bus, don't need to check line - except for train replacement bus and night busses
        if line.isdigit() and len(line) == 3:
            line = "Bus"
        elif line[0] in {"T", "M"} and line[1:2].isdigit() and len(line) > 2:
            line = "Bus"
        elif line[:3].isdigit() and line[3] in {"X", "N"}:
            line = "Bus"
        elif len(line) >= 3 and line[:-2].isdigit() and line[-2] == "T" and line[-1].isdigit():
            line = "Train_replacement_bus"  # Train replacement bus with 1-2 digits, "T", and 1 digit
        elif line.startswith("N") and line[1:].isdigit() and len(line) == 3:
            line = "Night_Bus"
    # Special case, line is B1 - it's a special bus with only 2 characters. Not sure why Copilot added this
    elif line == "B1":
        line = "B1"

    # Get the base colors for the line
    colors = base_colour_codes.get(line, base_colour_codes["Default"])
    
    # print(f"Line: {line}, Colors: {colors}")

    return colors


# Function that gets the departures for a specific transport type

def get_departures(stop_name, stop_id, modes_of_transport, routes_to_exclude):
    """
    Global args:
        API_KEY (str): API key for the Transport for NSW API.
    
    Args:
        stop_name (str): used to remove 'via' from the destination name if it is the same as the stop name.
        stop_id (str): The ID of the stop to get departures from.
        modes_of_transport (list): List of transport modes to include (e.g., ["train", "bus", "ferry"]).
        routes_to_exclude (list): List of routes to exclude from the results. Just really used for busses.
        
    Returns:
        list: List of departures with relevant details.
    
    Get departures for a specific transport type.
    """
    # Get the current date and time at the time of the API call
    current_date = datetime.now().strftime("%Y%m%d")
    current_time = datetime.now().strftime("%H%M")

    # Base endpoint URL without query parameters
    endpoint = "https://api.transport.nsw.gov.au/v1/tp/departure_mon"

    # Set up headers
    headers = {
        "Authorization": f"apikey {API_KEY}",
        "Content-Type": "application/json"
    }

    # Query parameters
    params = {
        "outputFormat": "rapidJSON",
        "coordOutputFormat": "EPSG:4326",
        "mode": "direct",
        "type_dm": "stop",
        "name_dm": stop_id,
        "departureMonitorMacro": "true",
        "TfNSWDM": "true",
        "version": "10.2.1.42",
        "itdDate": current_date,
        "itdTime": current_time,
        "excludedMeans": "checkbox",
        "includeNonPassengerTrips": "false",
    }

    # Will be used later to map the type of transport to a more readable format for the JSON output and defining the accent colours
    type_lookup_table = {
        1: "train",
        2: "metro",
        4: "light_rail",
        5: "bus",
        7: "coach",
        9: "ferry",
        11: "school_bus"
    }
    
    # The API specifies which modes to EXCLUDE, not include, so assume we wan't to exclude all then remove the ones from exluded_modes we want to keep.
    
    # Start by assuming we'll exclude all modes of transport
    excluded_modes = [
        "exclMOT_1",  # Exclude trains
        "exclMOT_2",  # Exclude metro
        "exclMOT_4",  # Exclude light rail
        "exclMOT_5",  # Exclude bus
        "exclMOT_7",  # Exclude coach
        "exclMOT_9",  # Exclude ferry
        "exclMOT_11"  # Exclude school bus
    ]

    # print(f"Modes I want to keep: {modes_of_transport}")
    # print(f"Excluded modes before un-excluding: {excluded_modes}")

    # Actually don't exclude modes we want to keep
    mode_name = modes_of_transport["mode_name"]
    if mode_name == "train":
        excluded_modes.remove("exclMOT_1")  # Keep trains
    elif mode_name == "metro":
        excluded_modes.remove("exclMOT_2")  # Keep metros
    elif mode_name == "light_rail":
        excluded_modes.remove("exclMOT_4")  # Keep light rails
    elif mode_name == "bus":
        excluded_modes.remove("exclMOT_5")  # Keep buses
    elif mode_name == "coach":
        excluded_modes.remove("exclMOT_7")  # Keep coaches
    elif mode_name == "ferry":
        excluded_modes.remove("exclMOT_9")  # Keep ferries
    elif mode_name == "school_bus":
        excluded_modes.remove("exclMOT_11")  # Keep school buses

    # print(f"Excluded modes after un-excluding: {excluded_modes}")

    # Add exclusion parameters
    for mode in excluded_modes:
        params[mode] = "true"

    response = requests.get(endpoint, headers=headers, params=params)
    departures = []

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return departures  # Early return if the response is not successful

    data = response.json()
    if "stopEvents" not in data:
        print(f"'stopEvents' not found in response for stop ID {stop_id} for mode {mode_name}")
        return departures  # Early return if no stop events are found

    # else the response is successful, so we can proceed to process the data
    # print(f"Successfully fetched departures for stop ID {stop_id} for mode {mode_name}")
    
    ############ Now have the data, time to transform it
    
    for i, service in enumerate(data["stopEvents"]):

        ###### Timing

        # Get minutes until departure
        departure_time = service.get("departureTimeEstimated", service.get("departureTimePlanned"))
        # print(f"Departure time: {departure_time}")
        if not departure_time:
            print(f"Error: No departure time available for service {i}")
            continue  # Skip if no departure time is available - error handling

        departure_dt = datetime.fromisoformat(departure_time.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        minutes_until_departure = int((departure_dt - now).total_seconds() // 60)
        # print(f"Minutes until departure: {minutes_until_departure}")

        # Check for delays by subtracting the planned departure time from the estimated departure time, then convert to minutes
        if "departureTimeEstimated" in service and "departureTimePlanned" in service:
            # print(f"Estimated departure time: {service['departureTimeEstimated']}")
            estimated_dt = datetime.fromisoformat(service["departureTimeEstimated"].replace("Z", "+00:00"))
            planned_dt = datetime.fromisoformat(service["departureTimePlanned"].replace("Z", "+00:00"))
            delay = int((estimated_dt - planned_dt).total_seconds() // 60)
            # print(f"Delay: {delay} minutes")

        ###### Destination

        # Extract destination and via information
        destination_full = service["transportation"]["destination"]["name"]
        # print(f"Destination full: {destination_full}")
        destination = destination_full.split(" via ")[0]
        # exclude via if the via station is the current station
        # print(f"Via (before excluding current station if applicable): {destination_full.split(' via ')[-1]}")
        via = destination_full.split(" via ")[-1] if " via " in destination_full and destination_full.split(" via ")[-1] != stop_name else ""
        # print(f"Via (after excluding current station if applicable): {via}")
        # print(f"Current station: {stop_name}")

        # Get the line information
        line = service["transportation"]["disassembledName"]
        # print(f"Line: {line}")
        

        ###### Formatting
        
        # Get the type of transport from the service data
        # stopEvents > transportation > product > class
        type_of_transport = service["transportation"]["product"]["class"]
        # print(f"Type of transport (as a number): {type_of_transport}")
        # Map the type to a more readable format
        type_of_transport = type_lookup_table.get(type_of_transport, "unknown")
        # print(f"Type of transport (as a string) (after lookup): {type_of_transport}")
        # print(f"Type: {type}")

        # Format platform
        platform = service["location"]["properties"].get("platform", "")
        # print(f"Platform: {platform}")
        platform_raw = service["location"]["parent"]["disassembledName"]
        # print(f"Platform raw: {platform_raw}")
        platform_display = format_platforms(platform, type_of_transport, service, platform_return_raw, platform_raw)
        # print(f"Platform display (after formatting): {platform_display}")
        
        # Get colour codes from line
        line_colour = colour_codes(line, type_of_transport)
        # print(f"Line colour: {line_colour}")
        
        
        # Get the occupancy information if available
        if "occupancy" in service["location"]["properties"]:
            occupancy = service["location"]["properties"]["occupancy"]
            # print(f"Occupancy: {occupancy}")
        
        
        alerts = []
        '''
        alert = [
            {
                "subtitle": "Alert subtitle",
                "content": "Alert content"
            }
        ]
        '''
        
        # Get alert information if it exists
        # if "infos" exists in service, then print it for now
        if "infos" in service:
            # TODO - Need a way to filter out alerts that apply to this specific departure - might not be possible with this API, might need to use the add_info API instead.
            # Filter out certain alert types
            # import pprint
            # pprint.pprint(f"Alerts: {service['infos']}")
            pass
            
            # for each alert, just print the subtitle
            for alert in service["infos"]:
                # if priority == "veryLow" then continue
                if "priority" in alert and alert["priority"] == "veryLow":
                    # print(f"Skipping very low priority alert: {alert['priority']}")
                    continue
                
                # assign an alert type to either alert or info
                # if the content contains "trains are not running" (case insensitive) then set the alert type to "alert", else the alert is just "info"
                if "content" in alert and "trains are not running" in alert["content"].lower():
                    alert_type = "alert"
                    # print(f"Alert type: {alert_type}")
                elif "content" in alert and "buses replacing trains" in alert["content"].lower():
                    alert_type = "alert"
                    # print(f"Alert type: {alert_type}")
                elif "content" in alert and "allow extra travel time" in alert["content"].lower():
                    alert_type = "alert"
                    # print(f"Alert type: {alert_type}")
                else:
                    alert_type = "info"
                    # print(f"Alert type: {alert_type}")
                
                # if properties > infoType != "lineInfo" then continue
                if "infoType" in alert["properties"] and alert["properties"]["infoType"] != "lineInfo":
                    # print(f"Skipping non-lineInfo alert: {alert['properties']['infoType']}")
                    continue
                
                if "subtitle" in alert:
                    # print(f"\nAlert Priority: {alert['priority']}.\nAlert title: {alert['subtitle']}.\nAlert full: {alert['content']}")
                    alerts.append({
                        "subtitle": alert["subtitle"],
                        "content": alert["content"],
                        "alert_type": alert_type
                    })
                    pass
                # print(f"Alert: {alerts}")
        
        # Get realtime trip ID to be used later, but not just yet
        realtime_trip_id = service["properties"]["RealtimeTripId"] if "RealtimeTripId" in service["properties"] else None
        # print(f"Realtime trip ID: {realtime_trip_id}")
        
        ###### Filtering

        # Skip excluded bus routes now that I've got type_of_transport and line
        if type_of_transport == "bus" and routes_to_exclude is not None and line in routes_to_exclude:
            print(f"Excluding bus route: {line}")
            continue

        ###### Done - add this service to the list of departures

        # Append the calculated values to the departures list
        departures.append({
            "isRealtimeControlled": service.get("isRealtimeControlled", False),
            "stop_name": stop_name, # use this as I'll actually have multiple stops on the same dashboard
            "stop_id": stop_id,
            "platform": platform_display,
            "destination": destination,
            "via": via,
            "minutes_until_departure": minutes_until_departure,
            "delay": delay if "delay" in locals() else 0,
            "line": line,
            "line_colour": line_colour,
            "type_of_transport": type_of_transport,
            "realtime_trip_id": realtime_trip_id,
            "occupancy": occupancy if "occupancy" in locals() else None,
            "alerts": alerts if "alerts" in locals() else None,
        })
        
        # print(f"Appended departure number {i} - full details: {departures[-1]}")

    return departures



def generate_json_output(every_departure, output_path):
    """
    Generate a JSON file with the departures information, including color codes.

    Args:
        every_departure (list): List of departures with relevant details.
        output_path (str): Path to save the generated JSON file.
    """
    try:
        # Save the departures list as a JSON file
        with open(output_path, "w") as file:
            json.dump(every_departure, file, indent=4)
        print(f"JSON file generated: {output_path}")
    except Exception as e:
        print(f"Error generating JSON file: {e}")

def print_in_terminal(every_departure):
    # Define color codes for terminal printing
    colors = {
        "train": "\033[33m",  # Yellow for trains
        "light_rail": "\033[31m",  # Red for light rails
        "ferry": "\033[32m",  # Green for ferries
        "bus": "\033[34m",  # Blue for busses
        "metro": "\033[36m",  # Cyan for metros
        "coach": "\033[35m",  # Magenta for coaches
        "reset": "\033[0m"  # Reset to default; stop printing in colour
    }

    # Printing for terminal using colour codes
    print(f"Found {len(every_departure)} departures")
    for departure in every_departure:
        type_of_transport = departure["type_of_transport"]
        line_colour = colors.get(type_of_transport, colors["reset"])
        # Print the departure information in the terminal using string formatting (e.g., the :<20 padding stuff)
        print(f"{line_colour}Departure from {departure['stop_name']:<20} {departure['platform']:<20} {departure['destination']:<20} {departure['via']:<20} {departure['minutes_until_departure']:>3} min {departure['delay']:>3} min delay Line: {departure['line']:>3} Type: {type_of_transport}{colors['reset']}")


def main():
    every_departure = []

    # Get the departures for each station in the stops_to_show stops
    for station in stops_to_show:
        for mode in station["modes"]:
            routes_to_exclude = mode.get("routes_to_exclude", [])  # Get routes_to_exclude if it exists, otherwise use an empty list
            departures = get_departures(
                station["station_name"],
                station["stop_id"],
                mode,
                routes_to_exclude
            )
            every_departure.extend(departures)
          
    # Sort the list of departures by minutes until departure
    every_departure.sort(key=lambda x: x["minutes_until_departure"])
    
    # Exclude departures that are less than 0 minutes until departure
    every_departure = [departure for departure in every_departure if departure["minutes_until_departure"] >= 0]
    
    # Can introduce more filtering here - such as a maximum number of departures to show, or a maximum number of minutes until departure to show.
      
    # Print the departures in the terminal
    print_in_terminal(every_departure)

    # JSON - generate the JSON file which will be used by the html/css/javascript frontend file
    output_path = r"C:\Users\Matth\OneDrive\Personal\Projects\Programming\TFNSW\output.json"
    generate_json_output(every_departure, output_path)


stops_to_show = None
# if preconfigured_stops is commented out, then as for the user input
if preconfigured_stops is None:
    # Get user input for station names and modes
    user_input = input("Enter station names and modes (e.g., 'Parramatta (train, bus); Parramatta Square (light_rail); Parramatta Wharf (ferry)'): ")
    
    # Use the user input to get the station IDs and modes
    stops_to_show = get_station_ids_from_station_names_and_modes(user_input)
    
    # Show all platform information
    platform_return_raw = True
else:
    # preconfigured_stops does exist, use that
    stops_to_show = preconfigured_stops
    platform_return_raw = False # Show the formatted platform name for your hardcoded station


refresh_in_seconds = 60  # Refresh every 60 seconds
refresh_coutner = 0
if __name__ == "__main__":
    while True:  # Run indefinitely
        max_retries = 3
        for attempt in range(max_retries):
            try:
                main()
                refresh_coutner += 1
                print(f"Refresh count: {refresh_coutner}")
                break  # Exit the retry loop if main() succeeds
            except Exception as e:
                print(f"Attempt {attempt + 1} failed with error: {e}")
                if attempt == max_retries - 1:
                    print("Maximum retries reached. Skipping this cycle.")
                    break  # Skip to the next cycle after max retries
            print(f"Retrying in {refresh_in_seconds} seconds...")
            time.sleep(refresh_in_seconds)
        print(f"Waiting {refresh_in_seconds} seconds before the next run...")
        time.sleep(refresh_in_seconds)
