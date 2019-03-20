import argparse
import os
import queue
import re
import sys
import threading
import time
import urllib.request
from subprocess import Popen, PIPE, CREATE_NEW_CONSOLE

from tqdm import tqdm


class Downloader(threading.Thread):
    def __init__(self, queue, ):
        super(Downloader, self).__init__()
        self.queue = queue
        self._stop_event = threading.Event()
    
    def run(self):
        proc = Popen([sys.executable, 'sub_downloader.py'],
                     stdin=PIPE, stderr=PIPE, bufsize=1, universal_newlines=True, creationflags=CREATE_NEW_CONSOLE)
        time.sleep(1)
        
        try:
            while self.queue.qsize() > 0 and not self.stopped():
                video_id, output_dir = self.queue.get()
                proc.stdin.write('id:{}, output_dir:{}\n'.format(video_id, output_dir))
                proc.stdin.flush()
                
                done = False
                while not done and proc.poll() is None and not self.stopped():
                    line = proc.stderr.readline()
                    done = True if line == 'done\n' else False
            
            proc.stdin.write('end\n')
            proc.stdin.flush()
            proc.wait()
        
        except OSError:
            self.stop()
    
    def stop(self):
        self._stop_event.set()
    
    def stopped(self):
        return self._stop_event.is_set()


def check_worker_alive(workers):
    alive = 0
    for worker in workers:
        alive += 1 if worker.is_alive() else 0
    return alive


def get_fav_list(user_id):
    url = 'https://api.bilibili.com/x/v2/fav/folder?vmid={}'.format(user_id)
    response = urllib.request.urlopen(url)
    content = response.read().decode('utf-8')
    
    ids = re.findall('"media_id":(\d+),', content)
    names = re.findall('"name":"(.*?)"', content)
    fav_list = [{'fav_id': id, 'name': name} for id, name in zip(ids, names)]
    
    url = 'https://api.bilibili.com/x/web-interface/card?mid={}'.format(user_id)
    response = urllib.request.urlopen(url)
    content = response.read().decode('utf-8')
    name = re.findall('"name":"(.*?)","approve"', content)[0]
    print('{:4} favorite folders of User "{}"'.format(len(fav_list), name))
    
    return fav_list


def get_video_list(fav_id):
    video_list = []
    page = 1
    
    while True:
        url = 'https://api.bilibili.com/medialist/gateway/base/spaceDetail?media_id={}&pn={}&ps=0'.format(fav_id, page)
        response = urllib.request.urlopen(url)
        content = response.read().decode('utf-8')
        ids = re.findall('"link":"bilibili://video/(\d+)","', content)
        names = [match[1] for match in re.findall('"tid":(\d+),"title":"(.*?)"', content)]
        
        if len(ids) > 0:
            video_list += [{'video_id': id, 'video_name': name} for id, name in zip(ids, names)]
            page += 1
        else:
            break
    
    name = re.findall('"title":"(.*?)","type":11,', content)[0]
    print('{:4} videos in favorite folder "{}"'.format(len(video_list), name))
    
    return {'fav_id': fav_id, 'fav_name': name, 'video_list': video_list}


def get_args():
    parser = argparse.ArgumentParser(description='bilibili favorite folder downloader')
    parser.add_argument('--user_id', type=str, default=None,
                        help='use --user_id={} to download this user\'s all favorite folder')
    parser.add_argument('--fav_id', type=str, default=None,
                        help='use --fav_id={} to download specific favorite folder')
    parser.add_argument('--output_dir', type=str, default='./',
                        help='use --output_dir={} download to specific folder')
    parser.add_argument('--use_fav_name', type=bool, default=False,
                        help='use --use_fav_name=True download to the same name of folder as the favorite folder')
    parser.add_argument('--thread', type=int, default=1,
                        help='use --thread={} to multi-thread download')
    args = parser.parse_args()
    
    return args


if __name__ == '__main__':
    args = get_args()
    assert args.user_id or args.fav_id, 'Request one args (user_id or fav_id)'
    assert not args.user_id or not args.fav_id, 'Cannot use user_id and fav_id both in the same time'
    
    root = os.path.expanduser(args.output_dir)
    
    if args.user_id and not args.fav_id:
        fav_list = get_fav_list(args.user_id)
        num_video = 0
        for i in range(len(fav_list)):
            fav_list[i] = get_video_list(fav_list[i]['fav_id'])
            num_video += len(fav_list[i]['video_list'])
    
    elif not args.user_id and args.fav_id:
        fav_list = [get_video_list(args.fav_id)]
    
    video_queue = queue.Queue()
    for fav in fav_list:
        if args.use_fav_name:
            output_dir = os.path.join(root, fav['fav_name'])
        else:
            output_dir = root
        
        for video in fav['video_list']:
            video_queue.put((video['video_id'], output_dir))
    
    workers = []
    for _ in range(args.thread):
        worker = Downloader(video_queue)
        worker.start()
        workers.append(worker)
    
    total_num = last_queue = now_queue = video_queue.qsize()
    print('Total video: {}'.format(total_num))
    
    try:
        with tqdm(total=last_queue, ascii=True) as pbar:
            while now_queue > 0:
                now_queue = video_queue.qsize()
                if last_queue != now_queue:
                    pbar.update(last_queue - now_queue)
                    last_queue = now_queue
                if check_worker_alive(workers) == 0:
                    print('All threads were dead')
                    sys.exit(-1)
    
    except KeyboardInterrupt:
        print('KeyboardInterrupt')
        for worker in workers:
            worker.stop()
        
        total_num = last_alive = now_alive = len(workers)
        print('Waitting all download thread stop')
        with tqdm(total=total_num, ascii=True) as pbar:
            while now_alive > 0:
                now_alive = check_worker_alive(workers)
                if last_alive != now_alive:
                    pbar.update(last_alive - now_alive)
                    last_alive = now_alive
    
    print('Download Complete!')
