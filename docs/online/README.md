# Realm architecture

Veyr is a client–server game. The **realm** owns everything: the database, the content, the simulation
and every rule. The **client** sends intents ("cast Fireball on bandit_3", "use the tonic in slot 4") and
shows what the realm tells it. Offline play runs the same realm inside the game process, so there is only
one code path.

```
shared/            the contract (the only code both sides load)
  protocol.gd        protocol version, tick rates, every message name and its fields
  link.gd            RPC transport: c_hello, c_msg, c_move  /  s_msg, s_state

server/            the authoritative realm - loads no art
  realm.gd           lifecycle, fixed 20 Hz tick, event bus, entity registry, saves
  server.tscn        dedicated entry point (run_server.bat; config/server.cfg)
  net/
    gateway.gd       ENet server, sessions (connected -> lobby -> world), version check, rate limits, routing
    accounts.gd      PBKDF2 sign-in on a worker thread, character lobby (create / delete / enter)
    replication.gd   interest management and state packets
  sim/             one module per game system (all extend system.gd)
    rules.gd         pure formulas: XP curve, damage, armour, party share...
    movement.gd      validates client positions (11 m/s cap), teleports, /unstuck
    combat.gd        abilities, casts, GCD, cooldowns, auto-attack, DoTs, AoE, regen, death, release
    ai.gd            spawns, respawns, aggro, threat, chase, leash/evade
    progression.gd   XP and levels
    inventory.gd     28-slot pack with stacks, gold, item use; all-or-nothing changes
    loot.gd          gold and drop tables
    quests.gd        data-driven objectives (kill, talk, collect, deliver)
    dialogue.gd      NPC conversations, quest offers and turn-ins, vendors
    chat.gd          chat and slash commands (/p, /invite, /accept, /leave, /who, /reload, /help)
    party.gd         invites, leader, party chat, member vitals, shared credit, round-robin loot
  persistence/
    database.gd      SQLite (godot-sqlite add-on): WAL, foreign keys, migrations, transactions
    schema.gd        append-only list of schema migrations
    repository.gd    every read and write of player data (the only place with player SQL)
  content/
    content.gd       loads and validates content tables; hot reload; the client's display catalog
    seed/content.json  starting rows for a new database (written by tools/build_game_data.py)
  world/
    zone.gd          a zone: its own physics world (baked collision), entity grid, regions
    veyr/            collision.scn + zone.json, baked by tools/bake_server_world.gd

client/            presentation and input only
  main.gd            boot: world, front end, offline realm
  net/session.gd     connection, lobby, applying state, turning input into intents
  content/catalog.gd display data from the realm + icons, body scenes, placeholder tints
  ui/, actors/, player/, world/
```

## How a frame of the game flows

1. The **client** moves its own character (WoW-style responsiveness) and sends `c_move` 15 times a second.
   `movement.gd` accepts the position or snaps the client back if it moved implausibly fast.
2. Input becomes a **message**: `c_msg('cast', {ability, target})`. The gateway drops floods (20/s with
   bursts of 40) and routes the message to the handler the combat system registered.
3. **Systems** validate (known ability, cooldown, resource, range, line of sight against the zone's baked
   collision) and change entity state. Cross-system effects go through events: `npc_killed` gives XP
   (progression), gold and drops (loot) and quest progress (quests) to everyone the party system credits.
4. **Replication** runs every second tick (10 Hz). For each player it asks the zone grid what is within
   120 m:
   - Newly visible actors are introduced with a reliable `appear` that carries static info and the quest
     marker the realm computed for that player. Actors that leave view get a `vanish`.
   - The unreliable, zstd-compressed state packet contains only actors whose dynamic state changed, plus
     a staggered refresh so a lost packet heals within about a second. Every packet also carries your
     vitals and your party's.
   - Your character sheet (level, XP, pack, quest log, abilities with tooltips, stats) is sent reliably
     whenever a system marks it dirty.
5. **Saves**: each character is saved every 60 s, plus on level-up, quest changes and logout. A save is a
   single transaction, so a crash never leaves half a character or a duplicated item.

## What the client never sees

Prices, NPC stats, drop tables, quest prerequisites and objectives, and ability formulas. Those stay on
the realm. The client gets names, icons, descriptions and the numbers it must display, such as tooltips
with damage already computed for your level and the remaining cooldowns. Quest markers come from the
realm too.

## The database (SQLite)

- **Location**:
  - Offline: `%APPDATA%/Godot/app_userdata/Veyr - A Morrowind-style Walk/offline/veyr.db`
  - Dedicated realm: `.../realm/veyr.db` (set in `config/server.cfg`)
- **Browsing and editing**: DB Browser for SQLite or DBeaver. Thanks to WAL mode, browsing never blocks
  the running realm.
- **Player tables**:
  - `accounts` (set `is_admin = 1` to allow `/reload`)
  - `characters`
  - `character_items` (container/slot/item/count)
  - `character_quests` (state plus a JSON progress array)
  - `character_skills`
- **Content tables**: `races`, `classes`, `abilities`, `class_abilities`, `items`, `npc_templates`,
  `npc_loot`, `npc_vendor`, `spawns`, `quests`, `quest_objectives`, `quest_items` and `skills`. A few
  columns hold small JSON values:
  - `abilities.effects`, for example `[{"type":"damage","amount":30}]`
  - `items.use_effect`, for example `{"heal":70}`
  - `races.skins`
- **Changing content**: edit rows, then type `/reload` in game. The realm validates the new content and
  refuses it with a list of problems (an unknown item or a missing quest objective, say) rather than
  breaking the world. NPCs respawn from the new templates.
- **Changing the schema**: add a migration at the end of `server/persistence/schema.gd`. Never edit one
  that has already run.
- **The seed** only fills empty tables in a new database. After that, the database is the source of truth.
- **Old saves**: the JSON saves from the first online version are imported once into an empty database.

## Zones

A zone is the unit of scale. `server/world/<zone>/` holds its baked collision and `zone.json` (spawn
point, regions). The realm loads each zone into its own physics world, so even the in-game offline realm
never touches the client's scene. Today there is one zone, `veyr`. The tutorial island, dungeons and party
instances will each be a zone. Moving zones into separate processes later doesn't change any system,
because systems already reach everything through `realm.zone_of(entity)`.

After rebuilding the world, re-bake it with `tools/bake_server_world.gd` (`tools/rebuild.ps1` does this).

## Builds

`export_presets.cfg` has two presets:
- **Windows Client**: the game. It includes the realm, for offline play.
- **Windows Dedicated Server**: Godot's dedicated-server export, with art stripped. It boots straight
  into `server/server.tscn`.

Install the 4.7.1 export templates (Editor → Manage Export Templates) to build them. In development,
`run_server.bat` runs the realm from the project.

## Adding things

- **A new item, NPC, quest or spawn**: add rows in the database and type `/reload`. No code changes.
- **A new ability**: add an `abilities` row, plus a `class_abilities` row to give it to a class. New
  *effect types* go in `combat.gd`'s `_resolve`.
- **A new system** (for example woodcutting): add `server/sim/<name>.gd` extending `RealmSystem`, then
  register it in `realm.gd`. Use its hooks:
  - `setup` to register messages and listen to events
  - `player_joined` to load its data
  - `write_save` and `write_sheet`
  - `tick`

  Add its tables with a new migration, and its message names to `shared/protocol.gd` (bump `VERSION`).
- **Load tests**: `tools/bot_client.gd` is a protocol-only client. Spawn many of them against a
  dedicated realm.

## Checks

```
Godot --headless --fixed-fps 60 --path . --script res://tools/verify_online.gd
```

The test runs an offline realm, the game client and a bot. It covers:
- the database and seed; the catalog carrying no rules
- account and character creation; entering the world; interest management
- server-sent quest markers, dialogue and quests
- a Fireball kill with XP and quest credit
- a second player: visibility, party invite, party frames, a shared kill
- turn-in and rewards; content hot reload from the database; death and release
- logout and a fresh sign-in with everything persisted
