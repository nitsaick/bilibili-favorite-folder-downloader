import re
import sys
from datetime import datetime

import requests
import you_get
from pathlib2 import Path
from tqdm import tqdm

from utils import illegal_chars


class Video:
    def __init__(self, aid, name=None, pubdate=None, fav_time=None, fav_id=None):
        self.aid = aid
        self.name = name
        self.pubdate = pubdate
        self.fav_time = fav_time
        self.fav_id = fav_id
        self.desc = None
        self.part_names = []
        self.cids = []
        self.danmakus = []
        self.info_got = False
        self.available = None
    
    def get_video_info(self):
        url = f'https://api.bilibili.com/x/web-interface/view?aid={self.aid}'
        response = requests.get(url)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        code = int(re.findall('"code":(.*?),"', content)[0])
        if code != 0:
            self.available = False
            return
        
        name = re.findall('"title":"(.*?)","pubdate"', content)[0]
        name = ''.join(c if c not in illegal_chars else '-' for c in name)
        
        timestamp = int(re.findall('"pubdate":(\d+)', content)[0])
        pubdate = datetime.fromtimestamp(timestamp)
        desc = re.findall('"desc":"(.*?)","state"', content)[0].replace('\\n', '\n')
        part_names = re.findall('"part":"(.*?)","duration"', content)
        
        if len(part_names) > 1:
            part_names = ['{} (P{}. {})'.format(name, i + 1, part_names[i]) for i in range(len(part_names))]
            part_names = [''.join(c if c not in illegal_chars else '-' for c in prat_name) for prat_name in part_names]
        else:
            part_names = [name]
        part_names = [prat_name.replace('[', '(') for prat_name in part_names]
        part_names = [prat_name.replace(']', ')') for prat_name in part_names]
        
        url = 'https://www.bilibili.com/widget/getPageList?aid={}'.format(self.aid)
        response = requests.get(url)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        cids = re.findall('"cid":(\d+)', content)
        
        danmakus = []
        for cid, part_name in zip(cids, part_names):
            url = f'https://comment.bilibili.com/{cid}.xml'
            response = requests.get(url)
            assert response.status_code == 200
            content = response.content
            danmakus.append(content)
        
        self.name = name
        self.pubdate = pubdate
        self.desc = desc
        self.part_names = part_names
        self.cids = cids
        self.danmakus = danmakus
        self.info_got = True
        self.available = True
    
    def download_video(self, output):
        output = Path(output)
        sys.argv.clear()
        sys.argv.extend(['--playlist',
                         '--no-caption',
                         '-o',
                         f'{output}',
                         f'https://www.bilibili.com/video/av{self.aid}'
                         ])
        you_get.main()
    
    def download_danmaku(self, output):
        assert self.info_got
        for danmaku, part_name in zip(self.danmakus, self.part_names):
            output = Path(output) / f'{part_name}.danmaku.xml'
            with open(output, 'wb') as file:
                file.write(danmaku)
    
    def download_info(self, output):
        assert self.info_got
        output = Path(output) / f'{self.name}.txt'
        with open(output, 'w', encoding='utf-8') as file:
            file.write(f'https://www.bilibili.com/video/av{self.aid}\n')
            file.write(self.pubdate.strftime('%Y-%m-%d %H:%M:%S\n\n'))
            file.write(self.desc)


class FavoriteFolder:
    def __init__(self, fav_id, name=''):
        self.fav_id = fav_id
        self.name = name
        self.video_list = []
        self.video_got = False
    
    def get_video(self):
        video_list = []
        page = 1
        
        while True:
            url = f'https://api.bilibili.com/medialist/gateway/base/spaceDetail?media_id={self.fav_id}&pn={page}&ps=0'
            response = requests.get(url)
            assert response.status_code == 200
            content = response.content.decode('utf-8')
            
            ids = re.findall('"link":"bilibili://video/(\d+)","', content)
            names = [match[1] for match in re.findall('"tid":(\d+),"title":"(.*?)","', content)]
            pubdates = re.findall(',"pubtime":(\d+),"tid":', content)
            fav_times = re.findall(',"fav_time":(\d+),"', content)
            
            assert len(ids) == len(names) == len(pubdates) == len(fav_times)
            
            if len(ids) > 0:
                video_list += \
                    [Video(aid, name, datetime.fromtimestamp(int(pubdate)), datetime.fromtimestamp(int(fav_time)),
                           self.fav_id)
                     for aid, name, pubdate, fav_time in zip(ids, names, pubdates, fav_times)]
                page += 1
            else:
                break
        
        name = re.findall('"title":"(.*?)","type":11,', content)[0]
        
        self.name = name
        self.video_list = video_list
        self.video_got = True
        
        return video_list
    
    def __len__(self):
        return len(self.video_list)


class User:
    def __init__(self, user_id):
        url = f'https://api.bilibili.com/x/v2/fav/folder?vmid={user_id}'
        response = requests.get(url)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        ids = re.findall('"media_id":(\d+),', content)
        names = re.findall('"name":"(.*?)"', content)
        fav_list = [FavoriteFolder(fav_id, name) for fav_id, name in zip(ids, names)]
        
        url = f'https://api.bilibili.com/x/web-interface/card?mid={user_id}'
        response = requests.get(url)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        name = re.findall('"name":"(.*?)","approve"', content)[0]
        
        self.fav_list = fav_list
        self.name = name
    
    def get_all_video(self, clear_duplicate=True):
        all_video_list = []
        video_check = []
        for fav in tqdm(self.fav_list, desc=f"{self.name}'s Favorite Folder", ascii=True):
            video_list = fav.get_video()
            for video in video_list:
                if not clear_duplicate or video.aid not in video_check:
                    all_video_list.append(video)
                    video_check.append(video.aid)
        
        return all_video_list
    
    def __len__(self):
        return len(self.fav_list)
