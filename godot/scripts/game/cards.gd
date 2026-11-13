class_name Cards
extends RefCounted
## Combat action cards as the combat mockup lists them (Combat v14: names, sources, AP, icons, text), with
## what each one does in the loop. Card rules: design/03 Classes & combat.md -> Combat; Martial class cards;
## the spell sections. ap = -1 means the AP cost isn't set in the docs (the card shows "?" and can't be used,
## as in the mockup).
##   kind: "move", "attack" (flip to hit), "save" (the foe flips to save), "ally" (no roll), "self", "breath" (a line,
##         aimed by a lit hex), "cell" (an empty hex: Glimmerstep)
##   limit: "" (repeatable basic), "turn" (once per turn: the default), "fight" (once per fight)
##   ab: the score an attack flips (default: the character's weapon ability); dmg: a set damage instead of the score
## Racial cards and racial spells (design/03 -> Races, Racial spells): text from the creator's (CreatorData), as the docs
## give it; amounts in Rules (design/06 -> First playable -> Races).

const SRC := {
	"basic": {"band": "#BFAE8E", "ink": "#5A5040", "label": "Basic", "icon_ink": "#33403B"},
	"weapon": {"band": "#5F7F99", "ink": "#3E5A70", "label": "Weapon", "icon_ink": "#3E5A70"},
	"klass": {"band": "#B5532F", "ink": "#9A4A12", "label": "Class", "icon_ink": "#9A4A12"},
	# PLACEHOLDER colours: the creator's racial card and elven spell bands, with class ink.
	"race": {"band": "#B5532F", "ink": "#9A4A12", "label": "Racial card", "icon_ink": "#9A4A12"},
	"elven": {"band": "#3E6F8C", "ink": "#2F5670", "label": "Elven spell", "icon_ink": "#2F5670"},
	"bloodline": {"band": "#3E6F8C", "ink": "#2F5670", "label": "Bloodline spell", "icon_ink": "#2F5670"},
}

const ALL := {
	"move": {"n": "Move", "src": "basic", "ap": 1, "kind": "move", "limit": "", "icon": "move", "desc": "Move a set number of hexes."},
	"attack": {"n": "Attack", "src": "basic", "ap": 1, "kind": "attack", "limit": "", "range": 1, "desc": "Basic attack with your %s."},
	"defend": {"n": "Defend", "src": "basic", "ap": 1, "kind": "self", "limit": "turn", "icon": "defend", "effect": "defend", "desc": "Defend or brace."},
	"use_item": {"n": "Use item", "src": "basic", "ap": 1, "kind": "self", "limit": "turn", "icon": "potion", "effect": "item", "desc": "Use an equipped consumable."},
	"parry": {"n": "Parry", "src": "weapon", "ap": 1, "kind": "self", "limit": "turn", "icon": "parry", "effect": "parry", "desc": "Longsword: block the next melee hit."},
	"block": {"n": "Block", "src": "weapon", "ap": 1, "kind": "self", "limit": "turn", "icon": "shield", "effect": "defend", "desc": "Shield: reduce damage this turn."},
	"shield_bash": {"n": "Shield Bash", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "icon": "bash", "rider": "push", "desc": "Shield: push the foe 1 hex away."},
	"second_wind": {"n": "Second Wind", "src": "klass", "ap": 1, "kind": "self", "limit": "fight", "icon": "heart", "effect": "heal", "desc": "Fighter: heal yourself."},
	"action_surge": {"n": "Action Surge", "src": "klass", "ap": 1, "kind": "self", "limit": "fight", "icon": "bolt", "effect": "surge", "desc": "Fighter: gain 3 bonus AP this turn (net +2)."},
	"trip": {"n": "Trip", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "icon": "trip", "rider": "prone", "desc": "Staff: knock an enemy prone."},
	"ward": {"n": "Ward", "src": "weapon", "ap": 1, "kind": "self", "limit": "turn", "icon": "ward", "effect": "ward", "desc": "Staff: a small magic shield."},
	"firebolt": {"n": "Firebolt", "src": "klass", "ap": 1, "kind": "attack", "limit": "turn", "range": Rules.SPELL_RANGE, "ranged": true, "ab": "INT", "icon": "fire", "bonus": 1, "desc": "Blaster spell: one heavy-hitting shot. Flip to hit."},
	"frost_ray": {"n": "Frost Ray", "src": "klass", "ap": 1, "kind": "attack", "limit": "turn", "range": Rules.SPELL_RANGE, "ranged": true, "ab": "INT", "icon": "snow", "rider": "slow", "slow": Rules.FROST_SLOW, "desc": "Blaster spell: damage, and the foe is slowed on a hit."},
	# The Wizard's other level-1 spells (03 -> Wizard spells; numbers: Wizard level-1 placeholders; text: Ethan, Nov 6, 2026).
	# conc: a concentration spell (03); hp: an HP cost on top of the AP.
	"shocking_grasp": {"n": "Shocking Grasp", "src": "klass", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "ab": "INT", "rider": "push", "icon": "bolt", "desc": "Blaster spell: a melee jolt that pushes the foe 1 hex away."},
	"animated_blade": {"n": "Animated Blade", "src": "klass", "ap": 2, "kind": "cell", "limit": "turn", "range": 1, "effect": "summon", "conc": true, "icon": "sword", "desc": "Summoner spell: a floating sword appears beside you and fights for you."},
	"wisp": {"n": "Wisp", "src": "klass", "ap": 2, "kind": "cell", "limit": "turn", "range": 1, "effect": "summon", "conc": true, "icon": "M12 4a8 8 0 1 0 0 16 8 8 0 1 0 0-16 M12 8a4 4 0 0 1 4 4", "desc": "Summoner spell: a small bound soul appears beside you; it flies and zaps foes at range."},
	"mirror_image": {"n": "Mirror Image", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "effect": "mirror", "save": "INT", "icon": "M8 4a3 3 0 1 0 0 6a3 3 0 1 0 0-6 M16 4a3 3 0 1 0 0 6a3 3 0 1 0 0-6 M3 20c0-4 2-7 5-7s5 3 5 7 M11 20c0-4 2-7 5-7s5 3 5 7", "desc": "Deceiver spell: 2 copies of you appear; foes may hit a copy instead. INT save."},
	"phantom_ally": {"n": "Phantom Ally", "src": "klass", "ap": 2, "kind": "cell", "limit": "turn", "range": Rules.SPELL_RANGE, "effect": "phantom", "save": "INT", "icon": "M6 20V10a6 6 0 0 1 12 0v10l-2-2-2 2-2-2-2 2-2-2z M10 10h.01 M14 10h.01", "desc": "Deceiver spell: a fake party member that foes chase and attack. INT save."},
	"blood_bolt": {"n": "Blood Bolt", "src": "klass", "ap": 1, "kind": "attack", "limit": "turn", "range": Rules.SPELL_RANGE, "ranged": true, "ab": "INT", "bonus": 2, "hp": Rules.BLOOD_BOLT_HP, "icon": "M12 3c3 4 6 8 6 11a6 6 0 0 1-12 0c0-3 3-7 6-11z", "desc": "Ritualist spell: pay 2 HP for a strong hit."},
	"warding_circle": {"n": "Warding Circle", "src": "klass", "ap": 2, "kind": "cell", "limit": "turn", "range": Rules.SPELL_RANGE, "effect": "circle", "conc": true, "icon": "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18 M12 7l4 7H8z", "desc": "Ritualist spell: a circle of 7 hexes; allies in it take 1 less damage."},
	# The Cleric's and Bard's other level-1 spells (03 -> Cleric spells, Bard spells; numbers: Cleric and Bard level-1
	# placeholders, Ethan, Nov 12, 2026: damage the casting score, heals and temporary HP the score + 2, range 5, conditions
	# until the target's next turn ends).
	"searing_touch": {"n": "Searing Touch", "src": "klass", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "ab": "WIS", "icon": "flame", "desc": "Order of Light: melee radiant damage, bonus vs undead. Flip to hit."},
	"shadow_bolt": {"n": "Shadow Bolt", "src": "klass", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "WIS", "ab": "WIS", "effect": "shadow", "icon": "M20 14A8 8 0 1 1 10 4a6 6 0 0 0 10 10z", "desc": "Order of Night: necrotic damage, more if the foe is in darkness (WIS save)."},
	"dread": {"n": "Dread", "src": "klass", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "WIS", "effect": "fear", "icon": "eye", "desc": "Order of Night: a foe is frightened, flipping one fewer coin on its next attack (WIS save)."},
	"shield_of_faith": {"n": "Shield of Faith", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": Rules.SPELL_RANGE, "effect": "faith", "icon": "shield", "desc": "Order of Good: an ally is harder to hit."},
	"bane": {"n": "Bane", "src": "klass", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "CHA", "effect": "bane", "icon": "drop", "desc": "Order of Evil: a foe flips one fewer coin on its next check (CHA save)."},
	"hex": {"n": "Hex", "src": "klass", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "WIS", "effect": "hex", "icon": "heart", "desc": "Order of Evil: every hit on the hexed foe heals the attacker a little (WIS save)."},
	"mockery": {"n": "Mockery", "src": "klass", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "WIS", "ab": "CHA", "icon": "bubble", "desc": "Narrator spell: a cutting insult deals psychic damage (WIS save)."},
	"heroic_tale": {"n": "Heroic Tale", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": Rules.SPELL_RANGE, "ab": "CHA", "effect": "temp", "icon": "star", "desc": "Narrator spell: an ally gains temporary HP."},
	"rousing_tune": {"n": "Rousing Tune", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": Rules.SPELL_RANGE, "conc": true, "effect": "tune", "icon": "M9 18V5l11-2v13 M9 18a3 3 0 1 1-6 0a3 3 0 1 1 6 0 M20 16a3 3 0 1 1-6 0a3 3 0 1 1 6 0", "desc": "Musician spell: an ally flips an extra coin on attacks while you sustain it."},
	"soothing_melody": {"n": "Soothing Melody", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": Rules.SPELL_RANGE, "ab": "CHA", "effect": "heal", "icon": "heart", "desc": "Musician spell: heal an ally a little."},
	"dazzle": {"n": "Dazzle", "src": "klass", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "WIS", "effect": "dazzle", "icon": "sparkle", "desc": "Dancer spell: a foe is mesmerized and its attacks are harder (WIS save)."},
	"blade_twirl": {"n": "Blade Twirl", "src": "klass", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "weapon_reach": true, "effect": "twirl", "icon": "move", "desc": "Dancer spell: a weapon attack, then a free short move. Flip to hit."},
	"rallying_strike": {"n": "Rallying Strike", "src": "klass", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "weapon_reach": true, "effect": "rally", "icon": "swords", "desc": "Leader spell: a weapon attack; an ally gains temporary HP. Flip to hit."},
	"war_cry": {"n": "War Cry", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "effect": "war_cry", "icon": "bubble", "desc": "Leader spell: nearby allies flip an extra coin on their next attack."},
	# The Bard's level-3 and after-level-5 spells (03 -> Bard spells; numbers: Bard level-1 placeholders and Rules).
	"cliffhanger": {"n": "Cliffhanger", "src": "klass", "ap": 2, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "WIS", "effect": "cliffhanger", "icon": "eye", "desc": "Narrator spell: a foe freezes in suspense and skips its next action (WIS save)."},
	"retell": {"n": "Retell", "src": "klass", "ap": 2, "kind": "ally", "limit": "turn", "range": Rules.SPELL_RANGE, "icon": "repeat", "built": false, "desc": "Narrator spell: an ally repeats their last action."},
	"shatter_chord": {"n": "Shatter Chord", "src": "klass", "ap": 2, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "CON", "effect": "burst", "radius": 1, "ab": "CHA", "icon": "bolt", "desc": "Musician spell: a sonic burst in an area. Everyone in it makes a CON save."},
	"battle_hymn": {"n": "Battle Hymn", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "conc": true, "effect": "battle_hymn", "icon": "M9 18V5l11-2v13 M9 18a3 3 0 1 1-6 0a3 3 0 1 1 6 0 M20 16a3 3 0 1 1-6 0a3 3 0 1 1 6 0", "desc": "Musician spell: nearby allies deal extra damage while you sustain it."},
	"captivate": {"n": "Captivate", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "save": "WIS", "effect": "captivate", "icon": "sparkle", "desc": "Dancer spell: nearby foes must watch you and can't target others (WIS save)."},
	"whirlwind_dance": {"n": "Whirlwind Dance", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "effect": "whirlwind", "icon": "swords", "desc": "Dancer spell: strike every adjacent foe. Flip to hit each."},
	"flanking_order": {"n": "Flanking Order", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "icon": "swords", "built": false, "desc": "Leader spell: you and an ally both move and attack one foe."},
	"hold_the_line": {"n": "Hold the Line", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "conc": true, "effect": "hold_line", "icon": "shield", "desc": "Leader spell: allies next to you take less damage while you sustain it."},
	"the_end": {"n": "The End", "src": "klass", "ap": 3, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "CHA", "effect": "the_end", "icon": "bubble", "desc": "Narrator spell: a badly hurt foe is narrated out of the fight (CHA save)."},
	"epic_saga": {"n": "Epic Saga", "src": "klass", "ap": 3, "kind": "self", "limit": "turn", "conc": true, "effect": "saga", "icon": "star", "desc": "Narrator spell: every ally gains a buff while you sustain the tale."},
	"requiem": {"n": "Requiem", "src": "klass", "ap": 3, "kind": "self", "limit": "turn", "save": "CON", "effect": "requiem", "ab": "CHA", "bonus": Rules.REQUIEM_BONUS, "icon": "bolt", "desc": "Musician spell: heavy sonic damage to every foe (CON save)."},
	"song_of_rest": {"n": "Song of Rest", "src": "klass", "ap": 3, "kind": "self", "limit": "turn", "effect": "song_of_rest", "ab": "CHA", "icon": "heart", "desc": "Musician spell: heal all allies."},
	"dance_of_blades": {"n": "Dance of Blades", "src": "klass", "ap": 3, "kind": "self", "limit": "turn", "icon": "swords", "built": false, "desc": "Dancer spell: several strikes on foes you move past."},
	"dance_macabre": {"n": "Dance Macabre", "src": "klass", "ap": 3, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "CHA", "effect": "macabre", "radius": 1, "icon": "sparkle", "desc": "Dancer spell: foes in an area are forced to dance and can't act (CHA save)."},
	"charge": {"n": "Charge!", "src": "klass", "ap": 3, "kind": "self", "limit": "turn", "icon": "move", "built": false, "desc": "Leader spell: every ally moves and attacks."},
	"last_stand": {"n": "Last Stand", "src": "klass", "ap": 3, "kind": "self", "limit": "turn", "effect": "last_stand", "icon": "shield", "desc": "Leader spell: allies can't drop below 1 HP this turn."},
	"bonebreaker": {"n": "Bonebreaker", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "icon": "mace", "rider": "slow", "slow": Rules.BONEBREAKER_SLOW, "desc": "Mace: lower enemy movement."},
	"sacred_flame": {"n": "Sacred Flame", "src": "klass", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "DEX", "ab": "WIS", "icon": "flame", "desc": "Order of Light: radiant damage. The target makes a DEX save."},
	"bless": {"n": "Bless", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": 5, "icon": "star", "effect": "bless", "desc": "Order of Good: an ally flips an extra coin on its next check."},
	"healing_word": {"n": "Healing Word", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": Rules.SPELL_RANGE, "ab": "WIS", "icon": "heart", "effect": "heal", "desc": "Order of Good: heal an ally at range."},
	"throw": {"n": "Throw", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": Weapons.THROW_RANGE, "ranged": true, "icon": "throw", "desc": "Dagger: a ranged attack with the dagger. It returns to your hand."},
	"sneak_attack": {"n": "Sneak Attack", "src": "klass", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "icon": "eye", "effect": "sneak", "desc": "Rogue: a weapon attack with bonus damage if the foe is flanked or unaware."},
	"duck_behind": {"n": "Duck Behind", "src": "race", "ap": 1, "kind": "ally", "limit": "turn", "range": 1, "icon": "M7 7h11l-3-3 M17 17H6l3 3", "effect": "swap", "desc": "Swap places with an adjacent ally."},
	"breath": {"n": "Breath Weapon", "src": "race", "ap": 2, "kind": "breath", "limit": "turn", "save": "DEX", "icon": "M12 3c1 4 5 6 5 11a5 5 0 0 1-10 0c0-3 2-4 2-7 1 2 2 3 3 3 0-3-1-5 0-7z", "desc": "A line of 3 hexes in one of the 6 directions. Everyone in it, allies included, makes a DEX save (half damage on a pass). Damage grows with level."},
	"lockdown": {"n": "Lockdown", "src": "race", "ap": 1, "kind": "self", "limit": "turn", "icon": "M7 11V8a5 5 0 0 1 10 0v3 M5 11h14v9H5z", "effect": "lockdown", "desc": "Your damage reduction doubles until your next turn, but you can’t move."},
	"stone_throw": {"n": "Stone Throw", "src": "race", "ap": 1, "kind": "attack", "limit": "turn", "range": Rules.RACIAL_RANGE, "ranged": true, "ab": "STR", "dmg": Rules.RACIAL_DAMAGE, "icon": "M5 16l3-7 6-2 5 5-2 6-8 1z", "desc": "A ranged STR attack, usable whatever weapon you hold."},
	"claw_swipe": {"n": "Claw Swipe", "src": "race", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "ab": "DEX", "dmg": Rules.CLAW_DAMAGE, "rider": "bleed", "icon": "M6 5l3 14 M11 4l2 15 M17 5l-2 14", "desc": "A melee scratch that makes the foe bleed. DEX attack."},
	"glimmerstep": {"n": "Glimmerstep", "src": "elven", "ap": 1, "kind": "cell", "limit": "turn", "range": Rules.GLIMMERSTEP_RANGE, "icon": "glim", "effect": "blink", "desc": "Vanish and reappear in an empty hex up to 3 hexes away."},
	"faerie_fire": {"n": "Faerie Fire", "src": "elven", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.RACIAL_RANGE, "save": "DEX", "icon": "spark", "effect": "glow", "desc": "The foe glows until your next turn: attacks against it flip 1 extra coin, and it can’t hide. DEX save."},
	"lull": {"n": "Lull", "src": "elven", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.RACIAL_RANGE, "save": "WIS", "icon": "moon", "effect": "lull", "desc": "The foe dozes off and loses its next attack. Any hit wakes it. WIS save."},
	"scorch": {"n": "Scorch", "src": "bloodline", "ap": 1, "kind": "attack", "limit": "turn", "range": Rules.RACIAL_RANGE, "ranged": true, "ab": "CHA", "dmg": Rules.RACIAL_DAMAGE, "icon": "flame", "desc": "A lance of fire at one foe in range. Attack flip to hit."},
	"ember_mend": {"n": "Ember Mend", "src": "bloodline", "ap": 1, "kind": "ally", "limit": "turn", "range": Rules.RACIAL_RANGE, "icon": "heart", "effect": "mend", "desc": "Heal an ally a little, more if they’re below half HP."},
	"guiding_ember": {"n": "Guiding Ember", "src": "bloodline", "ap": 1, "kind": "self", "limit": "turn", "icon": "spark", "effect": "guide", "desc": "A small light drifts out and reveals hidden foes and traps within 3 hexes."},
	# Ranger class cards (03 -> Martial class cards) and the Ranger's weapon cards (04 -> Weapon category cards; text from CreatorData).
	"hunters_mark": {"n": "Hunter's Mark", "src": "klass", "ap": 1, "kind": "mark", "limit": "turn", "icon": "M12 3v4 M12 17v4 M3 12h4 M17 12h4 M12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8", "desc": "Ranger: a marked foe takes extra damage from you for the fight."},
	"snare": {"n": "Snare", "src": "klass", "ap": 1, "kind": "cell", "limit": "turn", "range": Rules.SNARE_RANGE, "effect": "snare", "icon": "M4 18h16 M7 18l5-9 5 9 M12 9V5", "desc": "Ranger: set a hidden trap on a hex; the first foe to step in is rooted."},
	"quick_slash": {"n": "Quick Slash", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "icon": "w_shortsword", "effect": "quick", "desc": "Shortsword: a cheap extra attack."},
	"dancing_step": {"n": "Dancing Step", "src": "weapon", "ap": 0, "kind": "cell", "limit": "turn", "range": Rules.DANCE_HEXES, "effect": "dance", "icon": "w_scimitar", "desc": "Scimitar: right after a scimitar attack, take a free short move."},
	"sweeping_arc": {"n": "Sweeping Arc", "src": "weapon", "ap": 1, "kind": "arc", "limit": "turn", "range": 2, "icon": "w_glaive", "desc": "Glaive: hit enemies in a wide arc."},
	"double_shot": {"n": "Double Shot", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 6, "ranged": true, "shots": 2, "icon": "w_shortbow", "desc": "Shortbow: two quick arrows."},
	"aimed_shot": {"n": "Aimed Shot", "src": "weapon", "ap": 3, "kind": "attack", "limit": "turn", "range": 8, "ranged": true, "times": Rules.AIMED_TIMES, "pierce": true, "icon": "w_longbow", "desc": "Longbow: one huge shot."},
	"pinning_bolt": {"n": "Pinning Bolt", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 6, "ranged": true, "rider": "snare", "icon": "w_crossbow", "desc": "Crossbow: root an enemy."},
	"guard_up": {"n": "Guard Up", "src": "weapon", "ap": 1, "kind": "self", "limit": "turn", "effect": "guard", "icon": "w_gauntlets", "desc": "Gauntlets: take less damage until your next turn and counter the first hit."},
	"haymaker": {"n": "Haymaker", "src": "weapon", "ap": 2, "kind": "attack", "limit": "turn", "range": 1, "times": 2, "rider": "haymaker", "save": "CON", "icon": "w_knuckles", "desc": "Brass knuckles: a big hit that can stun (CON save)."},
	"disarm": {"n": "Disarm", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "rider": "disarm", "icon": "w_rapier", "desc": "Rapier: knock the enemy's weapon away."},
	"step_strike": {"n": "Step and Strike", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "step": Rules.STEP_STRIKE_HEXES, "icon": "w_wraps", "desc": "Wraps: move a short way and strike."},
	"poison_blade": {"n": "Poison Blade", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "icon": "drop", "effect": "poison", "desc": "Rogue: every hit for the rest of this turn poisons."},
	# Levels 2 to 5 (design/06 -> First playable -> Levels, Nov 9, 2026; picks: Progression). Text from the docs: mastery
	# cards 04 -> each weapon's tree, spells 03 -> Wizard spells and Cleric spells, subclass cards 03 -> Martial class cards,
	# forms, beasts and god spells 03. Amounts are PLACEHOLDER (Rules). built = false: not built yet (Progression).
	"sweep": {"n": "Sweep", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "rider": "push", "icon": "bash", "desc": "Longsword: knock a foe back a hex."},
	"overhand_cut": {"n": "Overhand Cut", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "bonus": Rules.OVERHAND_BONUS, "two_handed": true, "icon": "sword", "desc": "Longsword, two-handed: a heavy downward strike with bonus damage."},
	"brace": {"n": "Brace", "src": "weapon", "ap": 1, "kind": "self", "limit": "turn", "icon": "defend", "built": false, "desc": "Spear: strike the first foe that moves into your reach this round."},
	"volley": {"n": "Volley", "src": "weapon", "ap": 1, "kind": "self", "limit": "turn", "icon": "w_shortbow", "built": false, "desc": "Shortbow: arrows rain on a small area."},
	"sidestep": {"n": "Sidestep", "src": "weapon", "ap": 1, "kind": "self", "limit": "turn", "effect": "sidestep", "icon": "w_rapier", "desc": "Rapier: you're harder to hit until your next turn."},
	"rend": {"n": "Rend", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "rider": "rend", "save": "CON", "icon": "w_scimitar", "desc": "Scimitar: a cut that makes the foe bleed each turn (CON save)."},
	"throw_dirt": {"n": "Throw Dirt", "src": "weapon", "ap": 1, "kind": "self", "limit": "turn", "icon": "w_shortsword", "built": false, "desc": "Shortsword: blind a foe (CON save)."},
	"rage": {"n": "Rage", "src": "weapon", "ap": 1, "kind": "self", "limit": "turn", "effect": "rage", "icon": "flame", "desc": "Greataxe: deal more damage but take more damage until your next turn."},
	"wide_chop": {"n": "Wide Chop", "src": "weapon", "ap": 1, "kind": "arc", "limit": "turn", "range": 1, "icon": "w_greataxe", "desc": "Greataxe: hit up to three foes in an arc in front of you."},
	"smite": {"n": "Smite", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "bonus": Rules.SMITE_BONUS, "icon": "star", "desc": "Mace: a radiant strike, bonus vs undead and fiends."},
	"ground_pound": {"n": "Ground Pound", "src": "weapon", "ap": 1, "kind": "self", "limit": "turn", "effect": "pound", "save": "DEX", "icon": "w_warhammer", "desc": "Warhammer: slam the ground; adjacent foes are knocked prone (DEX save)."},
	"vault": {"n": "Vault", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 1, "step": Rules.VAULT_HEXES, "icon": "w_glaive", "desc": "Glaive: leap over an obstacle or foe to a hex up to 3 away, then attack."},
	"heavy_bolt": {"n": "Heavy Bolt", "src": "weapon", "ap": 2, "kind": "attack", "limit": "turn", "range": 6, "ranged": true, "pierce": true, "times": Rules.HEAVY_BOLT_TIMES, "icon": "w_crossbow", "desc": "Crossbow: a bolt that ignores armour and deals heavy damage."},
	"bolas_bolt": {"n": "Bolas Bolt", "src": "weapon", "ap": 1, "kind": "attack", "limit": "turn", "range": 6, "ranged": true, "rider": "prone", "icon": "w_crossbow", "desc": "Crossbow: a weighted bolt that knocks the target prone."},
	"shield_charge": {"n": "Shield Charge", "src": "weapon", "ap": 2, "kind": "attack", "limit": "turn", "range": 1, "step": Rules.CHARGE_HEXES, "rider": "push", "icon": "bash", "desc": "Shield: rush a few hexes and Shield Bash the first foe you reach."},
	"stone_sentinel": {"n": "Stone Sentinel", "src": "klass", "ap": 3, "kind": "cell", "limit": "turn", "range": 1, "effect": "summon", "conc": true, "icon": "shield", "desc": "Summoner spell: a sturdy construct that taunts: nearby foes must attack it."},
	"soul_swap": {"n": "Soul Swap", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": 99, "effect": "swap", "summons_only": true, "icon": "repeat", "desc": "Summoner spell: trade places with any of your summons."},
	"flame_burst": {"n": "Flame Burst", "src": "klass", "ap": 2, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "DEX", "effect": "burst", "radius": 1, "ab": "INT", "icon": "fire", "desc": "Blaster spell: a small explosion hitting a few hexes around the target. Everyone in it makes a DEX save."},
	"chain_spark": {"n": "Chain Spark", "src": "klass", "ap": 2, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "DEX", "effect": "chain", "jumps": 1, "ab": "INT", "icon": "bolt", "desc": "Blaster spell: lightning that jumps to a second foe. Each makes a DEX save."},
	"ice_wall": {"n": "Ice Wall", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "icon": "snow", "built": false, "desc": "Blaster spell: a short wall of ice across a few hexes that blocks movement and line of sight; it can be broken."},
	"mirror_burst": {"n": "Mirror Burst", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "save": "INT", "icon": "sparkle", "built": false, "desc": "Deceiver spell: pop one of your decoys; foes next to it are blinded (INT save)."},
	"whisper": {"n": "Whisper", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "save": "WIS", "icon": "bubble", "built": false, "desc": "Deceiver spell: one foe's next attack hits its ally instead (WIS save)."},
	"blood_ward": {"n": "Blood Ward", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": Rules.SPELL_RANGE, "effect": "blood_ward", "hp": Rules.BLOOD_WARD_HP, "icon": "ward", "desc": "Ritualist spell: pay HP to give an ally a damage-absorbing barrier."},
	"hemorrhage": {"n": "Hemorrhage", "src": "klass", "ap": 2, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "CON", "effect": "bleed", "icon": "drop", "desc": "Ritualist spell: curse a foe so it bleeds each turn (CON save)."},
	"holy_brand": {"n": "Holy Brand", "src": "klass", "ap": 2, "kind": "save", "limit": "turn", "range": 5, "save": "CON", "effect": "brand", "icon": "star", "desc": "Order of Light: mark a foe; it takes radiant damage whenever it's hit (CON save)."},
	"dawn_pulse": {"n": "Dawn Pulse", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "effect": "pulse", "save": "DEX", "icon": "sparkle", "desc": "Order of Light: a radiant burst around you, foes only (DEX save)."},
	"darkness": {"n": "Darkness", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "conc": true, "icon": "M20 14A8 8 0 1 1 10 4a6 6 0 0 0 10 10z", "built": false, "desc": "Order of Night: a zone of magical darkness that affects foes only; allies inside are hidden."},
	"shadow_cloak": {"n": "Shadow Cloak", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "icon": "M20 14A8 8 0 1 1 10 4a6 6 0 0 0 10 10z", "built": false, "desc": "Order of Night: an ally in darkness becomes hidden."},
	"sanctuary": {"n": "Sanctuary", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "save": "WIS", "icon": "shield", "built": false, "desc": "Order of Good: until your next turn, foes must pass a WIS save to attack a chosen ally."},
	"curse_of_frailty": {"n": "Curse of Frailty", "src": "klass", "ap": 2, "kind": "save", "limit": "turn", "range": 5, "save": "CON", "effect": "frailty", "icon": "drop", "desc": "Order of Evil: a foe is easier to hit (CON save)."},
	"life_transfer": {"n": "Life Transfer", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "save": "CON", "icon": "heart", "built": false, "desc": "Order of Evil: drain a foe to heal an ally (CON save)."},
	"bring_it": {"n": "Bring It", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "effect": "bring_it", "icon": "swords", "desc": "Brawler: taunt adjacent foes to attack you; you take less damage from them until your next turn."},
	"divine_smite": {"n": "Divine Smite", "src": "klass", "ap": 2, "kind": "attack", "limit": "turn", "range": 1, "weapon_reach": true, "bonus": Rules.DIVINE_SMITE_BONUS, "icon": "star", "desc": "Holy Defender: a weapon attack with heavy radiant bonus damage."},
	"reposition": {"n": "Reposition", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": Rules.REPOSITION_RANGE, "effect": "swap", "icon": "repeat", "desc": "Tactician: swap places with an ally, or move an adjacent ally 2 hexes."},
	"arcane_shield": {"n": "Arcane Shield", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "effect": "arcane_shield", "icon": "ward", "desc": "Arcane Knight: you take less damage until your next turn."},
	"fake_surrender": {"n": "Fake Surrender", "src": "klass", "ap": 1, "kind": "save", "limit": "turn", "range": 5, "save": "CHA", "effect": "surrender", "icon": "bubble", "desc": "Con Artist: the foe lowers its guard (CHA save); on a fail, it becomes unaware of you."},
	"vanish": {"n": "Vanish", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "effect": "vanish", "icon": "eye", "desc": "Assassin: become hidden."},
	"raise_the_stakes": {"n": "Raise the Stakes", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "effect": "stakes", "icon": "fight_once", "desc": "Gambler: your next attack needs one more heads to hit, but deals much more damage."},
	"mage_hand": {"n": "Mage Hand", "src": "klass", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "STR", "effect": "mage_hand", "icon": "sparkle", "desc": "Arcane Trickster: disarm a foe at range (STR save)."},
	"killing_shot": {"n": "Killing Shot", "src": "klass", "ap": 3, "kind": "attack", "limit": "turn", "range": 1, "weapon_reach": true, "effect": "killing", "times": Rules.KILLING_TIMES, "icon": "eye", "desc": "Hunter: huge damage to a marked foe below half HP."},
	"shift": {"n": "Shift", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "icon": "M12 3c3 4 6 8 6 11a6 6 0 0 1-12 0c0-3 3-7 6-11z", "built": false, "desc": "Shifter: take your werebeast hybrid form for the rest of the fight (1 AP to shift back)."},
	"command_beast": {"n": "Command Beast", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "icon": "star", "built": false, "desc": "Companion: your beast makes its signature move."},
	"infuse": {"n": "Infuse", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "icon": "bolt", "built": false, "desc": "Elementalist: for the rest of the fight your attacks deal the chosen element's damage, with its rider: fire hits harder, ice slows, lightning jumps to a second foe."},
	"fireball": {"n": "Fireball", "src": "klass", "ap": 3, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "DEX", "effect": "burst", "radius": 2, "ab": "INT", "bonus": Rules.FIREBALL_BONUS, "icon": "fire", "desc": "Blaster spell: big area fire damage. Everyone in it makes a DEX save."},
	"blizzard": {"n": "Blizzard", "src": "klass", "ap": 3, "kind": "self", "limit": "turn", "conc": true, "icon": "snow", "built": false, "desc": "Blaster spell: an ice zone that slows everything inside and deals cold damage each turn (CON save)."},
	"chain_lightning": {"n": "Chain Lightning", "src": "klass", "ap": 3, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "DEX", "effect": "chain", "jumps": 3, "weaken": 1, "ab": "INT", "icon": "bolt", "desc": "Blaster spell: a bolt that jumps from foe to foe, weakening with each jump, up to 4 foes."},
	"unbind": {"n": "Unbind", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "effect": "unbind", "save": "DEX", "icon": "sparkle", "desc": "Summoner spell: release your summon in a burst of soul energy that damages foes around it (DEX save)."},
	"animate_armor": {"n": "Animate Armor", "src": "klass", "ap": 3, "kind": "self", "limit": "turn", "conc": true, "icon": "shield", "built": false, "desc": "Summoner spell: a slow, very tough animated suit of armour that absorbs hits aimed at adjacent allies."},
	"soul_jar": {"n": "Soul Jar", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "icon": "potion", "built": false, "desc": "Summoner spell: trap a dying foe's soul; your next summon is stronger."},
	"now_you_see_me": {"n": "Now You See Me", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "icon": "eye", "built": false, "desc": "Deceiver spell: you become hidden and leave a decoy where you stood."},
	"psychic_spike": {"n": "Psychic Spike", "src": "klass", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "INT", "effect": "psychic", "ab": "INT", "icon": "sparkle", "desc": "Deceiver spell: psychic damage, more if the foe is unaware of you (INT save)."},
	"nightmare": {"n": "Nightmare", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "conc": true, "save": "WIS", "icon": "M20 14A8 8 0 1 1 10 4a6 6 0 0 0 10 10z", "built": false, "desc": "Deceiver spell: a foe sees its worst fear and takes psychic damage each turn (WIS save)."},
	"soul_siphon": {"n": "Soul Siphon", "src": "klass", "ap": 2, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "CON", "effect": "siphon", "ab": "INT", "icon": "heart", "desc": "Ritualist spell: drain HP from a foe to heal yourself (CON save)."},
	"blood_bond": {"n": "Blood Bond", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "conc": true, "save": "CON", "icon": "drop", "built": false, "desc": "Ritualist spell: link two foes; when one takes damage, the other takes half as much (CON save)."},
	"life_tap": {"n": "Life Tap", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "effect": "life_tap", "hp": Rules.LIFE_TAP_HP, "icon": "bolt", "desc": "Ritualist spell: gain 2 bonus AP this turn."},
	"burning_halo": {"n": "Burning Halo", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "conc": true, "icon": "flame", "built": false, "desc": "Order of Light: an ally glows; foes that hit them take radiant damage."},
	"sunlit_ground": {"n": "Sunlit Ground", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "conc": true, "icon": "sparkle", "built": false, "desc": "Order of Light: a zone where allies' attacks deal bonus radiant damage."},
	"lance_of_dawn": {"n": "Lance of Dawn", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "save": "DEX", "icon": "star", "built": false, "desc": "Order of Light: a beam through a line of foes, foes only (DEX save)."},
	"terror": {"n": "Terror", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "save": "WIS", "icon": "eye", "built": false, "desc": "Order of Night: a foe flees (WIS save)."},
	"nightmare_shroud": {"n": "Nightmare Shroud", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "icon": "M20 14A8 8 0 1 1 10 4a6 6 0 0 0 10 10z", "built": false, "desc": "Order of Night: an ally wears shadow; foes that attack them may become frightened (WIS save)."},
	"snuff_the_light": {"n": "Snuff the Light", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "save": "CON", "icon": "eye", "built": false, "desc": "Order of Night: blind a foe; blinded foes count as being in darkness (CON save)."},
	"mass_heal": {"n": "Mass Heal", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "effect": "mass_heal", "icon": "heart", "desc": "Order of Good: heal all allies nearby."},
	"miracle_of_plenty": {"n": "Miracle of Plenty", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "effect": "plenty", "icon": "potion", "desc": "Order of Good: every ally regains a little HP and their next consumable is free."},
	"purify": {"n": "Purify", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "effect": "purify", "icon": "sparkle", "desc": "Order of Good: remove every status effect from every ally."},
	"vampiric_aura": {"n": "Vampiric Aura", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "conc": true, "icon": "heart", "built": false, "desc": "Order of Evil: allies near you heal a little when they hit any foe."},
	"siphon_strength": {"n": "Siphon Strength", "src": "klass", "ap": 2, "kind": "save", "limit": "turn", "range": 5, "save": "CON", "effect": "siphon_str", "icon": "drop", "desc": "Order of Evil: a foe loses STR coins for the fight, and an ally gains them (CON save)."},
	"curse_of_ruin": {"n": "Curse of Ruin", "src": "klass", "ap": 2, "kind": "save", "limit": "turn", "range": 5, "save": "CON", "effect": "ruin", "icon": "drop", "desc": "Order of Evil: a foe takes more damage from every source until the end of its next turn (CON save)."},
	"sunspot": {"n": "Sunspot", "src": "klass", "ap": 1, "kind": "cell", "limit": "turn", "range": Rules.SPELL_RANGE, "effect": "zone", "zone": "sun", "conc": true, "icon": "sparkle", "desc": "Aurora: a patch of light; enemies in it are easier to hit."},
	"moonveil": {"n": "Moonveil", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": Rules.SPELL_RANGE, "effect": "veil", "icon": "M20 14A8 8 0 1 1 10 4a6 6 0 0 0 10 10z", "desc": "Selene: an ally is veiled in moonlight; attacks against it flip one fewer coin."},
	"heat_metal": {"n": "Heat Metal", "src": "klass", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "conc": true, "save": "CON", "effect": "heat", "icon": "fire", "desc": "Morin: a foe's metal gear burns, dealing damage each turn (CON save)."},
	"thorn_patch": {"n": "Thorn Patch", "src": "klass", "ap": 1, "kind": "cell", "limit": "turn", "range": Rules.SPELL_RANGE, "effect": "zone", "zone": "thorns", "conc": true, "icon": "t_forest", "desc": "Toyoko: slows foes that cross it."},
	"stone_skin": {"n": "Stone Skin", "src": "klass", "ap": 1, "kind": "ally", "limit": "turn", "range": 5, "effect": "stone_skin", "icon": "shield", "desc": "Adam: an ally takes less damage this turn."},
	"hymn": {"n": "Hymn", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "effect": "hymn", "icon": "star", "desc": "Canto: nearby allies flip an extra coin on their next check."},
	"sleight": {"n": "Sleight", "src": "klass", "ap": 1, "kind": "cell", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "CHA", "effect": "sleight", "icon": "repeat", "desc": "Eve: swap places with an ally or foe (CHA save if a foe)."},
	"toll_the_dead": {"n": "Toll the Dead", "src": "klass", "ap": 1, "kind": "save", "limit": "turn", "range": Rules.SPELL_RANGE, "save": "WIS", "ab": "WIS", "effect": "toll", "icon": "drop", "desc": "Tod: necrotic damage, more if the foe is hurt (WIS save)."},
	"hunt_down": {"n": "Hunt Down", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "save": "STR", "icon": "move", "built": false, "desc": "Werewolf: dash to a foe up to 4 hexes away and knock it prone (STR save)."},
	"thick_hide": {"n": "Thick Hide", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "icon": "shield", "built": false, "desc": "Werebear: take much less damage until your next turn."},
	"shred": {"n": "Shred", "src": "klass", "ap": 1, "kind": "self", "limit": "turn", "icon": "drop", "built": false, "desc": "Werecat: a flurry of scratches that makes the foe bleed heavily."},
	"howl": {"n": "Howl", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "save": "WIS", "icon": "bubble", "built": false, "desc": "Wolf: nearby foes are frightened and flip one fewer coin (WIS save)."},
	"roar": {"n": "Roar", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "icon": "bubble", "built": false, "desc": "Bear: nearby foes must attack the bear on their next turn."},
	"dive": {"n": "Dive", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "icon": "move", "built": false, "desc": "Hawk: a big hit from above that ignores cover."},
	"ambush_strike": {"n": "Ambush", "src": "klass", "ap": 2, "kind": "self", "limit": "turn", "icon": "eye", "built": false, "desc": "Panther: it vanishes, then on your next turn strikes for big damage, counted as from behind."},
}

## The basic attack's icon follows the weapon (Combat v14).
const WEAPON_ICON := {"longsword": "sword", "staff": "staff", "mace": "mace", "dagger": "dagger"}


## A card for whoever holds it: the basic attack's weapon, and Breath Weapon's dragon type (sub: "Blue"), as the creator shows it.
static func get_card(id: String, weapon := "", sub := "") -> Dictionary:
	var c: Dictionary = ALL[id].duplicate()
	c.id = id
	if id == "attack":
		c.icon = WEAPON_ICON.get(weapon, "w_" + weapon if CreatorData.IC.has("w_" + weapon) else "sword")   # the creator's weapon icon otherwise
		c.desc = c.desc % weapon
		if weapon.begins_with("summon_"):   # a summon's own attack (03), not gear
			c.desc = "Basic attack."
		if weapon == "wand":   # a wand's basic attack is Magic Bolt, a basic ranged spell (04)
			c.n = "Magic Bolt"
			c.desc = "Wand: a basic ranged spell."
	if CreatorData.PI.has(c.get("icon", "")) and not Icons.PATHS.has(c.icon):
		c.icon = CreatorData.PI[c.icon]
	elif CreatorData.IC.has(c.get("icon", "")) and not Icons.PATHS.has(c.icon):
		c.icon = CreatorData.IC[c.icon]
	if id == "attack" or ((id == "sneak_attack" or c.get("weapon_reach", false)) and weapon != ""):   # a weapon attack's reach and ranged-ness follow the weapon (04, 03)
		c.range = Weapons.of(weapon).range
		c.ranged = Weapons.ranged(weapon)
	if id == "throw":
		c.desc = "%s: a ranged attack with the %s. It returns to your hand." % [weapon.capitalize(), weapon]
	if id == "breath" and CreatorData.DRI.has(sub):
		c.icon = CreatorData.PI[CreatorData.DRI[sub]]
		c.desc = "%s %s" % [c.desc, CreatorData.ELEM[sub]]
	return c


## Card names whose one word is too wide for a card, and where they break instead (Ethan, Nov 5, 2026: "Glimmer / step").
const NAME_BREAKS := {"Glimmerstep": "Glimmer step", "Bonebreaker": "Bone breaker",
	"Hemorrhage": "Hemor rhage", "Reposition": "Re position", "Nightmare": "Night mare",
	"Cliffhanger": "Cliff hanger", "Whirlwind": "Whirl wind"}   # PLACEHOLDER breaks (Nov 9 and 12, 2026), for Ethan


## A card name as the lines it's drawn in, on a card `width` wide: words, with the over-wide ones broken where NAME_BREAKS says.
static func name_lines(n: String, font: Font, size: int, width: float) -> PackedStringArray:
	if font.get_string_size(n, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x <= width:
		return PackedStringArray([n])
	var out := PackedStringArray()
	for w in n.split(" "):
		if font.get_string_size(w, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x > width and NAME_BREAKS.has(w):
			out.append_array(NAME_BREAKS[w].split(" "))
		else:
			out.append(w)
	return out


static func ap_text(c: Dictionary) -> String:
	return "?" if c.ap < 0 else str(c.ap)
