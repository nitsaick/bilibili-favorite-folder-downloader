import re
import sys
import time
from subprocess import call

while True:
    text = sys.stdin.readline()
    if text == 'end\n':
        break
    
    match = re.match('id:(\d+), output_dir:(.*)', text)
    id = match.group(1)
    output_dir = match.group(2)
    
    try:
        call('you-get -o {} https://www.bilibili.com/video/av{}'.format(output_dir, id), shell=True)
    except KeyboardInterrupt:
        print('\nKeyboardInterrupt\n')
    
    sys.stderr.write('done\n')
    sys.stderr.flush()
    time.sleep(1)
