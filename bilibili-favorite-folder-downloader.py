import argparse
import os
import re
import urllib.request
from subprocess import call


def bilibili_video_download(video_id, output_dir):
    call("you-get -o {} https://www.bilibili.com/video/av{}".format(output_dir, video_id), shell=True)


def get_fav_list(user_id, info):
    url = 'https://api.bilibili.com/x/v2/fav/folder?vmid={}'.format(user_id)
    response = urllib.request.urlopen(url)
    content = response.read().decode('utf-8')
    
    ids = re.findall('"media_id":(\d+),', content)
    names = re.findall('"name":"(.*?)"', content)
    fav_list = [list(_) for _ in zip(ids, names)]
    
    if info:
        url = 'https://api.bilibili.com/x/web-interface/card?mid={}'.format(user_id)
        response = urllib.request.urlopen(url)
        content = response.read().decode('utf-8')
        name = re.findall('"name":"(.*?)","approve"', content)[0]
        print('Number of "{}" favlist: {}'.format(name, len(fav_list)))
    
    return fav_list


def get_video_list(fav_id, info):
    video_list = []
    page = 1
    
    while True:
        url = 'https://api.bilibili.com/medialist/gateway/base/spaceDetail?media_id={}&pn={}&ps=0'.format(fav_id, page)
        response = urllib.request.urlopen(url)
        content = response.read().decode('utf-8')
        ids = re.findall('"link":"bilibili://video/(\d+)","', content)
        names = [match[1] for match in re.findall('"tid":(\d+),"title":"(.*?)"', content)]
        
        if len(ids) > 0:
            video_list += [list(_) for _ in zip(ids, names)]
            page += 1
        else:
            break
    
    if info:
        name = re.findall('"title":"(.*?)","type":11,', content)[0]
        print('Number of "{}" video: {}'.format(name, len(video_list)))
    
    return video_list


def get_args():
    parser = argparse.ArgumentParser(description='bilibili favorite folder downloader')
    parser.add_argument('--user_id', type=str, default=None,
                        help='use --user_id={} to download this user\'s all favorite folder')
    parser.add_argument('--fav_id', type=str, default=None,
                        help='use --fav_id={} to download specific favorite folder')
    parser.add_argument('--info', type=bool, default=False,
                        help='use --info to show favorite folder info')
    parser.add_argument('--output_dir', type=str, default='./',
                        help='use --output_dir={} download to specific folder')
    parser.add_argument('--use_fav_name', type=bool, default=False,
                        help='use --use_fav_name download to the same name of folder as the favorite folder')
    args = parser.parse_args()
    
    return args


if __name__ == '__main__':
    args = get_args()
    
    assert args.user_id or args.fav_id, 'Request one args (user_id or fav_id)'
    assert not args.user_id or not args.fav_id, 'Cannot use user_id and fav_id both in the same time'
    
    root = os.path.expanduser(args.output_dir)
    
    if args.user_id and not args.fav_id:
        fav_list = get_fav_list(args.user_id, args.info)
        num_video = 0
        for i in range(len(fav_list)):
            video_list = get_video_list(fav_list[i][0], args.info)
            fav_list[i].append(video_list)
            num_video += len(video_list)
        
        print('{} favlist, {} videos'.format(len(fav_list), num_video))
        
        downloaded = 0
        for i in range(len(fav_list)):
            str = ' Downloading {}/{} favlist "{}" '.format(i + 1, len(fav_list), fav_list[i][1])
            print('\n{:=^60s}\n'.format(str))
            
            for j in range(len(fav_list[i][2])):
                print('Downloading {}/{} video: {}'.format(downloaded + 1, num_video, fav_list[i][2][j][1]))
                output_dir = os.path.join(root, fav_list[i][1]) if args.use_fav_name else root
                bilibili_video_download(fav_list[i][2][j][0], output_dir)
                downloaded += 1
    
    elif not args.user_id and args.fav_id:
        video_list = get_video_list(args.fav_id, args.info)
        
        downloaded = 0
        for i in range(len(video_list)):
            print('Downloading {}/{} video: {}'.format(downloaded + 1, len(video_list), video_list[i][1]))
            output_dir = root
            bilibili_video_download(video_list[i][0], output_dir)
            downloaded += 1
