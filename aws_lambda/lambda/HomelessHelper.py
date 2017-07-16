'''
Title: Basic Needs Chat Bot | AngelHack, Seattle 2017
Team Members: Brett Bejcek, Mayuree Binjolkar, Yana Sosnovskaya, Orysya Stus
Description: A chat bot to help the homeless population of Seattle.
'''

import math
import dateutil.parser
import datetime
import time
import os
import logging
import requests
import bs4
import html
import json
import string

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

app_id = 'INSERT APP ID HERE'
app_code = 'INSERT APP CODE HERE'
CLIENT_ID = 'INSERT CLIENT_ID HERE'
CLIENT_SECRET = 'INSERT CLIENT_SECRET HERE'

""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """

def get_slots(intent_request):
    return intent_request['currentIntent']['slots']

def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }

def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


# A different version of close with image return capabilities.
def close_img(session_attributes, fulfillment_state, message, url):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            "responseCard": {
                "version": 1,
                "contentType": "application/vnd.amazonaws.card.generic",
                "genericAttachments": [
                {
                "title":"Your Route",
                "imageUrl":url
                }
                                    ]
                            },
            'message': message
                        }
                }
    return(response)

def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


""" --- Helper Functions --- """

# Returns (lat, lon) combination of text input
def GetLatLon(location):
    location = location.replace(" ", "+")
    URL = "https://geocoder.cit.api.here.com/6.2/geocode.xml?app_id="+app_id+"&app_code="+app_code+"&searchtext="+location
    r = requests.get(url=URL)
    soup = bs4.BeautifulSoup(r.text, 'html5lib')
    soup = soup.body.response.navigationposition.contents
    lat = soup[0].contents[0]
    lon = soup[1].contents[0]
    return lat, lon

# Returns 3 places of specified type that are nearby (lat, lon)
def GetPlace(lat, lon, place):
    place_dict = {}
    place = place.replace(" ", "+")
    URL = "https://places.demo.api.here.com/places/v1/discover/search?at="+lat+"%2C"+lon+"&q="+place+"&tf=html&app_id="+app_id+"&app_code="+app_code
    r = requests.get(url=URL)
    soup = json.loads(bs4.BeautifulSoup(r.text, 'html5lib').html.body.get_text())
    for i in range(len(soup['results']['items'])):
        place_dict[soup['results']['items'][i]['title']] = soup['results']['items'][i]['vicinity']
    length = len(place_dict)
    if len(place_dict) > 3:
        length = 3
    string = ""
    for i in range(0,length):
        key = list(place_dict.keys())[0]
        value = place_dict.pop(key)
        string = string + "     " + "["+key + " : " + value + "]"
    return(string)

# Return Seattle Weather
def GetWeather():
    URL = 'http://api.aerisapi.com/observations/seattle,wa?'+'client_id='+CLIENT_ID+'&client_secret='+CLIENT_SECRET
    r = requests.get(url=URL)
    soup = json.loads(bs4.BeautifulSoup(r.text, 'html5lib').html.body.get_text())['response']
    general = soup['ob']['weather'].lower()
    humid = soup['ob']['humidity']
    temp = soup['ob']['tempF']
    precip = soup['ob']['precipIN']
    wind = soup['ob']['windMPH']
    snwd = soup['ob']['snowDepthIN']
    return(general, humid, temp, precip, wind, snwd)

# Return distance and time of route from (lat, lon) to (lat1, lon1)
def GetRoute(lat,lon,lat1,lon1):
    mode='fastest%3Bpedestrian'
    URL = "https://route.cit.api.here.com/routing/7.2/calculateroute.xml?app_id="+app_id+"&app_code="+app_code+"&waypoint0="+lat+"%2C"+lon+"&waypoint1="+lat1+"%2C"+lon1+"&mode="+mode
    r = requests.get(url=URL)
    soup = bs4.BeautifulSoup(r.text, 'html5lib')
    try:
        time = round(int(soup.body.response.traveltime.contents[0])/60, 1)
        distance = round(int(soup.body.response.distance.contents[0])/1609, 1)
        return distance, time
    except:
        return 99,99

# Returns map of Route
def GetMapRoute(lat,lon,lat1,lon1):
    lc='1652B4'
    lw='6'
    t='0'
    ppi='320'
    w='400'
    h='600'
    URL = "https://image.maps.cit.api.here.com/mia/1.6/routing?app_id="+app_id+"&app_code="+app_code+"&waypoint0="+lat+"%2C"+lon+"&waypoint1="+lat1+"%2C"+lon1+"&lc="+lc+"&lw="+lw+"&t="+t+"&ppi="+ppi+"&w="+w+"&h="+h
    return(URL)

def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }

""" --- Functions that control the bot's behavior --- """

def get_places(intent_request):

    currentLocation = get_slots(intent_request)["Location"]
    typeOfPlace = get_slots(intent_request)["typeOfPlace"]

    x,y = GetLatLon(currentLocation)
    places = GetPlace(x,y,typeOfPlace)
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': 'Nearby places include: {}. If you see a place you like, you may find it helpful to ask for directions from us.'.format(places)})

def get_weather(intent_request):

    general, humid, temp, precip, wind, snwd = GetWeather()

    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content':'Right now, it is {}. The current temperature is {}*F. Chance of rain is {}%. There are {}MPH winds. The snow-depth is {}.'.format(general,temp,precip,wind,snwd)})

def get_help(intent_request):

    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content':'Hello and welcome to Basic Needs. With our texting application, you can see what is around, ask for directions, get weather updates, get locations of free classes, see where the nearest wifi spots are, and report incidents.'})


def get_wifi(intent_request):

    wifi = [('Starbucks', '1912 Pike Pl', ('49.67807', '-124.99319')),
    ('Starbucks Coffee Works', '107 Pike St', ('45.3637143', '-75.6266729')),
    ('Barnes & Noble', '600 Pine St, #107', ('49.15622', '-123.9398822')),
    ('The Roosevelt Hotel', '1531 7th Ave', ('49.2060616', '-122.9373887')),
    ('Grand Hyatt Seattle', '721 Pine St', ('48.43624', '-123.39273')),
    ('Six Arms', '300 E Pike St', ('45.3625104', '-75.6257203')),
    ('Bauhaus Books & Coffee', '301 E Pine St', None),
    ('Starbucks', '1125 4th Ave', ('49.3761636', '-121.4357941')),
    ('Seattle Ferry Terminal ', '801 Alaskan Way', None),
    ('Seattle Public Library', '1000 4th Ave', ('49.2065678', '-122.92326')),
    ('Renaissance Seattle Hotel', '515 Madison St', ('49.8912551', '-97.2033325')),
    ('Caffe Vita', '1005 E Pike St', ('38.9861', '-84.82811')),
    ('Caffe Umbria', '320 Occidental Ave. S', ('22.1474514', '-101.0415156')),
    ('Café Presse', '1117 12th Ave', ('50.5096884', '-104.61769')),
    ('Skillet Diner', '1400 E Union St', ('43.95679', '2.88693')),
    ('Zoka Coffee', '129 Central Way', None),
    ('Apple Store', '213 Bellevue Sq', ('50.56245', '5.62475')),
    ('Hyatt Regency Bellevue', '900 Bellevue Way NE', ('41.13647', '-95.89249')),
    ('Café Cesura', '1015 108th Ave NE', ('50.3985924', '-105.5089704')),
    ('Pro Sports Club', '4455 148th Ave NE', None),
    ('Panera Bread', '4004 Factoria Blvd SE', None),
    ('Seattle- Tacoma International Airport', '17801 International Blvd', ('-12.15885', '-76.97894')),
    ('Hilton Seattle Aitport & Conference Center', '17620 Ibternational Blvd', None),
    ('United Club', 'Concourse A, near Gate 9', None),
    ("Tully's Coffee ", '3080 148th Ave SE, #113', None),
    ('Starbucks', '3181 156th Ave', None),
    ('DoubleTree by Hilton Seattle Airport', '18740 International Blvd', ('40.75538', '-75.26844')),
    ('Embassy Suits', '3225 158th Ave SE', None),
    ('Hampton Inn', '19445 International Blvd', None),
    ('Nordstorm', '100 Southcenter Shopping', None),
    ('Fairfield Inn Seattle Sea-Tac Airport', '19631 International Blvd', None),
    ('Westfield Southcenter', '2800 Southcenter Mall',('39.96928', '-85.3302412')),
    ('Panera Bread', '921 N 10th St, Ste E', ('49.51964', '-115.75179')),
    ("Vince's Coffee Shop", '401 Olympia Ave NE, #102',('47.05997', '-122.87741')),
    ('Starbucks', '14022 SE Petrovitsky Rd', None)]

    return close(intent_request['sessionAttributes'], 'Fulfilled', {'contentType': 'PlainText',
    'content':'You can get wifi at these nearest locations: {}.'.format(wifi[:2])})

def get_education(intent_request):

    educ = [['King County Library System', 'Computer Basics Training', '960 Newport Way NW, Issaquah, WA, 98027'],
    ['Seattle Public Library','Computer Classes','8635 Fremont Ave N, Seattle, WA, 98103'],
    ['Boys&Girls Clubs of King County','After-school Program','201 19th Ave, Seattle, WA, 98122'],
    ['Coyote Central', 'Electronics Classes', '2300 E Cherry St, Seattle, WA, 98122'],
    ['FAMILYWORKS', 'Pre-Employment Services', '1501 N 45th St, Seattle, WA, 98103'],
    ["GAY CITY: Seattle's LGBTQ Center", 'Queercore', '517 E Pike St, Seattle, WA, 98122'],
    ['Goodwill', 'Basic Skills& GED Preparation', '700 Dearborn Pl S, Seattle, WA, 98144'],
    ['Greenwood Senior Center', 'Computer Technology Center', '525 N 85th St, Seattle, WA, 98103'],
    ['Helping Link', 'ELS Citizenship Computer Literacy Program', '1032 S Jackson St, Suite C, Seattle, WA, 98104'],
    ["Jubulee Women's Center", 'Computer Basics Training', '620 18th Ave E, Seattle, WA, 98112'],
    ['Lambert House', 'Computer Lab', '1818 15th Ave, Seattle, WA, 98122'],
    ['Museum of History & Industry', 'Maker Day', '860 Terry Ave N, Seattle, WA, 98109'],
    ['Phinney Neighborghood Association','Arts, Scheduling and Community Education Programs','6532 Phinney Ave N, Seattle, WA, 98103'],
    ["Seattle Children's Research Institute", 'STEM High School Internship Program','1900 9th Ave, Seattle, WA, 98101'],
    ['Seattle Indian Center','Employment Services','1265 S Main St, Suite 105, Seattle, WA, 98144'],
    ['Seattle Parks and Recreation - Community Centers','Recreational Technology','2323 E Cherry St, Seattle, WA, 98122'],
    ['United Indians of all Tribes Foundation','Workforce Investment, Employment, Services','5011 Bernie Whitebear Way, Daybreak Star Center, Seattle, WA, 98199'],
    ['Seattle Public Library', 'ESL Classes', '1000 4th Ave, Seattle, WA, 98104'],
    ['Casa Latina', 'ESL Classes', '317 17th Ave S, Seattle, WA, 98144'],
    ['Center for Multicultural Health','Refugee and Immigrant Resources','1120 E Terrace St, Suite 200, Seattle, WA, 98122'],
    ["Children's Home Society of Washington",'Classes and Support Group','2611 NE 125th St, Suite 145, Seattle, WA, 98125'],
    ['Chinese Information and Service Center','Immigrant Transition Programs','611 S Lane St, Seattle, WA, 98104'],
    ['Literacy Source','Educational Services','3200 NE 125th St, Seattle, WA, 98125'],
    ['North Seattle College','Pre-College Programs','9600 College Way N, Seattle, WA, 98103'],
    ['Seattle Central College','Division of Basic Studies/ABE/ESL','1701 Broadway, Seattle, WA, 98122'],
    ['Farestart', 'Youth Barista Program', '1818 Yale Ave, Seattle, WA, 98101']]

    info = educ[:3]

    return close(intent_request['sessionAttributes'], 'Fulfilled', {'contentType': 'PlainText',
    'content':'Here are some nearby classes: {}.'.format(info)})



def report_incident(intent_request):

    return close(intent_request['sessionAttributes'], 'Fulfilled', {'contentType': 'PlainText',
    'content':'Thank you for reporting the incident. If you need additional support, please call the 24-hour Crisis Hotline at 866-427-4747'})

def get_route(intent_request):

    currentLocation = get_slots(intent_request)["currentLocation"]
    endLocation = get_slots(intent_request)["endLocation"]

    x1,y1 = GetLatLon(currentLocation)
    print(x1,y1)
    x2,y2 = GetLatLon(endLocation)
    print(x2,y2)
    distance, time = GetRoute(x1,y1,x2,y2)
    url = GetMapRoute(x1,y1,x2,y2)
    return close_img(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': '{} is {} miles away and will take {} minutes to get to.'.format(endLocation,distance,time)}, url)


""" --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'GetPlaces':
        return get_places(intent_request)
    elif intent_name == 'GetWeather':
        return get_weather(intent_request)
    elif intent_name == 'GetWifi':
        return get_wifi(intent_request)
    elif intent_name == 'GetRoute':
        return get_route(intent_request)
    elif intent_name == 'GetHelp':
        return get_help(intent_request)
    elif intent_name == 'GetEducation':
        return get_education(intent_request)
    elif intent_name == 'ReportIncident':
        return report_incident(intent_request)
    raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))
    return dispatch(event)
