from bottle import route, run
import psutil


@route('/')
def index():
    return 'Sauerkraut Slave'

@route('/status')
def status():
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent

    return {'cpu': cpu, 'ram': ram}

run(host='localhost', port=29547)