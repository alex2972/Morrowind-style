"""Writes the realm's starting content: server/content/seed/content.json, one list of rows per database table.

The realm copies these rows into its SQLite database the first time it creates it (or when a content table is
empty). After that the DATABASE is the source of truth: edit it with DB Browser for SQLite and type /reload
in game (admin accounts) or restart the realm. Re-run this script only to change what new databases start with.
Run: python tools/build_game_data.py
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / 'server' / 'content' / 'seed' / 'content.json'

races = [
    dict(id='human', name='Human', scale=1.0, playable=1, sort=0,
         description='Imperials of the old Cyrodiilic line: adaptable, stubborn and found in every port.',
         skins=['ffffff', 'f0ddcc', 'd6b89c', 'a88a70']),
    dict(id='high_elf', name='High Elf', scale=1.07, playable=1, sort=1,
         description='Altmer of the Summerset Isles: tall, golden-skinned and proud. (Placeholder: shares the human body for now.)',
         skins=['fff8dc', 'f7ecc4', 'ecdcac', 'dcc794']),
    dict(id='dark_elf', name='Dark Elf', scale=1.0, playable=1, sort=2,
         description='Dunmer of Morrowind, ash-skinned and red-eyed. (Placeholder: shares the human body for now.)',
         skins=['b4bec4', '9ca8b0', '86929a', '717c84']),
]

classes = [
    dict(id='warrior', name='Warrior', resource='rage', sort=0,
         description='A front-line fighter in heavy steel. Builds rage by dealing and taking blows, and spends it on crushing strikes.',
         health_base=140, health_per_level=22, resource_base=100, resource_per_level=0, melee_base=11, melee_per_level=2.4,
         swing=2.2, power=0.0, armor=20),
    dict(id='priest', name='Priest', resource='mana', sort=1,
         description='A servant of the Nine. Smites the wicked with holy fire and mends the wounds of allies.',
         health_base=95, health_per_level=14, resource_base=150, resource_per_level=24, melee_base=6, melee_per_level=1.2,
         swing=2.4, power=1.0, armor=6),
    dict(id='mage', name='Mage', resource='mana', sort=2,
         description='A scholar of destruction. Hurls fire and frost from afar, but falls quickly when the enemy closes in.',
         health_base=85, health_per_level=12, resource_base=165, resource_per_level=26, melee_base=5, melee_per_level=1.0,
         swing=2.4, power=1.15, armor=4),
]

def ability(id, name, level, icon, cost, cooldown, cast_time, range, target, effects, anim, fx, description):
    return dict(id=id, name=name, level=level, icon=icon, cost=cost, cooldown=cooldown, cast_time=cast_time, range=range,
                target=target, effects=effects, anim=anim, fx=fx, description=description)

abilities = [
    ability('heroic_strike', 'Heroic Strike', 1, 'atlas:1', 15, 0, 0, 4.0, 'enemy', [{'type': 'damage', 'amount': 22, 'weapon': True}],
            'sword_slash_a', 'melee', 'A strong attack that adds {damage} damage. 15 rage.'),
    ability('thunder_clap', 'Thunder Clap', 3, 'gen:thunder_clap', 20, 6, 0, 0, 'self_area', [{'type': 'area_damage', 'amount': 18, 'radius': 8.0}],
            'sword_slash_c', 'thunder', 'Blasts all nearby enemies for {damage} damage. 20 rage, 6 sec cooldown.'),
    ability('sundering_blow', 'Sundering Blow', 5, 'atlas:2', 25, 10, 0, 4.0, 'enemy', [{'type': 'damage', 'amount': 46, 'weapon': True}],
            'sword_slash_b', 'melee', 'A crushing blow for {damage} damage. 25 rage, 10 sec cooldown.'),
    ability('smite', 'Smite', 1, 'atlas:3', 20, 0, 1.8, 30.0, 'enemy', [{'type': 'damage', 'amount': 30}],
            'spell_cast', 'holy', 'Holy fire for {damage} damage. 1.8 sec cast, 20 mana.'),
    ability('lesser_heal', 'Lesser Heal', 1, 'atlas:4', 30, 0, 2.0, 30.0, 'ally', [{'type': 'heal', 'amount': 55}],
            'spell_cast', 'healing', 'Heals a friendly target, or you, for {heal}. 2 sec cast, 30 mana.'),
    ability('shadow_word_pain', 'Shadow Word: Pain', 4, 'gen:shadow_word_pain', 25, 0, 0, 30.0, 'enemy',
            [{'type': 'dot', 'amount': 9, 'ticks': 6, 'interval': 3.0}],
            'spell_cast', 'shadow', 'Shadow damage: {dot} every 3 sec for 18 sec. 25 mana.'),
    ability('fireball', 'Fireball', 1, 'gen:fireball', 25, 0, 2.2, 32.0, 'enemy', [{'type': 'damage', 'amount': 36}],
            'spell_cast', 'fire', 'Hurls a fiery ball for {damage} damage. 2.2 sec cast, 25 mana.'),
    ability('fire_blast', 'Fire Blast', 3, 'gen:fire_blast', 30, 8, 0, 20.0, 'enemy', [{'type': 'damage', 'amount': 28}],
            'spell_cast', 'fire', 'Instant fire damage: {damage}. 30 mana, 8 sec cooldown.'),
    ability('frostbolt', 'Frostbolt', 5, 'gen:frostbolt', 30, 0, 2.6, 32.0, 'enemy', [{'type': 'damage', 'amount': 50}],
            'spell_cast', 'frost', 'A bolt of frost for {damage} damage. 2.6 sec cast, 30 mana.'),
]

class_abilities = []
for cid, ids in (('warrior', ['heroic_strike', 'thunder_clap', 'sundering_blow']),
                 ('priest', ['smite', 'lesser_heal', 'shadow_word_pain']),
                 ('mage', ['fireball', 'fire_blast', 'frostbolt'])):
    for i, aid in enumerate(ids):
        class_abilities.append(dict(class_id=cid, ability_id=aid, sort=i))

items = [
    dict(id='health_tonic', name='Crimson Tonic', icon='atlas:5', price=12, stack=10, quest_item=0, use_effect={'heal': 70},
         description='Restores 70 health. Tonics share a 10 sec cooldown.'),
    dict(id='mana_tonic', name='Azure Tonic', icon='atlas:6', price=12, stack=10, quest_item=0, use_effect={'mana': 70},
         description='Restores 70 mana. Tonics share a 10 sec cooldown.'),
    dict(id='bandit_token', name='Brineroot Token', icon='atlas:7', price=2, stack=50, quest_item=0, use_effect={},
         description='A crude tin token carried by the marsh bandits. Traders pay a little for them.'),
    dict(id='harbour_letter', name='Sealed Letter', icon='gen:letter', price=0, stack=1, quest_item=1, use_effect={},
         description='A letter from Harbourmaster Ilvar to the Chapel of Veyr.'),
]

def npc(id, name, **kw):
    row = dict(id=id, name=name, subtitle='', sex='male', race_id='human', skin=0, role='', hostile=0, level=12, health=880,
               damage_min=0, damage_max=0, swing=2.4, aggro_radius=0, leash_radius=30, respawn_seconds=30, speed=3.5,
               xp_factor=1.0, gold_min=0, gold_max=0, greeting='')
    row.update(kw)
    return row

npc_templates = [
    npc('marsh_bandit', 'Brineroot Bandit', skin=3, role='enemy', hostile=1, level=2, health=110, damage_min=6, damage_max=9,
        swing=2.4, aggro_radius=9, leash_radius=32, respawn_seconds=30, speed=3.6, xp_factor=1.0, gold_min=3, gold_max=8),
    npc('ash_cultist', 'Ash Cultist', sex='female', race_id='dark_elf', skin=2, role='enemy', hostile=1, level=4, health=170,
        damage_min=9, damage_max=13, swing=2.2, aggro_radius=11, leash_radius=32, respawn_seconds=40, speed=3.8, xp_factor=1.2,
        gold_min=6, gold_max=14),
    npc('harbourmaster', 'Harbourmaster Ilvar', subtitle='Veyr Harbour', skin=2, role='quest',
        greeting='Welcome to Veyr, traveler. The tide brings all sorts ashore - most of them useful, some of them trouble.'),
    npc('trader', 'Gelvar the Trader', subtitle='General goods', skin=1, role='vendor',
        greeting='Tonics, fresh from the Chapel stills. Coin first, questions after.'),
    npc('priestess', 'Priestess Aldra', subtitle='Chapel of Veyr', sex='female', race_id='high_elf', skin=1, role='quest',
        greeting='The Nine watch over this town, though lately the ash wind carries other voices.'),
    npc('guard_captain', 'Captain Varro', subtitle='Town Watch', skin=2, role='guard',
        greeting='Keep your blade sheathed in town. Outside the walls, the marsh west along the coast road is crawling with bandits, and cultists haunt the Grey Ash Barrens.'),
]

npc_loot = [
    dict(template_id='marsh_bandit', item_id='bandit_token', chance=0.6, count_min=1, count_max=2),
    dict(template_id='marsh_bandit', item_id='health_tonic', chance=0.15, count_min=1, count_max=1),
    dict(template_id='ash_cultist', item_id='mana_tonic', chance=0.2, count_min=1, count_max=1),
    dict(template_id='ash_cultist', item_id='health_tonic', chance=0.2, count_min=1, count_max=1),
]

npc_vendor = [
    dict(template_id='trader', item_id='health_tonic', mode='sell'),
    dict(template_id='trader', item_id='mana_tonic', mode='sell'),
    dict(template_id='trader', item_id='bandit_token', mode='buy'),
]

spawns = [
    dict(id='harbourmaster', zone_id='veyr', template_id='harbourmaster', x=-8.0, z=66.0, yaw=180),
    dict(id='trader', zone_id='veyr', template_id='trader', x=8.0, z=34.0, yaw=270),
    dict(id='priestess', zone_id='veyr', template_id='priestess', x=5.0, z=-48.0, yaw=0),
    dict(id='guard_captain', zone_id='veyr', template_id='guard_captain', x=-6.0, z=6.0, yaw=90),
]
for i, (x, z) in enumerate([(-100, 31), (-110, 14), (-118, 36), (-125, 21), (-140, 16), (-132, 4)]):
    spawns.append(dict(id='bandit_%d' % (i + 1), zone_id='veyr', template_id='marsh_bandit', x=x, z=z, yaw=0))
for i, (x, z) in enumerate([(128, -96), (140, -108), (120, -116), (146, -90), (132, -124)]):
    spawns.append(dict(id='cultist_%d' % (i + 1), zone_id='veyr', template_id='ash_cultist', x=x, z=z, yaw=0))

quests = [
    dict(id='marsh_trouble', title='Trouble in the Marsh', giver_id='harbourmaster', turn_in_id='harbourmaster', level=1,
         requires_id=None, sort=0, reward_xp=250, reward_gold=25,
         offer_text="Bandits out of Brineroot Marsh, west along the coast road, have been robbing every cart that passes. The Watch won't go into the mud. You might.\n\nThin their numbers: put down five of them.",
         progress_text='Five bandits, traveler. Take the road west out of the Imperial Quarter into the marsh.',
         complete_text="Five fewer thieves on my road. Here's your pay, and my thanks."),
    dict(id='word_to_chapel', title='A Word to the Chapel', giver_id='harbourmaster', turn_in_id='priestess', level=1,
         requires_id='marsh_trouble', sort=1, reward_xp=150, reward_gold=10,
         offer_text="Those bandits weren't just thieves - one carried ash-cult markings. Take this letter to Priestess Aldra at the High Chapel, at the north end of the main street.",
         progress_text='The Chapel is north, up the cobbled road past the plaza.',
         complete_text='Ash-cult markings, this close to Veyr... Thank you for bringing this to me, traveler.'),
    dict(id='ashes_and_embers', title='Ashes and Embers', giver_id='priestess', turn_in_id='priestess', level=3,
         requires_id='word_to_chapel', sort=2, reward_xp=600, reward_gold=40,
         offer_text='Cultists gather in the Grey Ash Barrens, north-east of the Shell Ward, chanting over the ash. Scatter them before their rites bear fruit.\n\nDefeat four Ash Cultists.',
         progress_text='The Barrens lie north-east, beyond the Shell Ward plateau. Be careful - they hit harder than any bandit.',
         complete_text='The chanting has stopped. The Nine are grateful, and so am I.'),
]

quest_objectives = [
    dict(quest_id='marsh_trouble', idx=0, type='kill', target='marsh_bandit', count=5, label='Brineroot Bandits slain'),
    dict(quest_id='word_to_chapel', idx=0, type='deliver', target='harbour_letter', count=1, label='Deliver the letter to Priestess Aldra'),
    dict(quest_id='ashes_and_embers', idx=0, type='kill', target='ash_cultist', count=4, label='Ash Cultists defeated'),
]

quest_items = [
    dict(quest_id='marsh_trouble', item_id='health_tonic', count=3, kind='reward'),
    dict(quest_id='word_to_chapel', item_id='harbour_letter', count=1, kind='start'),
    dict(quest_id='ashes_and_embers', item_id='mana_tonic', count=2, kind='reward'),
    dict(quest_id='ashes_and_embers', item_id='health_tonic', count=2, kind='reward'),
]

skills = [
    dict(id='woodcutting', name='Woodcutting', icon='', sort=0, description='Fell trees for logs.'),
    dict(id='fishing', name='Fishing', icon='', sort=1, description='Catch fish from the coast and the marsh pools.'),
    dict(id='mining', name='Mining', icon='', sort=2, description='Dig ore from the Hollow Mine.'),
    dict(id='smithing', name='Smithing', icon='', sort=3, description='Smelt ore and forge weapons and armour.'),
]

# Table order matters: rows are inserted top to bottom, so referenced rows come first.
tables = {
    'races': races, 'classes': classes, 'abilities': abilities, 'class_abilities': class_abilities, 'items': items,
    'npc_templates': npc_templates, 'npc_loot': npc_loot, 'npc_vendor': npc_vendor, 'spawns': spawns,
    'quests': quests, 'quest_objectives': quest_objectives, 'quest_items': quest_items, 'skills': skills,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({'order': list(tables), 'tables': tables}, indent=1), encoding='utf-8')
print('wrote', OUT, sum(len(v) for v in tables.values()), 'rows')
