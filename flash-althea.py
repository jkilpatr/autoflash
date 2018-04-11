"""
Usage:
  autoflash flash [--device=<id>] [--loop] [--tmpdir=<dir>] [-v] [--vv]
  autoflash list-devices [-v] [--vv]
  autoflash download --device=<id> [--tmpdir=<dir>] [-v] [--vv]

Options:
  --device=<id>          Device id to flash [default: None]
  --loop                 Repeat the flash on a loop to flash many identical devices
  --tmpdir=<dir>         Filepath for the storage of Althea firmware files [default: Current Directory]
  -v                     Application level debugging
  -vv                    Library level debugging
"""

import requests
import paramiko
import docopt
import logging
import json

firmware_url="https://updates.altheamesh.com/"


# Generates a dictionary of firmware tags to urls
def get_devices_list():
    location = firmware_url + "devices"

    logging.info("Accessing updated devices list from " + location)

    response = requests.get(location, timeout=10)
    devices = {}
    for line in response.text.split('\n'):
        fields = line.split("\t")
        if len(fields) > 1:
            devices[fields[0]] = json.loads(fields[1])

    return devices

def display_devices_list():
    devices = get_devices_list()
    for entry in devices:
        print(entry)

def download(tmpdir, device):
    filename = device['firmwareURL'].split("/")[-1]
    url = device['firmwareURL']

    logging.info("Downloading firmware file " + filename + " to " + tmpdir)

    with open(tmpdir + filename, "wb") as file:
        response = requests.get(url, timeout=10)
        file.write(response.content)

    return tmpdir + filename, filename

# Takes a device populated with settings, returns a tuple of sftp and ssh connections
def ssh_setup(device):
    transport = paramiko.Transport((device['sshIP'], device['sshPort']))
    transport.connect(username=device['sshUser'], password=device['sshPassword'])
    sftp = paramiko.sftp_client.from_transport(transport)

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy)
    client.connect(device['sshIP'], port=device['sshPort'], username=device['sshUser'], password=device['sshPassword'])

    return client, sftp


# Flash method for devices that already run OpenWrt of some kind.
def flash_sysupgrade(device):

    client, sftp = ssh_setup(device)

    firmware_location = "/tmp/" + device['firmwareFilename']
    sftp.put(device['firmwarePath'], firmware_location)

    stdout, stderr = client.exec_command("sysupgrade -v -n" + firmware_location)
    print(stdout)
    print(stderr)

# Flash method that uploads to a firmware page in recovery mode
def flash_upload(device):
    files = {'upload_file': open(device['firmwarePath'],'rb')}
    r = requests.post(device['uploadAddress'], files=files)

# Specialied flashing routine for edgerouterlite
def flash_edgerouterlite(device):
    print("TODO")

# Specialized flashing routine for edgerouterx
def flash_edgerouterx(device):
    print("TODO")


def flash_device(device):
    if device['flashMethod'] == "sysupgrade":
        flash_sysupgrade(device)
    elif device['flashMethod'] == "edgerouterlite":
        flash_edgerouterlite(device)
    elif device['flashMethod'] == "upload":
        flash_upload(device)
    elif device['flashMethod'] == "edgerouterx":
        flash_edgerouterx(device)
    else:
        logging.error("Flashing method for this device is not supported, please update this program")
        exit(1)

def main():
    opts = docopt.docopt(__doc__)

    if opts['-v']:
        logging.basicConfig(level=logging.INFO)
    elif opts['--vv']:
        logging.basicConfig(level=logging.DEBUG)

    if opts['--tmpdir'] == 'Current Directory':
        tmpdir = "./" #TODO platform detection
    else:
        tmpdir = opts['--tmpdir']


    if opts['list-devices']:
        display_devices_list()
        exit(0)

    elif opts['flash'] and opts['--device']:
        devices = get_devices_list()
        device = devices[opts['--device']]

        device['firmwarePath'], device['firmwareFilename'] = download(tmpdir, device)

        if opts['--loop']:
            while True:
                flash_device(device)
        else:
            flash_device(device)

main()
