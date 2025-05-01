Overview
===
EDMC-PTN-WMM-Stacking monitors EDMC events for wing mining mission stacking. On startup, it will scan the last week's
worth of journal logs to get a current status of open wing mining missions. From then on, it will monitor EDMC events
to keep the display updated.

Two pieces of information are displayed, a hauling summary and an advertisement.

Hauling Summary
---
This will show a breakdown of each system, station, and commodity for which you have an open wing mission, as well as
the amount still to be deposited to complete the mission, and the number of trips it will take to haul that amount 
in your current ship (on startup, this will display 999 until an EDMC event fires that will allow it to calculate 
cargo space)

Example output:
```aiignore
Hauling Summary:
Mbutas
  Darlton Port
    Indite: 123 [1 trips]
    Silver: 45 [1 trips]
    Bertrandite: 1234 [2 trips]
    Gold: 23 [1 trips] 
```

Advertisement
---
This line previews what will be copied to the clipboard. Clicking the "Copy Ad" button will copy the advertisement to 
the system clipboard so that it can be pasted into the #wmm-shares PTN channel. This will include per-system number of
missions, broken down by station, and profit.

Example output:
```aiignore
@LFW-WMM [Mbutas] [Stack: 20; Darlton Port: 15, Burkin Orbital: 5] [Profit: 919 M] 
```

Installation
===
* Download the latest release from https://github.com/Zixhwizs/EDMC-PTN-WMM-Stacking/releases
* Open your EDMC plugins folder.
* Extract the root folder inside the zip file into the plugins folder
* Reload EDMC
