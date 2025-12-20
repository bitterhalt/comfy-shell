# My Ignis Shell (WIP)

_A modular Wayland shell powered by Ignis_

> ⚠️ **Status VERY Work in Progress**
>
> My first ever python project so don't kill me...
>
> I repeat **VERY WIP** at the moment!

## Overview

This is my custom Wayland shell built on **Ignis**, featuring bar, notification system, launcher, OSD components.

The goal is to keep things **clean, minimal, event-driven, and lightweight**, while being easy to extend and hack on.

Dependencies: check my [dotfiles](https://github.com/bitterhalt/dotfiles)

## Features (WIP)

### 🔸 Bar

- Clock
- Power menu
- Network & system indicators
- Record indicator
- Weather

### 🔸 OSD

- Audio
- Simple Media OSD with artwork
- Workspaces on barless mode
- Build-in Notifications

### 🔸 Launcher

- Power Menu
- Screenshot Menu
- App runner wired with: Calculator, Emojis, Websearch

### 🔸 Extra Integrations

- Barless mode

## Some screenshots

> Empty desktop
> <img src="assets/screenshots/empty.png" width="100%" />
>
> Without bar workspace overlay popup
> <img src="assets/screenshots/barless.png" width="100%" />

<details>
<summary><b>Notification Center</b></summary><br>
<img src="assets/screenshots/center.png" width="1000%" />
</details>
<details>
<summary><b>Weather</b></summary><br>
<img src="assets/screenshots/weather.png" width="80%" />
</details>
<details>
<summary><b>Quick settings</b></summary><br>
<img src="assets/screenshots/quick_settings.png" width="80%" />
</details>
<details>
<summary><b>Window-list</b></summary><br>
<img src="assets/screenshots/winmenu.png" width="80%" />
</details>

## TODO

> _02.12.27_

- [x] adapt new window_manager.api --> Mostly done, I think 👍🏻
- [x] add bluetooth in panel
- [ ] cleanup the code and make syntax more consistenta
- [x] add small time stamps to notifications
- [x] Parts of of notications are super ugly -> fix when rainy day
