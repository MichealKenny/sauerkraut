from bottle import route, run, request
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

    run(host=host, port=port)