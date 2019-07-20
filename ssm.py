import requests
import datetime
from os import stat, environ
from io import BytesIO
from random import choice
from PIL import Image


def get_cliche(location):
    cliches = ["{}\r.\r.\r", "whats your bucket list destination?", "Look how amazing {} is!", "Wish you were here!",
               "{} is just Wow!" "{} \r.\r.\r Where is your next vacation?",
               "Tag the friend you'd love to explore {} with!", "Have you ever seen anything like it?",
               "Guess the place?", "Caption This!", "Have you ever fallen in love with somewhere?",
               "Who wants to come with us on the next trip?", "Where was your most memorable vacation?",
               "What special memory do you have about traveling?"]
    cta = ['Become a local guide at Tourzan.com',
           "Get your guide with us at Tourzan.com",
           "Get off the beaten trail with Tourzan.com",
           "Make local friends around the world with Tourzan.com",
           "Follow us on twitter and facebookas at @tourzanhq"]
    selection = choice(cliches)
    if '{}' in selection:
        print(location['full_location'])
        print(selection)
        selection = selection.format(location['full_location'])
    out = selection + '\n\n\n' + choice(cta)
    if location['instagram'] is not None:
        out = selection + '\n\n' + choice(cta) + "\n\nphotographer's instagram: " + '@{}'.format(location['instagram'])
    return out


def get_facebook_content(data):
    location = data['name']
    content = get_cliche(location)
    if len(data['about']) > 100:
        content += '\n\nHere is what the photographer has to say about their photo:\n {}'.format(data['about'])
    return content


def get_twitter_content(data):
    return get_cliche(data)


def get_instagram_content(data):
    content = get_cliche(data)
    if data['about'] is not None and len(data['about']) > 10:
        print(data['about'])
        content += '\n\nHere is what the photographer has to say about their photo:\n {}'.format(data['about'])

    hashtags = "\r.\r.\r.\r#travel #travelphotography #travelblogger #traveling #travelgram #passionpassport " \
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


def post_to_social_media(image, profile_type):
    # Get social media profiles and authorize
    bearer = 12344
    headers = {'Authorization': 'Bearer {}'.format(bearer)}
    response = requests.get('https://platform.hootsuite.com/v1/socialProfiles', headers=headers).json()
    for res in response['data']:
        if res['type'] == str(profile_type).upper():
            social_id = res['id']
    if profile_type == 'facebook':
        content = get_facebook_content(image)
    if profile_type == 'instagram':
        content = get_instagram_content(image)
    if profile_type == 'twitter':
        content = get_twitter_content(image)

    # Get media url to upload to.
    data = '{"sizeBytes":{}, "mimeType": "image/png"}'.format(image['bytes'])
    response = requests.post('https://platform.hootsuite.com/v1/media', headers=headers, data=data).json()['data']
    upload_id = response['id']
    upload_url = response['uploadUrl']

    # Upload to hootsuite
    image_name = str(image['name']).split('/')[-1]
    headers = {
        'Content-Type': 'image/png',
        'Content-Length': image['bytes'],
        'Slug': image_name
    }
    requests.put(upload_url, data=open(image['name'], 'rb'), headers=headers).json()

    # Schedule Message
    set_time = (datetime.datetime.now() + datetime.timedelta(minutes=15)).isoformat()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(bearer),
    }
    data = {'{"text": {}, "scheduledSendTime": {},"socialProfileIds": [{}], "media": [{"id": {}]}'
            .format(content, set_time, social_id, upload_id)
    }
    response = requests.post('https://platform.hootsuite.com/v1/messages', headers=headers, data=data)
    print(response.status_code)
    print(response.content)


def get_locations():
    countries = requests.get('https://testing.tourzan.com/api/v1/countries/').json()
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
    # position_br = (width - margin - watermark_width, height - margin - watermark_height)
    transparent = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    transparent.paste(base_image, (0, 0))
    transparent.paste(watermark, position_tr, mask=watermark)
    # transparent.show()
    transparent.save(output_image_path)
    return output_image_path


def get_image(search_term, platform=None):
    try:
        unsplash_key = environ.get('unsplash_key')
        values = dict()
        url = "https://api.unsplash.com/photos/random/"
        values["client_id"] = unsplash_key
        values["orientation"] = "portrait"
        if platform:
            values["orientation"] = choice(["portrait", "landscape"])
        values["query"] = search_term
        r = requests.get(url, values)
        if r.status_code == 200:
            images_data = r.json()
            # print(images_data.keys())
            name = './images/{}.png'.format(images_data['id'])
            img_link = images_data['urls']['small']
            if values["orientation"] == 'landscape':
                img_link = images_data['urls']['regular']
            wm = watermark(img_link, name, './watermark/tp_watermark.png')
            print(wm, stat(name).st_size, images_data['location']['title'], images_data['user']['instagram_username'], images_data['description'])
            return {'image': name,
                    'bytes': stat(name).st_size,
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
    image1 = get_image(search1, platform='facebook')
    image2 = get_image(search2, platform='twitter')
    image3 = get_image(search3)
    print(get_facebook_content(image1))
    print(get_twitter_content(image1))
    print(get_instagram_content(image1))
    #
    # post_to_social_media(image1, 'facebook')
    # post_to_social_media(image2, 'twitter')
    # post_to_social_media(image3, 'instagram')
