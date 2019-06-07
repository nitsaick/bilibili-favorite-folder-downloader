import zmq
from pathlib2 import Path

from utils import REQ, DONE


class DownloadItem:
    def __init__(self, video, output='/'):
        self.video = video
        self.output = Path(output)
        if not self.output.exists():
            self.output.mkdir(parents=True)
    
    def __call__(self, *args, **kwargs):
        self.video.get_video_info()
        print(f'aid: {self.video.aid}\n')
        
        if self.video.available:
            self.video.download_video(self.output)
            print('\nvideo done!\n')
            self.video.download_danmaku(self.output)
            print('danmaku done!\n')
            self.video.download_info(self.output)
            print('info done!')
        else:
            print('not available!')
        
        print('\n' + '-' * 50 + '\n')


if __name__ == '__main__':
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect('tcp://localhost:5555')
    
    poll = zmq.Poller()
    poll.register(socket, zmq.POLLIN)
    
    while True:
        socket.send_pyobj(REQ)
        
        socks = dict(poll.poll(30000))
        if socks.get(socket) == zmq.POLLIN:
            item = socket.recv_pyobj()
            if type(item) is not DownloadItem and item == DONE:
                break
            item()
        else:
            break
