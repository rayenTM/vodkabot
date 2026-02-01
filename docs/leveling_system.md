# Leveling System Documentation

## Overview
The leveling system has been overhauled to provide a more balanced progression experience. The previous linear or fast-paced leveling has been replaced with a **Quadratic Scaling** system, making higher levels progressively harder to reach. Additionally, server administrators now have full control over the XP rate.

## 1. Leveling Formula
We now use a quadratic formula to determine the XP required for each level.

**Formula:**
```
Total XP Required = 100 * (Level - 1)^2
```

### Progression Table (Examples)
| Level | Total XP Required | Delta (XP needed from prev level) |
| :--- | :--- | :--- |
| **1** | 0 XP | 0 |
| **2** | 100 XP | 100 |
| **3** | 400 XP | 300 |
| **4** | 900 XP | 500 |
| **5** | 1,600 XP | 700 |
| **10** | 8,100 XP | - |
| **20** | 36,100 XP | - |
| **50** | 240,100 XP | - |

**Why this change?**
*   **Early Game:** Levels 1-5 are still relatively quick to attain, keeping new members engaged.
*   **Late Game:** Higher levels require significantly more activity, preventing users from "maxing out" the system too quickly and making high ranks more prestigious.

## 2. XP Rate Configuration
Admins can now configure how much XP is awarded per message. This allows you to fine-tune the speed of the server's leveling independent of the formula.

*   **Default Rate:** 10 XP per message.
*   **Configuration:** Stored per-guild in the database.

### Commands
*   `/level set_xp_rate <amount>`: Sets the XP gained per valid message.
    *   *Example:* `/level set_xp_rate 15` increases leveling speed by 50%.
    *   *Example:* `/level set_xp_rate 5` slows leveling speed by 50%.

## 3. Anti-Spam & Rules
*   **Bot Ignore:** Messages from bots do not grant XP.
*   **DM Ignore:** Direct Messages to the bot do not grant XP.
*   **Cooldown:** (Implicitly handled by natural conversation flow, but code allows one gain per message event processed).

## 4. Admin Tools
Several tools are available to manage user levels manually:

*   `/level set_level <member> <level>`: Instantly sets a user to a specific level.
    *   *Note:* This resets their XP to the *exact minimum* required for that level.
*   `/level reset <member>`: Resets a user's XP to the *exact minimum* required for their current level.
*   `/level recalculate <member>`: Recalculates a user's level based on their current XP (fixes "Low Level, High XP" issues).
*   `/level give_xp <member> <amount>`: Adds (or removes with negative numbers) a specific amount of XP.
*   `/sync_xp <limit>`: Scans the last `<limit>` messages in the current channel and awards XP retroactively. Useful for backfilling XP if the bot was offline or for new installs on existing servers.

## 5. Role Rewards
Role rewards are automatically assigned when a user levels up.

*   `/level set_reward <level> <role>`: Assigns a role to be given at a specific level.
*   `/level remove_reward <level>`: Removes the reward for that level.
*   `/level rewards`: Lists all currently configured level rewards.
