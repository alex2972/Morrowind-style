class_name Doors
extends RefCounted
## Doors that load into another space (Skyrim-style "E  Enter"). Shared by the client, which shows the
## prompt and builds the rooms, and the realm, which checks the player is at the door before moving them.
##
## Interiors are rooms built far outside the map (high above the sea, past its edge) in the same zone, so
## moving through a door is a plain teleport and everything else (combat, party, chat) keeps working.

const RANGE := 3.2           ## metres from the eyes to the door at which the prompt shows
const REALM_RANGE := 5.0     ## the realm's (more forgiving) horizontal check against latency

const TAVERN_NAME := 'The Lantern & Gull'
const TAVERN_ORIGIN := Vector3(0.0, 80.0, 420.0)    ## centre of the taproom floor
const TAVERN_HALF := Vector3(6.0, 4.2, 4.5)          ## inner half-size in x and z; y is the ceiling height

## id -> pos: centre of the door leaf in world space; facing: the way its front looks;
## action/label: prompt text; to/to_yaw: where using it puts the player (feet, radians)
const DOORS := {
	'tavern_enter': {
		'pos': Vector3(-13.22, 5.45, 48.6), 'facing': Vector3(1, 0, 0),
		'action': 'Enter', 'label': TAVERN_NAME,
		'to': TAVERN_ORIGIN + Vector3(4.7, 0.05, 0.0), 'to_yaw': PI * 0.5,
	},
	'tavern_exit': {
		'pos': TAVERN_ORIGIN + Vector3(5.93, 1.15, 0.0), 'facing': Vector3(-1, 0, 0),
		'action': 'Exit', 'label': 'Veyr, Imperial Quarter',
		'to': Vector3(-11.4, 4.4, 48.6), 'to_yaw': -PI * 0.5,
	},
}

static func interior_at(p: Vector3) -> String:
	## Name of the interior containing p, or '' outdoors.
	var d := p - TAVERN_ORIGIN
	if absf(d.x) < TAVERN_HALF.x + 1.0 and absf(d.z) < TAVERN_HALF.z + 1.0 and d.y > -3.0 and d.y < TAVERN_HALF.y + 3.0:
		return TAVERN_NAME
	return ''
