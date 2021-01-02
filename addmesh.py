#!/usr/bin/env python3
import hashlib
import random
import time
import uuid
import getpass
import requests


PUBLIC_KEY = "a2ffa5c9be07488bbb04a3a47d3c5f6a"

def sha1(x: str):
    return hashlib.sha1(x.encode()).hexdigest()

def get_mac_address():
    as_hex = f"{uuid.getnode():012x}"
    return ":".join(as_hex[i : i + 2] for i in range(0, 12, 2))

def generate_nonce(miwifi_type=0):
    return f"{miwifi_type}_{get_mac_address()}_{int(time.time())}_{int(random.random() * 1000)}"

def generate_password_hash(nonce, password):
    return sha1(nonce + sha1(password + PUBLIC_KEY))


class MiWiFi():
    def __init__(self, address="http://miwifi.com/", miwifi_type=0):
        if address.endswith("/"):
            address = address[:-1]

        self.address = address
        self.token = None
        self.miwifi_type = miwifi_type

    def login(self, password):
        nonce = generate_nonce(self.miwifi_type)

        response = requests.post(
            f"{self.address}/cgi-bin/luci/api/xqsystem/login",
            data={
                "username": "admin",
                "logtype": "2",
                "password": generate_password_hash(nonce, password),
                "nonce": nonce,
            },
        )
        jdata = response.json()
        if response.status_code == 200 and "token" in jdata:
            self.token = jdata["token"]
            return jdata
        return None

    def add_mesh_node(self, macaddr, location="Study"):
        response = requests.post(
            f"{self.address}/cgi-bin/luci/;stok={self.token}/api/xqnetwork/add_mesh_node",
            data={
                "mac": macaddr,
                "locate": location
            },
        )
        jdata = response.json()
        if response.status_code == 200 and "code" in jdata and jdata['code'] == 0:
            return jdata
        return None

if __name__ == "__main__":
    address_master = input("Master (online, configured) router address (leave blank for default->http://miwifi.com): ")
    if not address_master.startswith('http'):
        address_master = f"http://{address_master}"
    
    password_master = getpass.getpass(prompt='Master password: ')
    router = MiWiFi(address = address_master)
    print("Logging in..")
    if not router.login(password_master):
        print("Authentication failed!")
        exit(1)
    print("Login: OK")
    
    mac_address_client = input("Client (not configured) 5GHz mac address (AA:BB:CC:DD:EE:FF): ")
    print(f"Adding {mac_address_client} as mesh node..")
    if router.add_mesh_node(mac_address_client):
        print("Node configured correctly! Wait for it to reboot.")
        exit(0)
    else:
        print("Something went wrong!")
        exit(1)
