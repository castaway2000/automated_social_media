import requests
from os import stat, environ, rename
from io import BytesIO
from random import choice
from PIL import Image
from instapy_cli import client
from tweepy import API, OAuthHandler
import facebook
import warnings

import ssl
ssl._create_default_https_context = ssl._create_unverified_context


def get_cliche(location):
    cliches = ["{}\n.\n.", "whats your bucket list destination?", "Look how amazing {} is!", "Wish you were here!",
               "{} is just Wow!", "{} \n.\n.\n", "Where is your next vacation?",
               "Tag the friend you'd love to explore {} with!", "Have you ever seen anything like it?",
               "Guess the place?", "Caption This!", "Have you ever fallen in love with somewhere?",
               "Who wants to come with us on the next trip?", "Where was your most memorable vacation?",
               "What special memory do you have about traveling?", "Where are you off too next?", "Weekend plans?",
               "Don't forget to add {} on your bucket list!", "Hello from {}", "Fill your life with adventures, not things.",
               "I really need a vacation.", "There is a whole world out there to see.", "Remember to live life to the fullest."]
    cta = ['Become a local guide at Tourzan.com',
           "Get your guide with us at Tourzan.com",
           "Get off the beaten trail with Tourzan.com",
           "Make local friends around the world with Tourzan.com",
           "Follow us on twitter, facebook and instagram at @tourzanhq"]
    selection = choice(cliches)
    if '{}' in selection:
        selection = selection.format(location['full_location'])
    out = selection + '\n' + choice(cta)
    if location['instagram'] is not None:
        out = selection + '\n\n' + choice(cta) + "\n\nphotographer's instagram: " + '@{}'.format(location['instagram'])
    return out


def get_facebook_content(data):
    content = get_cliche(data)
    if data['about'] is not None and len(data['about']) > 10:
        content += '\n\nHere is what the photographer has to say about their photo:\n{}'.format(data['about'])
    return content


def get_twitter_content(data):
    content = get_cliche(data)
    return content


def get_instagram_content(data):
    content = get_cliche(data)
    if data['about'] is not None and len(data['about']) > 10:
        content += '\n\nHere is what the photographer has to say about their photo:\n{}'.format(data['about'])
    hashtags = "\n.\n.\n.\n#travel #travelphotography #travelblogger #traveling #travelgram #passionpassport " \
               "#travelguide #traveltour #tour #tours #tourguide #traveler #traveltheworld #travelislife " \
               "#travelingram #travelblog #travelnow #travelwithme #travelphoto #travelaroundtheworld #travelpic " \
               "#travellover #travelphotos #traveldiary #travelworld #instatravel #instatraveling"
    loc = data['full_location'].strip().split(',')
    try:
        if loc:
            tags = " #{} #{}".format("".join(loc[0].split()), "".join(loc[1].split()))
            if len(loc) > 2:
                tags = " #{} #{} #{}".format("".join(loc[0].split()), "".join(loc[1].split()), "".join(loc[2].split()))
    except IndexError:
        tags = " #{}".format("".join(data['full_location']))
    content += hashtags
    content += tags
    return content


def post_to_instagram(image):
    username = environ.get('instagram_username')
    password = environ.get('instagram_password')
    cookie_file = './{}_ig.json'.format(username)
    with client(username, password, write_cookie_file=True, cookie_file=cookie_file) as cli:
        cli.upload(image['image'], get_instagram_content(image))


def post_to_twitter(image):
    APP_KEY = environ.get('TWITTER_KEY')
    APP_SECRET = environ.get('TWITTER_SECRET')
    access_token = environ.get('TWITTER_ACCESS_TOKEN')
    access_token_secret = environ.get('TWITTER_ACCESS_TOKEN_SECRET')
    auth = OAuthHandler(APP_KEY, APP_SECRET)
    auth.set_access_token(access_token, access_token_secret)
    api = API(auth)
    print(api.verify_credentials())
    api.update_with_media(image['image'], status=get_twitter_content(image))


def post_to_facebook(image):
    # Hide deprecation warnings. The facebook module isn't that up-to-date (facebook.GraphAPIError).
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    ACCESS_TOKEN = environ.get("FB_KEY")
    facebook_graph = facebook.GraphAPI(access_token=ACCESS_TOKEN, version=3.1)
    facebook_graph.put_photo(image=open(image['image'], 'rb'), message=get_facebook_content(image))


def get_locations():
    countries = requests.get('https://api.tourzan.com/api/v1/countries/').json()
    # cities = requests.get('https://testing.tourzan.com/api/v1/cities/').json()
    out = {'countries': [], 'cities': []}
    for country in countries:
        out['countries'].append(country['name'])
    # for city in cities:
    #     out['cities'].append(city['name'])
    return out


def watermark(input_image, output_image_path, watermark_image_path):
    req = requests.get(input_image)
    try:
        base_image = Image.open(BytesIO(req.content))
    except IOError:
        print('ioerror')
        return None
    watermark = Image.open(watermark_image_path)
    width, height = base_image.size
    watermark_width, watermark_height = watermark.size
    margin = 4
    position_tr = (width - margin - watermark_width, 0 + margin)
    # Position for bottom right watermark
    # position_br = (width - margin - watermark_width, height - margin - watermark_height)
    transparent = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    transparent.paste(base_image, (0, 0))
    transparent.paste(watermark, position_tr, mask=watermark)
    # transparent.show()
    transparent.save(output_image_path)

    new_jpeg = output_image_path.replace('.png', '.jpg')
    rename(output_image_path, new_jpeg)
    image_to_upload = new_jpeg
    return image_to_upload


def get_image(search_term, platform=None):
    try:
        unsplash_key = environ.get('unsplash_key')
        values = dict()
        url = "https://api.unsplash.com/photos/random/"
        values["client_id"] = unsplash_key
        values["orientation"] = "landscape"
        if platform:
            values["orientation"] = choice(["portrait", "landscape"])
        values["query"] = search_term
        r = requests.get(url, values)
        if r.status_code == 200:
            images_data = r.json()
            name = './images/{}.png'.format(images_data['id'])
            img_link = images_data['urls']['small']
            if values["orientation"] == 'landscape':
                img_link = images_data['urls']['regular']
            wm = watermark(img_link, name, './watermark/tp_watermark.png')
            print(wm, stat(wm).st_size, images_data['location']['title'], images_data['user']['instagram_username'], images_data['description'])
            return {'image': wm,
                    'bytes': stat(wm).st_size,
                    'user': images_data['user'],
                    'instagram': images_data['user']['instagram_username'],
                    'location': images_data['location'],
                    'full_location': images_data['location']['title'],
                    'about': images_data['description'],
                    'alt_about': images_data['alt_description'],
                    'search_term': search_term
                    }
        else:
            print(r.status_code)
    except KeyError:
        get_image(search_term)


if __name__ == "__main__":
    locations = get_locations()
    search1 = choice(locations['countries'])
    search2 = choice(locations['countries'])
    search3 = choice(locations['countries'])
    # #
    image1 = get_image(search1)
    image2 = get_image(search2)
    image3 = get_image(search3)

    post_to_facebook(image1)
    post_to_twitter(image2)
    post_to_instagram(image3)
