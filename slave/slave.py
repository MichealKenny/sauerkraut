from bottle import route, run, request, ServerAdapter
from subprocess import Popen, check_output
from socket import gethostbyname
import psutil
import json
import os


def authorized():
    """
    Check if the request is from the master server.

    :return: True or False.
    """

    if master_ip:
        if request.remote_addr == master_ip:
            return True

        else:
            return False

    else:
        return True


@route('/')
def index():
    """
    Return that this is a Sauerkraut Slave.

    :return: Text.
    """

    return 'Sauerkraut Slave'


@route('/status')
def status():
    """
    Get data on the CPU and RAM.

    :return: JSON, CPU & RAM.
    """

    if authorized():
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent

        return {'cpu': cpu, 'ram': ram}

    else:
        return {'error': 'Not Authorized'}


@route('/extended')
def extended():
    """
    Get data on the CPU, RAM, Disk Usage, Disk Read, Disk Write, & Total Packets.

    :return: JSON, CPU, RAM, Disk Usage, Disk Read, Disk Write, & Total Packets.
    """

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
    """
    Get the payload data, perform a number of checks and execute the command.

    :return: JSON, Command output.
    """

    if authorized():
        command = request.forms.get('command')
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


class SecureAdapter(ServerAdapter):
    def run(self, handler):
        from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer
        from socketserver import ThreadingMixIn
        import ssl

        if self.quiet:
            class QuietHandler(WSGIRequestHandler):
                def log_request(*args, **kw):
                    pass

            self.options['handler_class'] = QuietHandler

        #Setup SSL context for 'A+' rating from Qualys SSL Labs.
        context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLSv1_2)
        context.load_cert_chain(certfile='slave.pem')
        context.set_ciphers('EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH')

        class ThreadAdapter(ThreadingMixIn, WSGIServer): pass
        ssl_server = make_server(self.host, self.port, handler, server_class=ThreadAdapter, **self.options)
        ssl_server.socket = context.wrap_socket(ssl_server.socket, server_side=True)
        ssl_server.serve_forever()


if __name__ == '__main__':
    print('Sauerkraut Slave')

    if not os.path.isfile('slave.pem'):
        try:
            os.system("openssl req -new -x509 -keyout slave.pem -out slave.pem -days 365 -nodes")

            if not os.path.isfile('slave.pem'):
                quit()

            print('Generated slave.pem x509 certificate')

        except:
            print('Sauerkraut requires an x509 openssl generated slave.pem file, could not auto generate.')
            print('Generate with: openssl req -new -x509 -keyout slave.pem -out slave.pem -days 365 -nodes')
            quit()

    if not os.path.isfile('config.json'):
        print('========================================\n\nFresh Install, Please fill in the following details:\n')

        host = input('Internal IP address/host [localhost]: ') or 'localhost'
        port = input('Port [29547]: ') or '29547'
        master_ip = input('This Sauerkraut slave will only accept requests from the following address\n'
                          '(Sauerkraut Master IP address/host) [Accept all]: ') or None

        config = json.dumps({'host': host, 'port': int(port),
                             'master_ip': master_ip}, indent=4)

        config_file = open('config.json', 'w+')
        config_file.write(config)
        config_file.close()

        print('\nCreated configuration file, it can be changed at any time.')

    config_file = open('config.json', 'r')
    config = json.loads(config_file.read())
    config_file.close()

    master_ip = config['master_ip']
    if master_ip:
        master_ip = gethostbyname(master_ip)

    host = config['host']
    try:
        port = int(os.sys.argv[1])

    except:
        port = config['port']

    run(server=SecureAdapter, host=host, port=port)