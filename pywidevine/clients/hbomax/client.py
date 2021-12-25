import base64, time, requests, os, json
import pywidevine.clients.hbomax.config as hmaxcfg
from os.path import join

SESSION = requests.Session()
HMAXTOKEN_FILE = join(hmaxcfg.COOKIES_FOLDER, 'hmax_login_data.json')


login_config = {
    'username': 'rivas909@me.com',
    'password': 'NoCambieselPass.12345'
}

def login(SESSION, login_endpoint, content_url, save_login=True):
    def get_free_token(token_url):
        token_data = hmaxcfg.get_token_info()
        free_token = requests.post(url=token_url, headers=token_data['headers'], json=token_data['data'])
        if int(free_token.status_code) != 200:
                print(free_token.json()['message'])
                exit(1)
        return free_token.json()['access_token']
    free_access_tk = get_free_token(login_endpoint)
    auth_data = hmaxcfg.get_auth_token_info(login_config)
    headers = auth_data['headers']
    headers['authorization'] = "Bearer {}".format(free_access_tk)
    auth_rep = SESSION.post(url=login_endpoint, headers=headers, json=auth_data['data'])
    if int(auth_rep.status_code) != 200:
            print(auth_rep.json()['message'])
            exit(1)

    access_token_js = auth_rep.json()
    
    login_grant_access = [
        {
            "id": "urn:hbo:privacy-settings:mined",
            "id": "urn:hbo:profiles:mined",
            "id": "urn:hbo:query:lastplayed",
            "id": "urn:hbo:user:me"}
    ]
    user_grant_access = {
        "accept": "application/vnd.hbo.v9.full+json",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": hmaxcfg.metadata_language,
        "user-agent": hmaxcfg.UA,
        "x-hbo-client-version": "Hadron/50.40.0.111 desktop (DESKTOP)",
        "x-hbo-device-name": "desktop",
        "x-hbo-device-os-version": "undefined",
        "Authorization": f"Bearer {access_token_js['refresh_token']}"
    }
    user_grant_req = SESSION.post(content_url, json=login_grant_access, headers=user_grant_access)

    if int(user_grant_req.status_code) != 207:
        print("failed to list profiles")
    
    user_grant_js = user_grant_req.json()
    user_grant_id = ""
    
    for profile in user_grant_js:
        if profile['id'] == "urn:hbo:profiles:mine":
            if len(profile['body']['profiles']) > 0:
                user_grant_id = profile['body']['profiles'][0]['profileId']
            else:
                print("no profiles found, create one on hbomax and try again")
                exit(1)

    profile_headers = {
        "accept": "application/vnd.hbo.v9.full+json",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": hmaxcfg.metadata_language,
        "user-agent": hmaxcfg.UA,
        "x-hbo-client-version": "Hadron/50.40.0.111 desktop (DESKTOP)",
        "x-hbo-device-name": "desktop",
        "x-hbo-device-os-version": "undefined",
        "referer": "https://play.hbomax.com/profileSelect",
        "Authorization": f"Bearer {free_access_tk}" #~ free token
    }

    user_profile = {
        "grant_type": "user_refresh_profile",
        "profile_id": user_grant_id,
        "refresh_token": f"{access_token_js['refresh_token']}",
    }
    
    user_profile_req = SESSION.post(login_endpoint, json=user_profile, headers=profile_headers)

    if int(user_profile_req.status_code) != 200:
        error_msg = "failed to obatin the final token"
        print(error_msg)

    user_profile_js = user_profile_req.json()
    
    refresh_token = user_profile_js['refresh_token']

    login_data = {'ACCESS_TOKEN': refresh_token, 'EXPIRATION_TIME': int(time.time())}
    if save_login:
        with open(HMAXTOKEN_FILE, 'w', encoding='utf-8') as f:
            f.write(json.dumps(login_data, indent=4))
            f.close()
    return auth_rep.json()['access_token']


def get_video_payload(urn):
    headers = hmaxcfg.generate_payload()
    payload = []
    payload.append({"id":urn, "headers": headers['headers']})
    return payload
