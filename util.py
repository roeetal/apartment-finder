import settings
import math
import googlemaps

def coord_distance(lat1, lon1, lat2, lon2):
    """
    Finds the distance between two pairs of latitude and longitude.
    :param lat1: Point 1 latitude.
    :param lon1: Point 1 longitude.
    :param lat2: Point two latitude.
    :param lon2: Point two longitude.
    :return: Kilometer distance.
    """
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    km = 6367 * c
    return km

def in_box(coords, box):
    """
    Find if a coordinate tuple is inside a bounding box.
    :param coords: Tuple containing latitude and longitude.
    :param box: Two tuples, where first is the bottom left, and the second is the top right of the box.
    :return: Boolean indicating if the coordinates are in the box.
    """
    if box[0][0] < coords[0] < box[1][0] and box[1][1] < coords[1] < box[0][1]:
        return True
    return False

def post_listing_to_slack(sc, listing):
    """
    Posts the listing to slack.
    :param sc: A slack client.
    :param listing: A record of the listing.
    """
    desc = "{0} | {1} | {2} | {3} | <{4}>".format(listing["area"], listing["price"], listing["bart_dist"], listing["name"], listing["url"])
    image_url=""
    if listing["geotag"] != None:
        image_url = """https://maps.googleapis.com/maps/api/staticmap?size=500x400"""+\
        """&markers=color:blue%7Clabel:S%7C"""+str(settings.WORK_COORD[0])+","+str(settings.WORK_COORD[1])+\
        """&markers=color:red%7Clabel:A%7C"""+str(listing["geotag"][0])+","+str(listing["geotag"][1])+"""&key="""+settings.GOOGLE_TOKEN_MAPS
        attachments = [{"title": "map",
                        "image_url": image_url}]
    else:
        attachments = None
    sc.api_call(
        "chat.postMessage", channel=settings.SLACK_CHANNEL, text=desc,
        username='pybot', icon_emoji=':robot_face:'
    )

def find_points_of_interest(geotag, location):
    """
    Find points of interest, like transit, near a result.
    :param geotag: The geotag field of a Craigslist result.
    :param location: The where field of a Craigslist result.  Is a string containing a description of where
    the listing was posted.
    :return: A dictionary containing annotations.
    """
    area_found = False
    area = ""
    min_dist = None
    near_bart = False
    bart_dist = "N/A"
    bart = ""
    distance_matrix_result=""
    # Look to see if the listing is in any of the neighborhood boxes we defined.

    if geotag is not None:
        for a, coords in settings.BOXES.items():
            if in_box(geotag, coords):
                area = a
                area_found = True
        # get googlemaps data for the distance and duration to the specified destination
        gmaps = googlemaps.Client(key=settings.GOOGLE_TOKEN_DISTANCE)
        distance_matrix = gmaps.distance_matrix(geotag, settings.DESTINATIONS, mode=settings.MODE, language=settings.LANG, avoid=settings.AVOID, units=settings.UNITS, departure_time=settings.DEPART_TIME, arrival_time=settings.ARRIV_TIME, transit_mode=settings.TRANS_MODE, transit_routing_preference=settings.TRANS_ROUT_PREF, traffic_model=settings.TRAFFIC_MODEL)
        gplaces = googlemaps.Client(key=settings.GOOGLE_TOKEN_PLACES)
        places_list = gplaces.places_nearby(geotag, settings.radius, settings.keyword, settings.LANG, settings.min_price, settings.max_price, settings.name, settings.open_now, settings.rank_by, settings.TYPE, page_token=None)
        if distance_matrix['rows'][0]['elements'][0]['status'] != 'ZERO_RESULTS':
            time = distance_matrix['rows'][0]['elements'][0]['duration']['text']
            distance = distance_matrix['rows'][0]['elements'][0]['distance']['text']
            distance_matrix_result = "{0} in {1}".format(distance, time)
        else:
            distance_matrix_result = "Google Error."
    else:
        distance_matrix_result= "Not enough location information available."

    # Check to see if the listing is near any transit stations.
    for station, coords in settings.TRANSIT_STATIONS.items():
        dist = coord_distance(coords[0], coords[1], geotag[0], geotag[1])
        if (min_dist is None or dist < min_dist) and dist < settings.MAX_TRANSIT_DIST:
            bart = station
            near_bart = True

        if (min_dist is None or dist < min_dist):
            bart_dist = dist

    # If the listing isn't in any of the boxes we defined, check to see if the string description of the neighborhood
    # matches anything in our list of neighborhoods.
    if len(area) == 0:
        for hood in settings.NEIGHBORHOODS:
            if hood in location.lower():
                area = hood

    return {
        "area_found": area_found,
        "area": area,
        "near_bart": near_bart,
        "bart_dist": bart_dist,
        "bart": bart
        "distance_matrix_result": distance_matrix_result
    }
