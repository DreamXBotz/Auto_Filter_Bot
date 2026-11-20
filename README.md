<p align="center">
  <span style="background: linear-gradient(135deg, #FF9933 0%, #FF512F 100%); color: #FFFFFF; font-weight: bold; font-size: 16px; padding: 7px 24px; border-radius: 20px; display: inline-block; box-shadow: 0 4px 12px rgba(255, 81, 47, 0.35); border: 1px solid #FF8008;">
    🚩 जय श्री राम 🚩
  </span>
</p>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=1,12,24&height=180&section=header&text=DreamXBotz%20Auto%20Filter&fontSize=40&fontAlignY=36&desc=High-Performance%20Telegram%20Media%20Indexing%20Bot&descAlignY=58&descAlign=50" width="100%" alt="Header Banner"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Pyrogram-v2-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Pyrogram">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white" alt="MongoDB">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

<p align="center">
  <a href="https://t.me/Princess_V4_bot">
    <img src="https://img.shields.io/badge/🤖%20Demo%20Bot-Telegram-0088cc?style=for-the-badge&logo=telegram&logoColor=white" alt="Demo Bot">
  </a>
  &nbsp;
  <a href="https://t.me/Deendayal_Support_Group">
    <img src="https://img.shields.io/badge/💬%20Support%20Group-Join-24A1DE?style=for-the-badge&logo=telegram&logoColor=white" alt="Support Group">
  </a>
  &nbsp;
  <a href="https://t.me/dreamxbotz">
    <img src="https://img.shields.io/badge/📢%20Updates-Channel-FF8800?style=for-the-badge&logo=telegram&logoColor=white" alt="Updates">
  </a>
</p>

---

## 📌 Features Overview

| 🚀 Core Engine | 🛡️ Security & Access | 💎 Management & Perks |
| :--- | :--- | :--- |
| ⚡ **Auto-Filter Engine** (Instant search results) | 🔐 **Force-Subscription** (Join Request & Public) | 💎 **Premium Membership** (Stars / UPI plans) |
| 🗄️ **Multi-DB Failover** (MongoDB scalable cluster) | 🛡️ **3-Step Verification** (Shortener token gates) | ⚙️ **Group Control** (Captions, IMDb & settings) |
| 🔍 **Smart Spell Check** (Fuzzy misspelled queries) | 🚫 **User & Chat Moderation** (Ban / Unban tools) | 📢 **Mass Broadcast** (Users & connected groups) |

---

> [!TIP]
> ### 📂 Seamless 3-Step File Indexing
> 1. **Grant Permissions**: Add your bot as an **Administrator** in your file channel with delete & invite permissions.
> 2. **Auto-Discovery**: Any new file posted to the channel is automatically indexed into MongoDB in real-time.
> 3. **Manual Batch Indexing**: Forward existing files or send post message links directly to the bot in PM.

---

## 🚀 Quick Setup & Deployment

### 1. Local Run
```bash
# Clone the repository
git clone https://github.com/DreamXBotz/Auto_Filter_Bot.git
cd Auto_Filter_Bot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Start the bot
python bot.py
```

### 2. Docker
```bash
docker build -t auto-filter-bot .
docker run --env-file .env -p 8080:8080 auto-filter-bot
```

### 3. Cloud / Render Hosting
1. Fork or push this repository to GitHub.
2. Create a new **Web Service** on [Render](https://render.com).
3. Set Runtime Environment to **Docker** (or Python 3).
4. Add your environment variables and click **Deploy**.

---

## ⚙️ Key Environment Variables

| Variable | Required | Description |
| :--- | :---: | :--- |
| `BOT_TOKEN` | Yes | Telegram Bot Token from [@BotFather](https://t.me/BotFather) |
| `API_ID` | Yes | Telegram API ID from [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Yes | Telegram API Hash from [my.telegram.org](https://my.telegram.org) |
| `ADMINS` | Yes | Telegram User IDs of administrators (space-separated) |
| `DATABASE_URI` | Yes | MongoDB connection string |
| `LOG_CHANNEL` | Yes | Channel ID for activity logs (e.g. `-100...`) |
| `CHANNELS` | No | Channels to auto-index files from (Bot must be admin) |
| `STREAM_MODE` | No | Enable or disable media streaming mode |

*(Refer to [info.py](info.py) for all available configuration options.)*

---

## 🎮 Essential Commands

| Command | Description | Access |
| :--- | :--- | :---: |
| `/start` | Start the bot & open main menu | Everyone |
| `/settings` | Open group filter & customize settings | Everyone |
| `/plan` / `/myplan` | View pricing or check active premium plan | Everyone |
| `/redeem <code>` | Redeem a premium voucher code | Everyone |
| `/id` / `/info` | Get user/chat ID and information | Everyone |
| `/alive` / `/ping` | Check bot status & response latency | Everyone |
| `/stats` | View database storage & bot statistics | Admin |
| `/broadcast` | Broadcast a message to all bot users | Admin |
| `/grp_broadcast` | Broadcast a message to all connected groups | Admin |
| `/ban` / `/unban` | Manage user ban status | Admin |
| `/add_premium` | Grant premium access to a user | Admin |
| `/deleteall` | Clear all indexed files from database | Admin |
| `/restart` | Restart the bot process | Admin |

---

## 📜 License & Credits

- Licensed under the [MIT License](LICENSE).

### Special Thanks & Credits:
- [⌯ Ꭺɴᴏɴʏᴍᴏᴜs | ×͜× |](https://t.me/BeingXAnonymous)
- [⌯ ᴢɪsʜᴀɴ | ×͜× |](https://t.me/IM_JISSHU)
- [⌯ ʙʜᴀʀᴀᴛʜ | ×͜× |](https://t.me/Bharath_boy)
- [Support Group](https://t.me/Deendayal_Support_Group)
- Thanks to the **DreamXBotz** community and all contributors who worked on the original project.

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=1,12,24&height=100&section=footer" width="100%" alt="Footer Banner"/>
</p>
