import json
import requests
import os
from pathlib import Path
from time import sleep

# 현재 디렉토리에서 확인
file_path = Path('read.txt')

def recall_read_ids(file_path :Path):
    if file_path.is_file():
        with file_path.open('r') as file:
            r = [x.strip() for x in file.read().split('\n') if x != '']
    else:
        print('read.txt doesn not exist.. creating one')
        with file_path.open('w') as file:
            file.write('')
        r = []
    return r

def add_read_ids(id_, file_path :Path):
    with file_path.open('a') as file:
        file.write('\n'+id_)

instance_url = "https://msk.canor.kr"
api_key = "tdMyv3l3RMjHnNVvfuhbNAulLjEopf7z" # nodularfy this #TODO

def run():
    body = {'limit':10}
    headers = {'Authorization': 'Bearer ' + api_key}

    r = requests.post(instance_url + '/api/i/notifications', json=body, headers=headers)
    notifications = json.loads(r.content)

    #for n in notifications:
    #print(n)
    return notifications

def parse(n):
    read_ids = recall_read_ids(file_path)
    if n['id'] in read_ids:
        return 0
    else:
        print('id : ', n['id'])
        print('user : ', n['user']['name'] , '(', n['user']['username'], '@', n['user']['host'], ')')
        print('type : ', n['type'])
        try:
            print('tar : ', n['note']['text'])
        except:
            print('tar: note content unavailable')
        print('---------')
        add_read_ids(n['id'], file_path)

if __name__=='__main__':
    while True:
        try:
            read_ids = recall_read_ids(file_path)
            notifications = run()
            for n in notifications:
                parse(n)
            sleep(10)
        except:
            sleep(10)
