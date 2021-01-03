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
    def __init__(self, address, miwifi_type=0):
        if address.endswith("/"):
            address = address[:-1]

        self.address = address
        self.token = None
        self.miwifi_type = miwifi_type

    def get_infos(self):
        if not self.token:
            print("You need to be logged in to use this function!")
            return None
        response = requests.get(f"{self.address}/cgi-bin/luci/;stok={self.token}/api/misystem/status")
        jdata = response.json()
        if response.status_code == 200 and "hardware" in jdata:
            print(f"Platform: {jdata['hardware']['platform']}")
            print("")
        else:
            print("Something went wrong while retrieving the infos!")
            exit(1)

    def get_5ghz_xiaomi(self):
        if not self.token:
            print("You need to be logged in to use this function!")
            return None
        print(f"Asking master to scan for Xiaomi Wifi APs...")
        response = requests.get(f"{self.address}/cgi-bin/luci/;stok={self.token}/api/xqnetwork/wifi_list")
        jdata = response.json()
        detected = 0
        if response.status_code == 200 and "list" in jdata:
            for ap in jdata["list"]:
                if ap["ssid"].startswith("Xiaomi_") and ap["encryption"] == "NONE":
                    if (ap["band"] == "5g" and ap["ssid"].endswith("_5G")) or (ap["band"] == "2g"):
                        if detected == 0:
                            print("Detected APs:")
                        print(f'\tBand: {ap["band"]}hz SSID: {ap["ssid"]} CH: {ap["channel"]} MODEL: {ap["wsc_modelname"]} MAC: {ap["bssid"]}')
                        if ap["band"] == "2g":
                            pmac = ap['bssid'].split(":")
                            pmac[-1] = hex(int(pmac[-1],16)+1)[2:]
                            pmac = ':'.join(pmac).upper()
                            print(f'\t\tPOSSIBLE MAC for 5GHz: {pmac}')
                        detected += 1
        if detected == 0:
            print("No AP detected! (Are the two devices close enough?)")
            print("You can continue, but it will probably fail.")
        print("")

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
        if not self.token:
            print("You need to be logged in to use this function!")
            return None
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
    address_master = input("Master (online, configured) router address: ")
    if address_master and not address_master.startswith('http'):
        address_master = f"http://{address_master}"

    password_master = getpass.getpass(prompt='Master password: ')
    router = MiWiFi(address = address_master)
    print("Logging in..")
    if not router.login(password_master):
        print("Authentication failed!")
        exit(1)
    print("Login: OK\n")
    
    router.get_infos()
    router.get_5ghz_xiaomi()

    mac_address_client = input("Client (not configured) 5GHz mac address (AA:BB:CC:DD:EE:FF): ")
    print(f"Adding {mac_address_client} as mesh node..")
    if router.add_mesh_node(mac_address_client):
        print("Node configured correctly! Wait for it to reboot.")
        exit(0)
    else:
        print("Something went wrong!")
        exit(1)
