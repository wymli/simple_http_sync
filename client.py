#!/bin/env python
# coding=utf-8
from os import path, read
from threading import local
import requests
import argparse
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

modified_file_name_list = set()


class MyEventHandler(FileSystemEventHandler):
    def on_moved(self, event):
        pass

    def on_created(self, event):
        pass

    def on_deleted(self, event):
        pass

    def on_modified(self, event):
        print("文件编辑触发:" + event.src_path)
        modified_file_name_list.add(event.src_path)
        print('输入sync以同步改动:')


parser = argparse.ArgumentParser()
parser.add_argument('path_to_listen_and_sync', type=str, default='.')
parser.add_argument('--remote_app_dir', '-r', type=str, default='')
parser.add_argument('--all', '-all', '--force_all', action='store_true')
parser.add_argument('--file', '-file', type=str)
parser.add_argument('--port', '-port', type=str, default="9989")
parser.add_argument('--ip', '-ip', type=str, default="", help="")
parser.add_argument('--proxy', '-proxy', type=str, default="abc", choices=['abc', 'asdf'])
args = parser.parse_args()

local_listen_dir = path.abspath(path.join(os.getcwd(), args.path_to_listen_and_sync))

remote_app_dir = args.remote_app_dir
if not remote_app_dir:
    remote_app_dir = '/' + path.basename(path.abspath(local_listen_dir))

port = args.port
if not port:
    port = "9989"

ip = args.ip
if not ip:
    ip = ""

force_override = args.all
file_to_sync = args.file

print('local listen dir:', local_listen_dir)
print('remote app dir:', remote_app_dir)
print('force override:', force_override)
print('file to sync:', file_to_sync)
print('port:', port)


proxy_map = {
    'abc': 'http://ip:port',
    'asdf': 'http://ip:port'
}

if not args.proxy or args.proxy == 'asdf':
    ip = "asdf"
    proxy_ip = proxy_map['abc']
if args.proxy == 'asdf':
    ip = "asdf"
    proxy_ip = proxy_map['asdf']



def upload_files(file_name_list):
    print('[upload] local file name list: {}'.format(file_name_list))
    if not file_name_list:
        return

    files = {}
    for abs_file_name in file_name_list:
        if '.git' in abs_file_name:
            continue
        rel_path = path.relpath(abs_file_name, local_listen_dir)
        remote_file_path = path.join(remote_app_dir, rel_path)
        files['file_' + remote_file_path] = open(abs_file_name, 'rb')
    print('[upload] remote file name list: {}'.format(files.keys()))


    r = requests.post('http://{}:{}/upload'.format(ip, port),
                      files=files,
                      proxies={'http': proxy_ip}
                      )

    print(r.text)


def get_all_file_in_dir(walk_dir):
    file_list = set()
    for root, subdirs, files in os.walk(walk_dir):


        for filename in files:
            file_path = os.path.join(root, filename)
            file_list.add(file_path)
    return file_list


def main():
    if force_override:
        upload_files(get_all_file_in_dir('.'))
        return
    if file_to_sync:
        upload_files([path.abspath(file_to_sync)])
        return

    observer = Observer()  # 创建观察者对象
    file_handler = MyEventHandler()  # 创建事件处理对象
    observer.schedule(file_handler, local_listen_dir, recursive=True)  # 向观察者对象绑定事件和目录

    t = threading.Thread(target=observer.start)
    t.start()

    while True:
        x = input('输入sync以同步改动:')
        if x == 'sync':
            upload_files(modified_file_name_list)
            modified_file_name_list.clear()
        else:
            print('only support `sync`')


if __name__ == '__main__':
    main()
