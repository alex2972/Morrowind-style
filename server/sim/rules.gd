class_name Rules
extends RefCounted
## Pure game formulas: no state, no I/O. The numbers they work on come from content rows.

const MAX_LEVEL := 20
const GCD := 1.5                 ## global cooldown after any ability, seconds
const MELEE_RANGE := 3.6
const POTION_COOLDOWN := 10.0
const PACK_SLOTS := 28           ## RuneScape-sized backpack
const COMBAT_TIMEOUT := 5.0      ## seconds without hits before regeneration resumes
const NPC_REACH := 2.2
const NPC_WALK_SPEED := 1.3      ## m/s when wandering or walking a path
const WALK_CLIP_SPEED := 1.06    ## m/s the walk clip shows at rate 1 on an NPC body (client plays rate = speed / this)
const RUN_CLIP_SPEED := 4.9
const INTERACT_RANGE := 5.0
const PARTY_RANGE := 60.0        ## members this close share kills, XP and quest credit
const PARTY_MAX := 5

static func xp_to_next(level: int) -> int:
	## Experience needed to go from `level` to `level + 1`.
	if level >= MAX_LEVEL:
		return 0
	return int(round(100.0 * pow(float(level), 1.55) + 40.0 * (level - 1)))

static func kill_xp(player_level: int, enemy_level: int, factor: float) -> int:
	var diff := enemy_level - player_level
	if diff <= -5:
		return 0   # grey: too low to be worth anything
	return int(round((45.0 + 10.0 * enemy_level) * clampf(1.0 + 0.12 * diff, 0.2, 1.6) * factor))

static func party_share(members: int) -> float:
	## Each member's share of a kill's XP: a bonus for grouping, split between members.
	return 1.0 if members <= 1 else (1.0 + 0.1 * members) / members

static func max_health(cls: Dictionary, level: int) -> float:
	return float(cls.health_base) + float(cls.health_per_level) * (level - 1)

static func max_resource(cls: Dictionary, level: int) -> float:
	return float(cls.resource_base) + float(cls.resource_per_level) * (level - 1)

static func melee_damage(cls: Dictionary, level: int) -> float:
	return float(cls.melee_base) + float(cls.melee_per_level) * (level - 1)

static func armor(cls: Dictionary, level: int) -> float:
	return float(cls.armor) + 2.0 * (level - 1)

static func npc_armor(level: int) -> float:
	return 8.0 * level

static func mitigate(amount: float, armor_value: float) -> float:
	return amount * 100.0 / (100.0 + armor_value)

static func scaled(amount: float, level: int) -> float:
	## Ability amounts grow with the caster's level.
	return amount * (1.0 + 0.1 * (level - 1))

static func effect_amount(effect: Dictionary, cls: Dictionary, level: int) -> float:
	var amount := scaled(float(effect.amount), level)
	if effect.get('weapon', false):
		return amount + melee_damage(cls, level)
	return amount * maxf(float(cls.power), 1.0)

static func ability_text(ability: Dictionary, cls: Dictionary, level: int) -> String:
	var text := str(ability.description)
	for e in ability.effects:
		var n := str(int(effect_amount(e, cls, level)))
		text = text.replace('{damage}', n).replace('{heal}', n).replace('{dot}', n)
	return text

static func safe_name(raw: String) -> String:
	var result := ''
	for ch in raw.strip_edges():
		if ch.to_lower() in "abcdefghijklmnopqrstuvwxyz '-":
			result += ch
	result = result.strip_edges()
	return result.left(18).capitalize() if result.length() > 0 else ''
