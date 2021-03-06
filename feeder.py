from redis import StrictRedis
from config import (REDIS_HOST, REDIS_PORT, INTERFACES, PERIOD, EXPIRATION,
                    INFLUX_HOST)
import subprocess
import re
from periodic import periodic
from datetime import datetime
import requests

ARP_REGEX = r"(?P<host>^\S+) \((?P<ip>(\d{1,3}\.){3}\d{1,3})\) at (?P<mac>((\d|[a-f]){2}:){5}(\d|[a-f]){2}) \[\w+\] on (?P<interface>\S+)$"
ARP_REGEX = re.compile(ARP_REGEX)


def get_redis():
    return StrictRedis(REDIS_HOST, REDIS_PORT)


def send_mac(client, maclist):
    payload = ','.join(maclist)
    client.setex('incubator_pamela', EXPIRATION, payload)
    if INFLUX_HOST:
        try:
            r = requests.post(INFLUX_HOST,
                              data='mac_count value={}'.format(len(maclist)),
                              headers={'Accept-encoding': 'identity'})
        except:
            print(datetime.now(), "Error when sending people count to influx")


def get_mac(*interfaces):
    stdout = subprocess.check_output(['sudo', 'arp', '-a'])
    stdout = stdout.split('\n')
    valid = filter(lambda x: "<incomplete>" not in x, stdout)
    valid = filter(lambda x: x.strip() != "", valid)

    out = []

    for line in valid:
        match = re.match(ARP_REGEX, line)
        if match:
            machine = match.groupdict()
            if machine['interface'] in interfaces:
                out.append(machine)

    return out


@periodic(PERIOD)
def main(client):
    macdict = get_mac(*INTERFACES)
    maclist = [x['mac'] for x in macdict]
    send_mac(client, maclist)

if __name__ == '__main__':
    client = get_redis()
    client.set("incubator_pamela_expiration", EXPIRATION)
    main(client)
