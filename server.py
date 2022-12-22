#!/bin/env python
# coding=utf8
import os
import argparse
from os import path
from flask import Flask, render_template, request, Response
app = Flask(__name__)


parser = argparse.ArgumentParser()
parser.add_argument('--makedir', '--mkdir', '-mkdir', action='store_true', default=True)
parser.add_argument('--port', '-port', type=str)
parser.add_argument('--local', '-local', action='store_true', default=False,help="只取文件的basename放在当前目录, 不在乎目录关系")
args = parser.parse_args()
can_mkdir = args.makedir

port = args.port
if not port:
    port = "9989"

local = args.local

print('can make dir: {}'.format(can_mkdir))
print('local: {}'.format(local))
print(args)


@app.route('/')
def upload_file():
    html = '''
<html>
   <body>
      <form action = "/upload" method = "POST"
         enctype = "multipart/form-data">
         <input type = "file" name = "file" />
         <input type = "submit"/>
      </form>
   </body>
</html>
'''
    return Response(html, content_type='text/html')


@app.route('/upload', methods=['POST'])
def upload_file_handler():
    if request.method == 'POST':
        abs_save_file_list = []
        for k, v in request.files.viewitems():
            print('[server] saving {}'.format(k))
            if k.startswith('file_'):
                save_file = k.replace('file_', '')
                if local:
                    save_file = path.basename(save_file)
                else:
                    if not path.exists(path.dirname(save_file)):
                        if can_mkdir:
                            os.makedirs(path.dirname(save_file))
                            print('[server] making dirs: {}'.format(save_file))
                        else:
                            print('[server] [skip] dir is not exists: {}'.format(save_file))
                            continue
                v.save(save_file)
                # 删除同名的.so
                # ...
                abs_save_file_list.append(save_file)
            if k == 'file':
                print('[unknown] {}'.format(v.filename))

        return 'file uploaded successfully, saved in {}'.format(abs_save_file_list)


if __name__ == '__main__':
    app.run("0.0.0.0", port, debug=False)
