#!/usr/bin/env python3
import requests, subprocess, argparse, tempfile, shutil, sys, getpass, keyring, readline
exit = sys.exit

def launchMT(mtpath, host, port, name, passwd):
    passwdFile = tempfile.NamedTemporaryFile(mode="w")
    try:
        passwdFile.write(passwd)
        passwdFilePath = passwdFile.file.name
        passwdFile.flush()
        try:
            completed = subprocess.run([mtpath,"--address",host,"--port",str(port),"--name",name,"--password-file",passwdFilePath,"--go"])
        except KeyboardInterrupt:
            pass
        return completed
    finally:
        passwdFile.close()

def download_serverlist(url):
    R = requests.get(url)
    if R.status_code != 200:
        raise requests.HTTPError(responce=R)
    return R.json()

def const_serverflag(item):
    RLST = []
    if "creative" in item and item["creative"]:
        RLST.append("CRE")
    if "damage" in item and item["damage"]:
        RLST.append("DMG")
    if "pvp" in item and item["pvp"]:
        RLST.append("PVP")
    if "password" in item and item["password"]:
        RLST.append("PWD")
    if "rollback" in item and item["rollback"]:
        RLST.append("ROL")
    return " ".join(RLST)

def const_entry(x,item):
    return str(x).zfill(3) + ". " + item["name"] + " (" + item["address"] + ":" + str(item["port"]) + ") " + const_serverflag(item)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'Minetest Launcher with password saving')
    parser.add_argument('-m', '--minetest-path', help = "Executeable of the Minetest client. Default: Find in $PATH",
                        dest = "mtpath")
    parser.add_argument('-p', '--protocol', type = int, dest = "protocol",
                        help = "Protocol version of the Minetest client. Servers of all versions will be shown if none is provided.")
    parser.add_argument('-s', '--serverlist', help = "URL of the serverlist. Default: https://servers.minetest.net/list",
                        default = "https://servers.minetest.net/list", dest = "serverlist")
    parser.add_argument('-k', '--keyring', help = "Keyring to store passwords. Default: mtlaunch",
                        default = "mtlaunch", dest = "keyring")
    args = parser.parse_args()

    # Find where Minetest is
    mtpath = args.mtpath
    if mtpath == None:
        mtpath = shutil.which("minetest")
        if mtpath == None:
            print("Minetest executeable not found. Please specify one in --minetest-path.")
            exit(1)
        else:
            print("Minetest executeable found at: " + mtpath)
            print("If this is wrong, specify one in --minetest-path.")
    else:
        print("Using user-provided Minetest executeable path: " + mtpath)

    # download serverlist
    try:
        serverlist = download_serverlist(args.serverlist)
    except requests.HTTPError:
        print("Serverlist not found. Please check the entered URL.")
        raise
    except requests.RequestException:
        print("A connection exception occured. Please check your internet connection.")
        raise

    # Filter out servers
    serverlistlist = serverlist["list"]
    if args.protocol != None:
        for x in list(serverlistlist):
            if args.protocol < x.proto_min or args.protocol > x.proto_max:
                serverlistlist.remove(x)
    serverlistlistlen = len(serverlistlist)

    print("Serverlist fetched, " + str(serverlistlistlen) + " servers found.")

    # Help message
    print("Press Enter to show more entries. Type the server ID to join. Type in keywords to search.")

    # Mainloop
    pointer = 0
    noshow = False
    while True:
        if not noshow:
            pointer = pointer + 5
            for x in range(pointer - 5,pointer):
                if x >= serverlistlistlen:
                    print("--- END OF LIST ---")
                    pointer = 0
                    break
                item = serverlistlist[x]
                print(("*" if x%5 == 4 else " ") + const_entry(x,item))
        noshow = False
        try:
            prompt = input("> ")
        except KeyboardInterrupt:
            print()
            exit(0)
        if prompt != "":
            noshow = True
            try:
                serverID = int(prompt)
                if serverID >= serverlistlistlen:
                    raise ValueError
                item = serverlistlist[serverID]
                pointer = 0
                print("--- SERVER DETAILS ---")
                print(item["name"] + " (" + item["address"] + ":" + str(item["port"]) + ")")
                if "description" in item:
                    print("Destription: " + item["description"])
                if "version" in item:
                    print("Version: " + item["version"])
                if "clients" in item and "clients_max" in item:
                    print("Players: " + str(item["clients"]) + "/" + str(item["clients_max"]))
                if "privs" in item:
                    print("Default Privileges: " + item["privs"])
                print("Flags: " + const_serverflag(item))
                print("--- SERVER DETAILS ---")
                print("Type in your username if you want to join. Type \":exit\" or press Ctrl-C to quit.")
                try:
                    uname = input("Username: ")
                    if uname == ":exit":
                        continue
                    try:
                        keyringpass = keyring.get_password(args.keyring,uname + "@" + item["address"] + ":" + str(item["port"]))
                    except keyring.errors.KeyringError:
                        print("ERROR: Cannot fetch data from the keyring. Please check your keyring settings.")
                        keyringpass = None
                    passwd = None
                    if keyringpass != None:
                        ask = input("Password found in keyring. Do you want to use that one? (Y/n) ").lower()
                        if ask[0] != "n":
                            passwd = keyringpass
                    if passwd == None:
                        passwd = getpass.getpass("Password: ")
                        if passwd == ":exit":
                            continue
                    if passwd != keyringpass:
                        ask = input("Do you want to save this password into the keyring? (y/N) ").lower()
                        if ask[0] == "y":
                            try:
                                keyring.set_password(args.keyring,uname + "@" + item["address"] + ":" + str(item["port"]),passwd)
                            except keyring.errors.KeyringError:
                                print("ERROR: Password cannot be set. Please check your keyring settings.")
                except KeyboardInterrupt:
                    print()
                    continue
                print("Launching Minetest...")
                launchMT(mtpath, item["address"], item["port"], uname, passwd)
            except ValueError:
                # Fallback to search mode, prompt = query
                prompts = prompt.split(" ")
                results = []
                for i, x in enumerate(serverlistlist):
                    for y in prompts:
                        if y in x["name"] or y in x["address"]:
                            results.append((i,x))
                            break
                if len(results) == 0:
                    print("--- NO RESULT ---")
                else:
                    print("--- SEARCH RESULT ---")
                    for x in results:
                        print(const_entry(x[0],x[1]))
                    print("--- SEARCH RESULT ---")
        else:
            print("\x1b[1A\x1b[2K\x1b[1A")
