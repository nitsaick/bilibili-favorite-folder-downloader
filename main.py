import sys
import time
from subprocess import Popen, CREATE_NEW_CONSOLE

import click
import zmq
from pathlib2 import Path
from tqdm import tqdm

from bilibili import User, FavoriteFolder, Video
from downloader import Downloader
from utils import REQ


class Exclusion:
    def __init__(self, fav_list=[], video_list=[], pubdate=None, fav_time=None):
        self.fav_list = fav_list
        self.video_list = video_list
        self.pubdate = pubdate
        self.fav_time = fav_time
    
    def __call__(self, video):
        exc = video.fav_id in self.fav_list or video.aid in self.video_list or \
              self.pubdate is not None and self.pubdate > video.pubdate or \
              self.fav_time is not None and self.fav_time > video.fav_time
        return exc


@click.command()
@click.option('--type', help='type', type=click.Choice(['user', 'fav', 'video']))
@click.option('-i', '--id', help='user or fav folder ID', type=int, required=True)
@click.option('-o', '--output', help='output path',
              type=click.Path(dir_okay=True, resolve_path=True), required=True)
@click.option('--pubdate', help='pubdate',
              type=click.DateTime(), default=None, show_default=True)
@click.option('--fav_time', help='fav_time',
              type=click.DateTime(), default=None, show_default=True)
@click.option('--exc_fav', 'exclusion_fav', help='exclusion fav', is_flag=True)
@click.option('--exc_vid', 'exclusion_video', help='exclusion video', is_flag=True)
@click.option('-p', '--port', help='port',
              type=click.IntRange(1000, 65535, clamp=True), default=5555, show_default=True)
@click.option('-t', '--thread', help='thread',
              type=click.IntRange(1, 100, clamp=True), default=1, show_default=True)
def main(type, id, output, pubdate, fav_time, exclusion_fav, exclusion_video, port, thread):
    video_list = []
    
    if type == 'user':
        user = User(id)
        video_list = user.get_all_video()
    elif type == 'fav':
        fav = FavoriteFolder(id)
        video_list = fav.get_video()
    elif type == 'fav':
        video_list.append(Video(id))

    exc_fav_list = []
    if exclusion_fav:
        with open('exc_fav.txt', 'r', encoding='UTF-8') as f:
            for fid in f.readlines():
                exc_fav_list.append(fid.strip())

    exc_vid_list = []
    if exclusion_video:
        with open('exc_vid.txt', 'r', encoding='UTF-8') as f:
            for vid in f.readlines():
                exc_vid_list.append(vid.strip())
    
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f'tcp://*:{port}')
    
    procs = []
    for i in range(thread):
        proc = Popen([sys.executable, 'downloader.py', '-p', str(port)], bufsize=1, creationflags=CREATE_NEW_CONSOLE)
        procs.append(proc)
    time.sleep(5)
    
    exclusion = Exclusion(fav_list=exc_fav_list, video_list=exc_vid_list, pubdate=pubdate, fav_time=fav_time)
    
    exclusion_count = download_count = 0
    output = Path(output)
    with tqdm(video_list, ascii=True, desc='Downloading') as tbar:
        for video in tbar:
            if not exclusion(video):
                cmd = socket.recv_pyobj()
                if cmd == REQ:
                    socket.send_pyobj(Downloader(video, output))
                    time.sleep(1)
                    download_count += 1
            else:
                exclusion_count += 1
            tbar.set_postfix(downloaded=download_count, excluded=exclusion_count)
            tbar.update()
    
    print('Waiting all download thread done')
    now_alive = last_alive = len(procs)
    with tqdm(total=len(procs), ascii=True, desc='Waiting') as pbar:
        while now_alive > 0:
            now_alive = 0
            for proc in procs:
                if proc.poll() is None:
                    now_alive += 1
            
            if last_alive != now_alive:
                pbar.update(last_alive - now_alive)
                last_alive = now_alive
    
    print('done')


if __name__ == '__main__':
    main()
