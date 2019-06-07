import click
import zmq
from pathlib2 import Path

from utils import REQ, DONE


class Downloader:
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


@click.command()
@click.option('-p', '--port', help='port',
              type=click.IntRange(1000, 65535, clamp=True), default=5555, show_default=True)
@click.option('-t', '--wait_time', help='wait time',
              type=click.IntRange(0, clamp=True), default=30000, show_default=True)
def main(port, wait_time):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(f'tcp://localhost:{port}')
    
    poll = zmq.Poller()
    poll.register(socket, zmq.POLLIN)
    
    while True:
        socket.send_pyobj(REQ)
        
        socks = dict(poll.poll(wait_time))
        if socks.get(socket) == zmq.POLLIN:
            item = socket.recv_pyobj()
            if type(item) is not Downloader and item == DONE:
                break
            item()
        else:
            break


if __name__ == '__main__':
    main()
