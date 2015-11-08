from bottle import route, run, request, ServerAdapter
from subprocess import Popen, check_output
import psutil
import json
import os


def authorized():
    if request.remote_addr == master_ip:
        return True

    else:
        return False

@route('/')
def index():
    return 'Sauerkraut Slave'

@route('/status')
def status():
    if authorized():
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent

        return {'cpu': cpu, 'ram': ram}

    else:
        return {'error': 'Not Authorized'}

@route('/extended')
def extended():
    if authorized():
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent
        disk_read = psutil.disk_io_counters(perdisk=False).read_count
        disk_write = psutil.disk_io_counters(perdisk=False).write_count
        packets = psutil.net_io_counters(pernic=False)
        total_packets = packets.packets_recv + packets.packets_sent

        return {'cpu': cpu, 'ram': ram, 'disk_usage': disk_usage, 'disk_read': disk_read,
                'disk_write': disk_write, 'total_packets': total_packets}

    else:
        return {'error': 'Not Authorized'}


@route('/execute', method='POST')
def execute():
    if authorized():
        command = request.forms.get('command').split()
        path = request.forms.get('path')
        type = request.forms.get('type')

        if type == 'blocking':
            try:
                if path:
                    Popen(command, cwd=path, shell=True)

                else:
                    Popen(command, shell=True)

                return {'output': 'Command spawned.'}

            except:
                return {'output': 'Error executing command'}

        else:

            try:
                if path:
                    output = check_output(command, cwd=path, shell=True).decode()

                else:
                    output = check_output(command, shell=True).decode()

            except:
                return {'output': 'Error executing command'}

            return {'output': output}

    else:
        return {'error': 'Not Authorized'}


class SSLWSGIRefServer(ServerAdapter):
    def run(self, handler):
        from wsgiref.simple_server import make_server, WSGIRequestHandler
        import ssl
        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(*args, **kw): pass
            self.options['handler_class'] = QuietHandler
        srv = make_server(self.host, self.port, handler, **self.options)
        srv.socket = ssl.wrap_socket (
         srv.socket,
         certfile='slave.pem',  # path to certificate
         server_side=True)
        srv.serve_forever()

if __name__ == '__main__':
    print('Sauerkraut Slave')
    if not os.path.isfile('config.json'):
        print('========================================\n\nFresh Install, Please fill in the following details:\n')

        config = json.dumps({'host': input('Host: '), 'port': int(input('Port: ')),
                             'master_ip': input('Host of Master: ')}, indent=4)

        config_file = open('config.json', 'w+')
        config_file.write(config)
        config_file.close()

        print('\nCreated configuration file, it can be changed at any time.')

    config_file = open('config.json', 'r')
    config = json.loads(config_file.read())
    config_file.close()

    master_ip = config['master_ip']
    host = config['host']
    port = config['port']

    srv = SSLWSGIRefServer(host=host, port=port)
    run(server=srv)