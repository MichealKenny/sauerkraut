from bottle import route, run, request
import psutil


def authorized():
    master_ip = '127.0.0.1'

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

run(host='localhost', port=29547)
#run(host='localhost', port=29548)
#run(host='localhost', port=29549)
#run(host='localhost', port=29550)