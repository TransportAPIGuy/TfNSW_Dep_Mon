import requests
import time
from datetime import datetime, timezone
import sys  # Add this import for sys.exit()
import json  # Import the JSON module

API_KEY = "PASTE YOUR API KEY HERE"
output_path = r"PASTE YOUR FILE PATH HERE"


def get_departures(type, stop_id, excluded_modes, min_departure_time, max_departure_time, number_of_services_to_return, routes_to_exclude):
    """
    Get departures for a specific transport type.
    
    Args:
        type (str): The type of transport (e.g., "train", "bus", "ferry", "light_rail") manually determined by me. Useful for debugging.
        stop_id (str): The stop ID for the transport type.
        excluded_modes (list): List of modes to exclude (e.g., ["exclMOT_1", "exclMOT_2"]).
        line_name (str): The line name to assign to the departures (e.g., "T1", "L4").
        min_departure_time (int): Minimum minutes until departure to include.
        max_departure_time (int): Maximum minutes until departure to include.
    
    Returns:
        list: A list of departures with relevant details.

        list contains dictionaries with keys:
            - platform: The platform number (if available).
            - destination: The destination of the service.
            - via: The via point of the service (if available).
            - minutes_until_departure: Minutes until departure.
            - line: The line name of the service.
                The line will be used to determine the colours for the HTML table
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
        "itdDate": current_date,  # Use the current date
        "itdTime": current_time,  # Use the current time
        "excludedMeans": "checkbox",
        "includeNonPassengerTrips": "false",
    }

    # Add exclusion parameters
    for mode in excluded_modes:
        params[mode] = "true"

    response = requests.get(endpoint, headers=headers, params=params)

    departures = []
    if response.status_code == 200:
        data = response.json()

        if "stopEvents" in data:
            for i, service in enumerate(data["stopEvents"]):
                if number_of_services_to_return is not None and i >= number_of_services_to_return:
                    break
                # Get minutes until depature using departure time (estimated or planned)
                departure_time = service.get("departureTimeEstimated", service.get("departureTimePlanned"))
                departure_dt = datetime.fromisoformat(departure_time.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                minutes_until_departure = int((departure_dt - now).total_seconds() // 60)

                # if both departureTimeEstimates and departureTimePlanned exist, then calculate the delay. Only care about delays more than a few minutes
                if "departureTimeEstimated" in service and "departureTimePlanned" in service:
                    estimated_dt = datetime.fromisoformat(service["departureTimeEstimated"].replace("Z", "+00:00"))
                    planned_dt = datetime.fromisoformat(service["departureTimePlanned"].replace("Z", "+00:00"))
                    delay = int((estimated_dt - planned_dt).total_seconds() // 60)
                    # if delay greater than 5 minutes then print it. # TODO - maybe add delay to the departures list. Can format the minutes until departure to red if delayed
                    if delay > 5:
                        # Print in the terminal with information about the service
                        print(f"Delay: {delay} minutes for service {i} - {service['transportation']['disassembledName']}")

                # Skip services outside the specified time range, add the rest to the departures list
                if min_departure_time <= minutes_until_departure <= max_departure_time:
                    # Calculate the required fields
                    destination_full = service["transportation"]["destination"]["name"]
                    destination = destination_full.split(" via ")[0]  # Extract the main destination
                    platform = service["location"]["properties"].get("platform", "")
                    line = service["transportation"]["disassembledName"]
                    via = destination_full.split(" via ")[-1] if " via " in destination_full else ""
                    platform_display = (
                        "" if line in ["L4", "F3"] else
                        (f"Platform {platform[3:]}" if platform.startswith("PTA") else f"Stand {platform}" if platform else "")
                    )
                    
                    # if the mode is a bus, and the line is contained in the routes_to_exclude, then skip it
                    if type == "bus" and routes_to_exclude is not None and line in routes_to_exclude:
                        # print(f"Skipping bus {line} as it is in the excluded routes list")
                        continue

                    # Append the calculated values to the departures list
                    departures.append({
                        "platform": platform_display,
                        "destination": destination,
                        "via": via,
                        "minutes_until_departure": minutes_until_departure,
                        "line": line
                    })
                    
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

    return departures

def colour_codes(line):
    # Bus routes never have less than 3 characters - even bus replacement busses. If you needed to account for the F10 you'd have to add a check for that here.
    if len(line) >= 3:
        # If the line is a 3-digit number, starts with 'T' or 'M' followed by digits, or starts with a 3-digit number followed by 'X' or 'N', it's a bus
        # e.g., Metro buses (e.g., M91), eXpress busses (e.g., 811X), Night versions of daytime busses (e.g., 500N. Not Nightride busses e.g., N50), and T-way busses (e.g., T80)
        if (
            (line.isdigit() and len(line) == 3) or
            ((line[0] == "T" or line[0] == "M") and line[1:2].isdigit() and len(line) > 2) or
            (line[0:3].isdigit() and (line[3] == "X" or line[3] == "N"))
        ):
            line = "Bus"

        # If the line has a 2-digit number, then 'T', then another number, it's a train replacement bus
        elif line.startswith("T") and line[1:3].isdigit() and len(line) > 3 and line[3] == "T" and line[4:].isdigit():
            line = "Train_replacement_bus"

        # If the line starts with 'N', and then has a 2-digit number, it's a night bus
        elif line.startswith("N") and line[1:].isdigit() and len(line) == 3:
            line = "Night_Bus"

    # Define the color codes
    colour_codes = {
        "T1": {
            "dark": "#F99D1C",
            "light": "#FEE7C7"
        },
        "T2": {
            "dark": "#0098CD",
            "light": "#BFE5F2"
        },
        "T5": {
            "dark": "#C4258F",
            "light": "#F0C8E3"
        },
        "T7": {
            "dark": "#6F818E",
            "light": "#DBDFE3"
        },
        "BMT": {
            "dark": "#F99D1C",
            "light": "#FDE6C6"
        },
        "CCN": {
            "dark": "#D11F2F",
            "light": "#F3C7CB"
        },
        "L4": {
            "dark": "#CD0D4D",
            "light": "#F2C2D2"
        },
        "F3": {
            "dark": "#009E4D",
            "light": "#BFE7D2"
        },
        "Bus": {
            "dark": "#83D0F5",
            "light": "#E0F3FC"
        },
        "Night_Bus": {
            "dark": "#001b3d",
            "light": "#BFC6CE"
        },
        "Train_replacement_bus": {
            "dark": "#565658",
            "light": "#D5D5D5"
        },
        "Default": {
            "dark": "#000000",
            "light": "#FFFFFF"
        }
    }

    # Use line to get the color codes - if not found, use default values
    if line in colour_codes:
        # print the line and key
        #print(f"Line: {line} Key: {colour_codes[line]}")
        return colour_codes[line]
    else:
        print(f"Line: {line} - no matching colour codes. Using default colours (black and white)")
        return colour_codes["Default"]

def generate_html(every_departure, output_path):
    """
    I have removed the HTML stuff here. Below is what should be converted to output.json.
    """

    # Write the table body using the information from every_departure
    for item in every_departure:
        # Get the color codes for the current line
        colors = colour_codes(item['line'])
        light_color = colors['light']
        dark_color = colors['dark']

        # Add a row
        html_content += "<tr>"

        # First column (line) with dark color and bold white text
        html_content += f"<td class='category' style='background-color: {dark_color};'>{item['line']}</td>"

        # Destination and platform in the second column with light color
        destination = f"<span class='destination'>{item['destination']}</span>"
        if item.get('via', ''):  # Add 'via' if it exists
            destination += f" <span class='regular' style='font-size: 0.9em;'>via {item['via']}</span>"

        # Only add the platform and <br> if the platform exists
        platform = f"<br><span class='regular'>{item['platform']}</span>" if item.get('platform', '') else ""
        html_content += f"<td class='content expand' style='background-color: {light_color};'>{destination}{platform}</td>"

        # Minutes until departure in the third column with light color and black text
        minutes_display = "Now" if item['minutes_until_departure'] == 0 else f"{item['minutes_until_departure']} min"
        html_content += f"<td class='time' style='background-color: {light_color}; color: black;'>{minutes_display}</td>"

        html_content += "</tr>"

    # Print the HTML table footer

    # Save the HTML file to a specific directory
    with open(output_path, "w") as file:
        file.write(html_content)

    print(f"HTML file generated: {output_path}")

def generate_json_output(every_departure, output_path):
    """
    Generate a JSON file with the departures information, including color codes.

    Args:
        every_departure (list): List of departures with relevant details.
        output_path (str): Path to save the generated JSON file.
    """
    try:
        # Add color codes to each departure
        for departure in every_departure:
            colors = colour_codes(departure['line'])
            departure['line_color_dark'] = colors['dark']
            departure['line_color_light'] = colors['light']

        # Save the departures list as a JSON file
        with open(output_path, "w") as file:
            json.dump(every_departure, file, indent=4)
        print(f"JSON file generated: {output_path}")
    except Exception as e:
        print(f"Error generating JSON file: {e}")

# Update the main function to call the new generate_json function
def main():
    every_departure = []

    every_departure.extend(get_departures(
        type="train",
        stop_id="10101100",  # Trains from Central
        excluded_modes=["exclMOT_2", "exclMOT_4", "exclMOT_5", "exclMOT_7", "exclMOT_9", "exclMOT_11"],  # Exclude all but trains
        min_departure_time=5,
        max_departure_time=60,
        number_of_services_to_return=20,
        routes_to_exclude=None
    ))

    every_departure.extend(get_departures(
        type="light_rail",
        stop_id="10101100",  # Light Rails from Central
        excluded_modes=["exclMOT_1", "exclMOT_2", "exclMOT_5", "exclMOT_7", "exclMOT_9", "exclMOT_11"],  # Exclude all but light rails
        min_departure_time=5,
        max_departure_time=60,
        number_of_services_to_return=10,
        routes_to_exclude=None
    ))

    every_departure.extend(get_departures(
        type="ferry",
        stop_id="10101103",  # Ferries from Circular Quay
        excluded_modes=["exclMOT_1", "exclMOT_2", "exclMOT_4", "exclMOT_5", "exclMOT_7", "exclMOT_11"],  # Exclude all but ferries
        min_departure_time=5,
        max_departure_time=60,
        number_of_services_to_return=5,
        routes_to_exclude=None
    ))

    every_departure.extend(get_departures(
        type="bus",
        stop_id="10101100",  # Buses from Central
        excluded_modes=["exclMOT_1", "exclMOT_2", "exclMOT_4", "exclMOT_7", "exclMOT_9", "exclMOT_11"],  # Exclude all but buses
        min_departure_time=5,
        max_departure_time=60,
        number_of_services_to_return=20,
        routes_to_exclude=None  # Blacklisting specific routes
    ))

    # Sort the list of departures by minutes until departure
    every_departure.sort(key=lambda x: x['minutes_until_departure'])

    number_of_departures_to_return = 16
    # Limit the number of departures to return to the specified number
    if len(every_departure) > number_of_departures_to_return:
        every_departure = every_departure[:number_of_departures_to_return]

    # Printing for terminal
    print(f"Found {len(every_departure)} departures")
    for departure in every_departure:
        print("{:<10} {:<30} {:<10} {:<15}".format(
            departure['line'],
            departure['destination'],
            f"{departure['minutes_until_departure']} min",
            departure['platform'] if 'platform' in departure else ""
        ))

    # Generate the JSON file
    generate_json_output(every_departure, output_path)

refresh_in_seconds = 60  # Refresh every 60 seconds
refresh_coutner = 0

if __name__ == "__main__":
    while True:  # Run indefinitely
        max_retries = 3
        for attempt in range(max_retries):
            try:
                main()
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
