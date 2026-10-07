class_name Protocol
extends RefCounted
## The contract between client and realm: version, port, timing and the message names both sides use.
## Bump VERSION whenever a message changes shape; the realm refuses clients with another version.
##
## Transport (shared/link.gd):
##   client -> realm   c_hello(version, username, password, creating)   reliable
##                     c_msg(type, data)                                reliable, one of C_* below
##                     c_move(pos, yaw, clip, rate)                     unreliable, 15 Hz
##   realm -> client   s_msg(type, data)                                reliable, one of S_* below
##                     s_state(packed, size)                            unreliable, zstd [me, actors]

const VERSION := 3
const PORT := 27840
const TICK_RATE := 20                ## realm simulation ticks per second
const SNAPSHOT_EVERY := 2            ## ticks between state packets (10 Hz)
const MOVE_RATE := 15.0              ## client position updates per second

# client -> realm
const C_CREATE_CHARACTER := 'create_character'   ## {name, sex, race, class, skin}
const C_DELETE_CHARACTER := 'delete_character'   ## {id}
const C_ENTER := 'enter'                         ## {id}
const C_LEAVE := 'leave'                         ## {}
const C_TARGET := 'target'                       ## {id}
const C_ATTACK := 'attack'                       ## {on}
const C_CAST := 'cast'                           ## {ability, target}
const C_USE_ITEM := 'use_item'                   ## {slot} or {item}
const C_SWAP_SLOTS := 'swap_slots'               ## {a, b}
const C_INTERACT := 'interact'                   ## {id}
const C_DIALOGUE := 'dialogue'                   ## {npc, choice}
const C_RELEASE := 'release'                     ## {}
const C_UNSTUCK := 'unstuck'                     ## {}
const C_USE_DOOR := 'use_door'                   ## {door}  (shared/doors.gd)
const C_ABANDON_QUEST := 'abandon_quest'         ## {quest}
const C_CHAT := 'chat'                           ## {text}  (slash commands are parsed by the realm)
const C_PARTY_RESPOND := 'party_respond'         ## {accept}

# realm -> client
const S_AUTH := 'auth'               ## {ok, message, roster}
const S_CATALOG := 'catalog'         ## display data: races, classes, items, rules, version
const S_ENTER := 'enter'             ## {eid, name, sex, race, class, skin, pos, yaw, zone}
const S_SHEET := 'sheet'             ## level, xp, gold, inventory slots, quest log, abilities, stats
const S_APPEAR := 'appear'           ## {id, info}  an actor came into view (or its info changed)
const S_VANISH := 'vanish'           ## {id}
const S_EVENT := 'event'             ## combat, chat, xp, level, death... see client/net/session.gd
const S_DIALOGUE := 'dialogue'       ## {npc, name, subtitle, text, options} or {close}
const S_TELEPORT := 'teleport'       ## {pos, yaw}
const S_PARTY := 'party'             ## {leader, members:[{eid, name, level, class}]} or {}
