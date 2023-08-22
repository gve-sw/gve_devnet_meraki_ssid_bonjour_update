"""
Copyright (c) 2023 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
               https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import track
from rich.table import Table
import meraki
from meraki.exceptions import APIError
from dotenv import load_dotenv
import os
import sys
from csv import DictReader

# Load environment variables
load_dotenv()

API_KEY = os.getenv("MERAKI_DASHBOARD_API_KEY")

console = Console()

BONJOUR_SERVICES = [
    "All Services",
    "AirPlay",
    "AFP",
    "BitTorrent",
    "FTP",
    "iChat",
    "iTunes",
    "Printers",
    "Samba",
    "Scanners",
    "SSH",
]


def getOrgs(dashboard: meraki.DashboardAPI) -> str:
    """
    Get Meraki organizations and prompt user to select one
    """
    with console.status("Connecting to Meraki...."):
        try:
            orgs = dashboard.organizations.getOrganizations()
        except APIError as e:
            print("\r\n[red]Failed to connect to Meraki. Error:")
            print(f"[red]{e.message['errors'][0]}")
            sys.exit(1)
    print("[green]Connected to Meraki dashboard!")
    print(f"Found {len(orgs)} organization(s).\r\n")

    # If one org, return early
    if len(orgs) == 1:
        print(f"Working with Org: {orgs[0]['name']}")
        return orgs[0]["id"]

    # Else, ask which org to use
    print("Available organizations:")
    org_names = [org["name"] for org in orgs]
    for org in orgs:
        print(f"- {org['name']}")

    print()
    selection = Prompt.ask(
        "Which organization should we use?", choices=org_names, show_choices=False
    )
    for org in orgs:
        if org["name"] == selection:
            return org["id"]


def getNetworks(dashboard: meraki.DashboardAPI, org_id: str) -> dict:
    """
    Collect existing Meraki network names / IDs
    """
    print("Collecting networks...")
    networks = dashboard.organizations.getOrganizationNetworks(org_id)
    print(f"Found {len(networks)} networks.")
    return networks


def getNetworkSSID(dashboard: meraki.DashboardAPI, networks: dict) -> dict:
    """
    Collect SSIDs for each network
    """
    ssid_map = {}
    print("Collecting SSIDs for each network...")
    for network in track(networks, description="Working..."):
        # Skip any non-wireless networks
        if not "wireless" in network["productTypes"]:
            continue
        ssids = dashboard.wireless.getNetworkWirelessSsids(network["id"])
        ssid_map[network["name"]] = {}
        ssid_map[network["name"]]["id"] = network["id"]
        ssid_map[network["name"]]["ssids"] = {
            ssid["name"]: ssid["number"] for ssid in ssids
        }

    print("[green]Done!")
    return ssid_map


def openCSV() -> dict:
    """
    Open CSV File & read contents
    """
    while True:
        file = input("Enter the CSV file name: ")
        try:
            with open(file, "r") as f:
                print("Reading CSV...")
                csv = DictReader(f, skipinitialspace=True)
                csv_data = [row for row in csv]
                print("[green]Done!")
                return csv_data
        except FileNotFoundError:
            print(f"[red]Cannot locate file: {file}")
            print()


def processCSV(csv: dict, ssids: dict) -> None:
    """
    Validate CSV Input
    """
    print("Checking CSV file...")
    print(f"{len(csv)} entries to validate.")
    bad_network = []
    bad_ssid = []
    bad_vlan = []
    bad_services = []
    good = 0
    good_entries = {}

    for line in track(csv, "Working..."):
        # Check each line to make sure network / SSID match what Meraki has
        try:
            target_network = ssids[line["Network Name"]]
        except KeyError:
            bad_network.append(line)
            continue

        try:
            target_ssidnum = target_network["ssids"][line["SSID Name"]]
        except KeyError:
            bad_ssid.append(line)
            continue

        try:
            vlan = int(line["VLAN"])
            if not vlan > 1 or not vlan < 4096:
                raise ValueError
        except ValueError:
            bad_vlan.append(line)
            continue

        services = [s.strip() for s in line["Services"].split(",")]
        ok = True
        for service in services:
            if service.lower() not in [x.lower() for x in BONJOUR_SERVICES]:
                bad_services.append(line)
                ok = False
                break
        if not ok:
            continue

        # If line passes:
        good += 1

        # Restructure data for upload
        if not target_network["id"] in good_entries.keys():
            good_entries[target_network["id"]] = {}
        if not target_ssidnum in good_entries[target_network["id"]].keys():
            good_entries[target_network["id"]][target_ssidnum] = []
        good_entries[target_network["id"]][target_ssidnum].append(
            {
                "description": line["Description"],
                "vlanId": str(vlan),
                "services": services,
            }
        )

    if good == len(csv):
        print("[green]All CSV rows processed. No issues found!")
    else:
        print(f"\r\nIssues were found. Only {good} passed of {len(csv)}")
        if Confirm.ask("Show errors?"):
            table = Table(
                "Error",
                "Network Name",
                "SSID Name",
                "Description",
                "VLAN",
                "Services",
                expand=True,
                show_lines=True
            )
            for entry in bad_network:
                table.add_row("Network Name Mismatch", *entry.values())
            for entry in bad_ssid:
                table.add_row("SSID Name Mismatch", *entry.values())
            for entry in bad_vlan:
                table.add_row("Bad VLAN ID", *entry.values())
            for entry in bad_services:
                table.add_row("Bad Services", *entry.values())
            print()
            print(table)
            print()
    return good_entries


def updateBonjour(dashboard: meraki.DashboardAPI, data: dict) -> list:
    """
    Update Bonjour settings across multiple networks
    """
    print("Beginning update process...")
    errors = []
    for network_id in track(data):
        for ssid_id in data[network_id]:
            update_body = {"enabled": True, "rules": data[network_id][ssid_id]}
            try:
                dashboard.wireless.updateNetworkWirelessSsidBonjourForwarding(
                    network_id, ssid_id, **update_body
                )
            except APIError as e:
                errors.append(
                    {
                        "error": e.message["errors"][0],
                        "network": network_id,
                        "ssid": ssid_id,
                        "payload": update_body,
                    }
                )
    return errors


def showUpdateErrors(errors: list, ssids: dict) -> None:
    """
    Parse & print error table from updates
    """
    table = Table("Error", "Network Name", "SSID Name", "Update Payload", expand=True, show_lines=True)
    for error in errors:
        for network in ssids:
            if ssids[network]["id"] == error["network"]:
                network_name = network
            for ssid in ssids[network]["ssids"]:
                if ssids[network]["ssids"][ssid] == error["ssid"]:
                    ssid_name = ssid
        table.add_row(error["error"], network_name, ssid_name, str(error["payload"]))
    print(table)


def main():
    print()
    print(Panel.fit("  -- Start --  "))
    print()

    print()
    print(Panel.fit("Connect to Meraki", title="Step 1"))
    if API_KEY:
        print("Found API key as environment variable")
        dashboard = meraki.DashboardAPI(suppress_logging=True)
    else:
        key = Prompt.ask("Enter Meraki Dashboard API Key")
        dashboard = meraki.DashboardAPI(key, suppress_logging=True)
    org_id = getOrgs(dashboard)

    print()
    print(Panel.fit("Collect Deployment Info", title="Step 2"))
    networks = getNetworks(dashboard, org_id)
    ssids = getNetworkSSID(dashboard, networks)

    print()
    print(Panel.fit("CSV Input", title="Step 3"))
    csv = openCSV()
    good_entries = processCSV(csv, ssids)

    print()
    print(Panel.fit("Update Bonjour Settings", title="Step 4"))
    if not Confirm.ask("Proceed with updating bonjour settings?"):
        print("[red]Quitting. Please re-run script when ready.")
        sys.exit(1)
    errors = updateBonjour(dashboard, good_entries)
    if len(errors) == 0:
        print("[green]All changes processed successfully.")
    else:
        print(f"[orange]{len(errors)} changes had errors.")
        if Confirm.ask("Show errors?"):
            showUpdateErrors(errors, ssids)

    print()
    print(Panel.fit("  -- Finished --  "))
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\r\n[red]Quitting...")
