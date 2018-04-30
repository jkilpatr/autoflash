"""
Usage:
  autoflash flash [--device=<id>] [--loop] [--tmpdir=<dir>] [--router-ip=<ip>] [-v] [--vv]
  autoflash list-devices [-v] [--vv]
  autoflash download --device=<id> [--tmpdir=<dir>] [-v] [--vv]

Options:
  --device=<id>          Device id to flash [default: None]
  --loop                 Repeat the flash on a loop to flash many identical devices
  --tmpdir=<dir>         Filepath for the storage of Althea firmware files [default: Current Directory]
  --router-ip=<ip>       SSH ip address for devices like the aclite that dhcp out of the box
  -v                     Application level debugging
  -vv                    Library level debugging
"""

from time import sleep
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

# To handle devices that need jailbreak firmware
def download_intermediary_firmware(tmpdir, device):
    filename = device['intermediaryFirmwareURL'].split("/")[-1]
    url = device['intermediaryFirmwareURL']

    logging.info("Downloading Intermediary firmware file " + filename + " to " + tmpdir)

    with open(tmpdir + filename, "wb") as file:
        response = requests.get(url, timeout=10)
        file.write(response.content)

    return tmpdir + filename, filename


# Takes a device populated with settings, returns a tuple of sftp and ssh connections
def ssh_setup(device):
    logging.info("ssh {}@{}:{}".format(device['sshUser'],device['sshIP'],device['sshPort']))
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    while True:
        try:
            client.connect(device['sshIP'],
                        port=device['sshPort'],
                        username=device['sshUser'],
                        password=device['sshPassword'],
                        look_for_keys=False)
        except paramiko.ssh_exception.NoValidConnectionsError:
            print("Can't find router via ssh, retrying. ")
            print("If this happens for more than 5 minutes, double check router power and connection")
            sleep(30)
        break
    sftp = client.open_sftp()

    return client, sftp

def run_ssh_command(client, command):
    logging.info("Running command: {}".format(command))
    stdin, stdout, stderr = client.exec_command(command)
    while not stdout.channel.exit_status_ready():
        sleep(.01)

    logging.info(stdout.readlines())
    logging.info(stderr.readlines())
    if stdout.channel.recv_exit_status():
        logging.error("SSH command failed!")
        exit(1)


# Flash method for devices that already run OpenWrt of some kind.
def flash_sysupgrade(device):

    client, sftp = ssh_setup(device)

    firmware_location = "/tmp/" + device['firmwareFilename']
    sftp.put(device['firmwarePath'], firmware_location)

    stdout, stderr, rc = client.exec_command("sysupgrade -v -n" + firmware_location)
    print(stdout)
    print(stderr)

# Specialied flashing routine for edgerouterlite
def flash_edgerouterlite(device):
    print("TODO")

# Specialized flashing routine for edgerouterx
def flash_edgerouterx(device, opts):
    intermediary_firmware_path, intermediary_firmware_filename = \
    download_intermediary_firmware(opts['--tmpdir'], device)

    input("Please plug your computer into eth0 of the EdgerouterX then press enter\n")
    client, sftp = ssh_setup(device)
    env_magic = "/opt/vyatta/bin/vyatta-op-cmd-wrapper"


    intermediary_firmware_location = "/tmp/" + intermediary_firmware_filename
    sftp.put(intermediary_firmware_path, intermediary_firmware_location)
    run_ssh_command(client, "{} add system image {}".format(env_magic ,intermediary_firmware_location))
    run_ssh_command(client, "{} reboot now".format(env_magic))

    print("Waiting for EdgerouterX to perform jailbreak reboot, do not unplug")

    sleep(30)
    client.close()
    sftp.close()

    print("Jailbreak complete, Uploading and Flashing Althea image")
    device['sshUser'] = 'root'
    client, sftp = ssh_setup(device)

    firmware_location = "/tmp/" + device['firmwareFilename']
    sftp.put(device['firmwarePath'], firmware_location)

    run_ssh_command(client, "sysupgrade -v -n {}".format(firmware_location))

    print("Waiting for final boot")

    sleep(30)
    client.close()
    sftp.close()
    print("Flashing Successful!")

def flash_aclite(device, opts):
    input("Please plug both your computer and the ACLite into a network using\
the same dhcp service. Find it's ip either by browsing your routers device page\
or using some external program like nmap. Press enter when ready")

    if not opts['--device-ip']:
        opts['--device-ip'] = input("Please enter the device ip")




def flash_device(device, opts):
    if device['flashMethod'] == "sysupgrade":
        flash_sysupgrade(device)
    elif device['flashMethod'] == "edgerouterlite":
        flash_edgerouterlite(device)
    elif device['flashMethod'] == "edgerouterx":
        flash_edgerouterx(device, opts)
    elif device['flashMethod'] == "aclite":
        flash_aclite(device, opts)
    else:
        logging.error("Flashing method for this device is not supported, please update this program")
        exit(1)

def main():
    opts = docopt.docopt(__doc__)
    print("Welcome to the Alhtea firmware flasher, please make sure your computer\
please make sure your computer has internet access until instructed to connect devices")

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
        print("Starting...")
        devices = get_devices_list()
        device = devices[opts['--device']]

        device['firmwarePath'], device['firmwareFilename'] = download(tmpdir, device)

        if opts['--loop']:
            while True:
                flash_device(device, opts)
        else:
            flash_device(device, opts)

main()
