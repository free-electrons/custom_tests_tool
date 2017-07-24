import os
import logging

import sys

import paramiko

# The next three function are borrowed from Lavabo, thx Oleil! :)
def get_hostkey(hostname):
    try:
        hkeys = paramiko.util.load_host_keys(os.path.expanduser("~/.ssh/known_hosts"))
    except IOError:
        hkeys = {}

    if hostname in hkeys:
        hkeytype = hkeys[hostname].keys()[0]
        return hkeys[hostname][hkeytype]

    logging.warning("host key unavailable")
    return None

def pkey_connect(transport, user):
    for pkey in paramiko.Agent().get_keys():
        try:
            transport.auth_publickey(user, pkey)
            break
        except paramiko.SSHException:
            pass

def get_sftp(hostname, port, user):
    logging.debug("Opening SSH connection...")
    hkey = get_hostkey(hostname)
    transport = paramiko.Transport((hostname, port))

    # We must set _preferred_keys before calling start_client() otherwise
    # there's a chance Paramiko won't negotiate the host key type we have
    # in our local known_keys... And there's no way to set it properly.
    if hkey is not None:
        transport._preferred_keys = [hkey.get_name()]

    transport.start_client()

    # Host key checks
    if hkey is not None:
        rkey = transport.get_remote_server_key()
        if rkey.get_name() != hkey.get_name() or rkey.asbytes() != hkey.asbytes():
            logging.error("Remote host identification has changed!")
            sys.exit(1)

    # We don't use the connect() method directly because it can't handle
    # multiple keys from the SSH agent. It's also not possible to call it
    # multiple time as a workaround because this genius calls start_client()
    pkey_connect(transport, user)
    if not transport.is_authenticated():
        logging.error("Authentication failed")
        transport.close()
        sys.exit(1)

    sftp_client = transport.open_sftp_client()
    logging.debug('Connection established')
    return sftp_client

def mkdir_p(sftp, remote_directory):
    dir_path = str()
    for dir_folder in remote_directory.split("/"):
        if dir_folder == "":
            continue
        dir_path += r"/{0}".format(dir_folder)
        try:
            sftp.listdir(dir_path)
        except IOError:
            sftp.mkdir(dir_path)

