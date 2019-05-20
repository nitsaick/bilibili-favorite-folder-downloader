import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from subprocess import call, Popen, PIPE
import gzip

import requests

video_ext = ['flv', 'mp4', 'mkv']
illegal_chars = '\/*?:"<>|'


def download(output_dir, id, vidoe_to_mp4=False, danmaku_to_ass=False):
    url = 'https://api.bilibili.com/x/web-interface/view?aid={}'.format(id)
    response = urllib.request.urlopen(url)
    content = response.read().decode('utf-8')
    
    name = re.findall('"title":"(.*?)","pubdate"', content)[0]
    name = ''.join(c if c not in illegal_chars else '-' for c in name)
    
    timestamp = int(re.findall('"pubdate":(\d+)', content)[0])
    pubdate = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S\n\n')
    desc = re.findall('"desc":"(.*?)","state"', content)[0].replace('\\n', '\n')
    part_names = re.findall('"part":"(.*?)","duration"', content)
    if len(part_names) > 1:
        part_names = ['{} (P{}. {})'.format(name, i + 1, part_names[i]) for i in range(len(part_names))]
        part_names = [''.join(c if c not in illegal_chars else '-' for c in prat_name) for prat_name in part_names]
    else:
        part_names = [name]
    
    # TODO Test
    part_names = [prat_name.replace('[', '(') for prat_name in part_names]
    part_names = [prat_name.replace(']', ')') for prat_name in part_names]
    
    call('you-get --playlist --no-caption --debug -o "{}" https://www.bilibili.com/video/av{}'.format(output_dir, id),
         shell=True)
    
    if vidoe_to_mp4:
        for part_name in part_names:
            filename = os.path.join(output_dir, part_name)
            if os.path.isfile('{}.{}'.format(filename, 'flv')) and not os.path.isfile('{}.{}'.format(filename, 'mp4')):
                call('"./ext_file/ffmpeg" -i "{}.flv" -c copy -copyts "{}.mp4"'.format(filename, filename), shell=True)
    
    desc_file = os.path.join(output_dir, '{}.txt'.format(name))
    with open(desc_file, 'w', encoding='utf-8') as file:
        file.write('https://www.bilibili.com/video/av{}\n'.format(id))
        file.write(pubdate)
        file.write(desc)
    
    url = 'https://www.bilibili.com/widget/getPageList?aid={}'.format(id)
    response = urllib.request.urlopen(url)
    content = gzip.decompress(response.read()).decode(response.headers.get_content_charset())
    cids = re.findall('"cid":(\d+)', content)
    
    for cid, part_name in zip(cids, part_names):
        url = 'https://comment.bilibili.com/{}.xml'.format(cid)
        response = requests.get(url)
        danmaku_file = os.path.join(output_dir, '{}.danmaku.xml'.format(part_name))
        with open(danmaku_file, 'wb') as file:
            file.write(response.content)
        
        if danmaku_to_ass:
            filename = os.path.join(output_dir, part_name)
            for ext in video_ext:
                video_filename = '{}.{}'.format(filename, ext)
                if os.path.isfile(video_filename):
                    command = '"./ext_file/ffprobe" -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "{}"'.format(
                        video_filename)
                    output, _ = Popen(command, universal_newlines=True, shell=True, stdout=PIPE).communicate()
                    match = re.match('(\d+)x(\d+)', output)
                    width, height = int(match.group(1)), int(match.group(2))
                    if width > height:
                        ratio = 1920. / width
                    else:
                        ratio = 1080. / width
                    font_size = round(56 / ratio)
                    video_size = '{}x{}'.format(width, height)
                    call(
                        '{} "./ext_file/danmaku2ass.py" "{}.danmaku.xml" -s {}  -o "{}.danmaku.ass" -fs {} -fn "SimHei" -dm 10 -ds 10'
                            .format(sys.executable, filename, video_size, filename, font_size))
                    break


if __name__ == '__main__':
    error = []
    while True:
        error_sign = False
        text = sys.stdin.readline()
        if text == 'end\n':
            break
        
        match = re.match('id:(\d+), output_dir:(.*)', text)
        id = match.group(1)
        output_dir = match.group(2)
        try:
            download(output_dir, id, True, True)
        except KeyboardInterrupt:
            print('\nKeyboardInterrupt\n')
        
        except Exception:
            print('\nSomething wrong when download id: {}\n'.format(id))
            error.append(id)
            error_sign = True
            pass
        
        if not error_sign:
            sys.stderr.write('success\n')
        else:
            sys.stderr.write('failure\n')
        
        sys.stderr.flush()
        time.sleep(1)
    
    if len(error):
        print('Error id:')
        print(error)
        while True: pass
