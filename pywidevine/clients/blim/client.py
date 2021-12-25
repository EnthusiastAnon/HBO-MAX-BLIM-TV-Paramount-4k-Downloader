import json, sys, time
import pywidevine.clients.blim.config as blim_cfg
from os.path import join

BLIMLOGINDATA_FILE = join(blim_cfg.COOKIES_FOLDER, 'blim_login_data.json')

login_cfg = {
    'email': 'teste@blim.com',
    'password': 'teste1234'
}

def login(SESSION, save_login=False):
    post_data = {"email": login_cfg['email'], "password": login_cfg['password'], "remember": True, "clientId":5}
    login_resp = SESSION.post(url=blim_cfg.ENDPOINTS['login'], json=post_data)
    if login_resp.json()['data'] == []:
        print(login_resp.json()['messages'][0]['value'])
        sys.exit(1)

    costumer_key = login_resp.json()['data']['sessionId']
    access_key_secret = login_resp.json()['data']['accessToken']
    login_data = {'COSTUMER_KEY': costumer_key, 'SECRET_KEY': access_key_secret}
    if save_login:
        with open(BLIMLOGINDATA_FILE, 'w', encoding='utf-8') as f:
            f.write(json.dumps(login_data, indent=4))
            f.close()

    return SESSION, costumer_key, access_key_secret
