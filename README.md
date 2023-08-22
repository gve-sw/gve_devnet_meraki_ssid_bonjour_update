# Cisco Meraki - Bonjour Settings Updater

This repository contains sample code for bulk updating bonjour settings across multiple networks & SSIDs.

## Contacts

- Matt Schmitz (<mattsc@cisco.com>)

## Solution Components

- Cisco Meraki

## Installation/Configuration

### **Step 1 - Clone repo:**

```bash
git clone <repo_url>
```

### **Step 2 - Install required dependancies:**

```bash
pip install -r requirements.txt
```

### **Step 3 - Provide Cisco Meraki API Key (Optional)**

You may choose to provide the Cisco Meraki API key via the `MERAKI_DASHBOARD_API_KEY` environment variable.

If the environment variable is not provided, then the script will prompt for the API key.

### **Step 4 - Prepare CSV file**

A local CSV file must be provided in the following structure:

```text
Network Name, SSID Name, Description, VLAN, Services
Network 01,Wifi01, Rule 01, 10, "iChat, iTunes, Samba"
Network 01,Wifi02, Some description, 200, "AFP,FTP,SSH"
Network 02,Another wifi, Lots of printers, 400, "Printers, scanners"
```

## Usage

### Running locally

Run the application with the following command:

```
python3 update_bonjour.py
```

The script will prompt for any additional information, then push the changes to Meraki.

# Related Sandbox

- [Cisco Meraki Enterprise Lab](https://devnetsandbox.cisco.com/RM/Diagram/Index/e7b3932b-0d47-408e-946e-c23a0c031bda?diagramType=Topology)

# Screenshots

### Demo of script

![/IMAGES/demo.gif](/IMAGES/demo.gif)

### LICENSE

Provided under Cisco Sample Code License, for details see [LICENSE](LICENSE.md)

### CODE_OF_CONDUCT

Our code of conduct is available [here](CODE_OF_CONDUCT.md)

### CONTRIBUTING

See our contributing guidelines [here](CONTRIBUTING.md)

#### DISCLAIMER

<b>Please note:</b> This script is meant for demo purposes only. All tools/ scripts in this repo are released for use "AS IS" without any warranties of any kind, including, but not limited to their installation, use, or performance. Any use of these scripts and tools is at your own risk. There is no guarantee that they have been through thorough testing in a comparable environment and we are not responsible for any damage or data loss incurred with their use.
You are responsible for reviewing and testing any scripts you run thoroughly before use in any non-testing environment.
