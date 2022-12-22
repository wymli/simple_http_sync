#!/bin/env bash

# 
# USAGE:
#   1. curl -s stdout.txt?last_lines=10
#   2. print(requests.get('http://?last_lines=10').text)
#   2. print(requests.get('http://?last_bytes=4096').text)
#
# LogFilePath:
#   HTTP Log Server:
#     1. /dev/null
#   Cronjob Health Check:
#     1. $log_dir/operate_file_server_\$(date '+\%Y\%m\%d').cronjob.log
#

base_dir=1
log_dir=1

function rand() {
    min=${1}
    range=$(($2 - $min + 1))
    num=${RANDOM}
    echo $((num % $range + $min))
}

function getport(){
    min=$1
    max=$2
    retry=${3-1}
    for i in {1..${retry}}; do
        p=$(rand $1 $2)
        python -c "import socket; exit(socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex(('127.0.0.1', $p)))"
        if [ $? != 0 ]; then
            echo $((p))
            break
        fi
    done
}

function cleanup {
    echo "$(date '+%Y-%m-%d %H:%M:%S') | cleaning old LogFileServer..."
    ps aux | grep 'file_server.py' | grep -v grep | awk '{print $2}' | xargs kill -9
}

cleanup

file_server_port=$(getport 9010 9050 5)
echo "$(date '+%Y-%m-%d %H:%M:%S') | new file server port: $file_server_port"
cat > $base_dir/file_server.py <<EOF
import argparse
import urllib
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, required=True)
parser.add_argument('--dir', type=str, required=True)
args = parser.parse_args()

print(f"switching to dir {args.dir} and listening on {args.port}")
os.chdir(args.dir)


class H(SimpleHTTPRequestHandler):
    # 支持中文
    extensions_map = {k: v + ';charset=UTF-8' for k, v in SimpleHTTPRequestHandler.extensions_map.items()}
    
    def do_GET(self):
        f = self.send_head()
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(self.path).query))
        last_lines = int(query.get('last_lines', 0))
        last_bytes = int(query.get('last_bytes', 0))
        if f:
            try:
                if last_bytes > 0: 
                    content = self.tail_bytes(f, bytes=last_bytes)
                elif last_lines > 0:
                    lines = self.tail_lines(f, lines=last_lines)
                    content = b''.join(lines)
                else:
                    content = f.read()
                # Note: Content-Length in http response headers here is fileLength, not bodyLength.
                self.wfile.write(content)
            finally:
                f.close()

    def tail_lines(self, f, lines=20, BLOCK_SIZE=4096):
        total_lines_wanted = lines
        f.seek(0, 2)
        block_end_byte = f.tell()
        lines_to_go = total_lines_wanted
        block_number = -1
        blocks = []
        while lines_to_go > 0 and block_end_byte > 0:
            if (block_end_byte - BLOCK_SIZE > 0):
                f.seek(block_number*BLOCK_SIZE, 2)
                blocks.append(f.read(BLOCK_SIZE))
            else:
                f.seek(0,0)
                blocks.append(f.read(block_end_byte))
            lines_found = blocks[-1].count(b'\n')
            lines_to_go -= lines_found
            block_end_byte -= BLOCK_SIZE
            block_number -= 1
        all_read_text = b''.join(reversed(blocks))
        return all_read_text.splitlines(keepends=True)[-total_lines_wanted:]
    
    def tail_bytes(self, f, bytes=4096):
        f.seek(0, 2)
        if f.tell() < bytes:
            f.seek(0,0)
        else:
            f.seek(-bytes, 2)
        return f.read()

httpd = HTTPServer(('0.0.0.0', args.port), H)
httpd.serve_forever()

EOF
python3 $base_dir/file_server.py --port $file_server_port --dir $log_dir/ > /dev/null 2>&1 &


# ------------------------------------------
# 运维
# 认为端口不可用时需要重启进程，而非pid存在
# ------------------------------------------
cat > $base_dir/operate_file_server.sh <<EOF
#!/bin/env bash
python -c "import socket; exit(socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect_ex(('127.0.0.1', $file_server_port)))"
if [ \$? != 0 ]; then
    echo "\$(date '+%Y-%m-%d %H:%M:%S') | reloading, file server port is not available: $file_server_port" 
    reload
else
    echo "\$(date '+%Y-%m-%d %H:%M:%S') | check pass, port is available: $file_server_port" 
fi
EOF

service cron restart
cat > $base_dir/operate_file_server.cronjob <<EOF
*/1 * * * * bash $base_dir/operate_file_server.sh >> $log_dir/operate_file_server_\$(date '+\%Y\%m\%d').cronjob.log 2>&1

EOF
crontab $base_dir/operate_file_server.cronjob
