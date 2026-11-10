class_name Progression
extends RefCounted
## Levels 2 to 5 for the hero and every companion (design/06 -> First playable -> Levels, Ethan, Nov 9, 2026). What each level
## grants (05 -> Levels and milestones; 03 -> Class action cards; 07 -> Level-up):
##   2: martials train one weapon mastery node, the first node of a branch (04 -> Weapon mastery; 05: martials train at 2)
##   3: martials gain their level-3 class card; casters pick 2 more spells from every level-3 spell (any school or order)
##   4: a free feat pick from every level-4 feat the character qualifies for (05 -> General feats), beside the +1 score
##   5: a subclass, then its card and class-card upgrade (martials) or a spell from the new school's or order's tier 1 (casters);
##      a Shifter picks its form, a Companion ranger its beast, a Holy Defender its god (03 -> Half-classes, Shifter forms)
## What a member has picked lives on its party dictionary, so saves keep it: mastery (node ids), feat and feat_pick, subclass,
## form, beast, god, renames (card id -> its upgraded name) and levelled (the highest level whose picks are made).
## built = false: the docs define it but the rule it needs isn't in the prototype yet. It can still be picked; a card shows
## its text and can't be used ("Not built yet"), a passive or upgrade does nothing. Every one is listed in godot/README.md.

const MARTIALS := ["fighter", "rogue", "ranger"]
const CASTERS := ["wizard", "cleric"]
const MASTERY_LEVELS := {"fighter": [2, 6, 7, 9, 11, 13], "rogue": [2, 7, 13], "ranger": [2, 7, 13]}   # DOCS (05, Nov 9, 2026)
const FEAT_LEVELS := [4, 12]                                    # DOCS (05 -> General feats)
const SUBCLASS_LEVEL := 5
const CLASS_CARD_LEVEL := 3
const SPELL_PICKS_3 := 2                                         # DOCS (03): casters pick 2 spells at level 3
## The level-3 class card (03 -> Martial class cards; 06 -> Start, Ethan, Nov 9, 2026: no longer in the starting kit), and
## Chelmsford's Healing Word, which also comes at level 3 now, beside his 2 picks (06 -> Start).
const LEVEL3_CARD := {"fighter": "action_surge", "rogue": "poison_blade", "ranger": "snare"}
const LEVEL3_GRANT := {"Chelmsford": "healing_word"}

## Weapon mastery: the first node of each branch (04 -> each weapon's tree). kind: card (a new card), upgrade (changes a
## card, renaming it), passive. Staves and wands have no tree (04: casters don't train).
const MASTERY := {
	"greatsword": [
		{"id": "heavy_blade", "branch": "Executioner", "n": "Heavy Blade", "kind": "passive", "text": "Greatsword basic attacks deal more damage.", "built": true},
		{"id": "cleave_plus", "branch": "Sweeper", "n": "Cleave+", "kind": "upgrade", "of": "cleave", "text": "Cleave deals more damage for each extra foe it hits.", "built": false}],
	"longsword": [
		{"id": "riposte", "branch": "Duelist", "n": "Riposte", "kind": "upgrade", "of": "parry", "text": "A successful Parry triggers a free counterattack.", "built": true},
		{"id": "sweep", "branch": "Warlord", "n": "Sweep", "kind": "card", "card": "sweep", "built": true},
		{"id": "overhand_cut", "branch": "Blademaster", "n": "Overhand Cut", "kind": "card", "card": "overhand_cut", "built": true}],
	"dagger": [
		{"id": "backstab_plus", "branch": "Shadow", "n": "Backstab+", "kind": "upgrade", "of": "backstab", "text": "Backstab deals more damage.", "built": true},
		{"id": "throw_plus", "branch": "Thrower", "n": "Throw+", "kind": "upgrade", "of": "throw", "text": "Throw has longer range.", "built": true}],
	"spear": [
		{"id": "brace", "branch": "Legionary", "n": "Brace", "kind": "card", "card": "brace", "built": false},
		{"id": "throw_plus", "branch": "Javelineer", "n": "Throw+", "kind": "upgrade", "of": "throw", "text": "Thrown spears deal more damage.", "built": true},
		{"id": "reach_plus", "branch": "Lancer", "n": "Reach+", "kind": "upgrade", "of": "reach", "text": "Two-handed Reach extends to 3 hexes.", "built": true}],
	"longbow": [
		{"id": "high_ground", "branch": "Sniper", "n": "High Ground", "kind": "passive", "text": "Shooting from high ground flips an extra coin.", "built": false},
		{"id": "piercing_shot", "branch": "Deadeye", "n": "Piercing Shot", "kind": "upgrade", "of": "aimed_shot", "text": "Aimed Shot pierces armour.", "built": false}],
	"shortbow": [
		{"id": "volley", "branch": "Volley", "n": "Volley", "kind": "card", "card": "volley", "built": false},
		{"id": "triple_shot", "branch": "Rapid Shot", "n": "Triple Shot", "kind": "upgrade", "of": "double_shot", "text": "Double Shot becomes Triple Shot.", "built": true}],
	"rapier": [
		{"id": "exposing_disarm", "branch": "Fencer", "n": "Exposing Disarm", "kind": "upgrade", "of": "disarm", "text": "Disarm also leaves the foe easier to hit.", "built": true},
		{"id": "sidestep", "branch": "Bladedancer", "n": "Sidestep", "kind": "card", "card": "sidestep", "built": true}],
	"scimitar": [
		{"id": "phantom_step", "branch": "Dervish", "n": "Phantom Step", "kind": "upgrade", "of": "dancing_step", "text": "Dancing Step's move can pass through foes' hexes.", "built": false},
		{"id": "rend", "branch": "Reaver", "n": "Rend", "kind": "card", "card": "rend", "built": true}],
	"shortsword": [
		{"id": "quick_slash_plus", "branch": "Striker", "n": "Quick Slash+", "kind": "upgrade", "of": "quick_slash", "text": "Quick Slash deals more damage.", "built": true},
		{"id": "throw_dirt", "branch": "Gutter Fighter", "n": "Throw Dirt", "kind": "card", "card": "throw_dirt", "built": false}],
	"battleaxe": [
		{"id": "relentless_hack", "branch": "Raider", "n": "Relentless Hack", "kind": "upgrade", "of": "hack", "text": "Hack's bonus stacks with each hit on the same foe.", "built": false},
		{"id": "throw_plus", "branch": "Thrower", "n": "Throw+", "kind": "upgrade", "of": "throw", "text": "Thrown axes deal more damage.", "built": true},
		{"id": "headhunter", "branch": "Headsman", "n": "Headhunter", "kind": "passive", "text": "Two-handed attacks deal bonus damage to wounded foes.", "built": true}],
	"greataxe": [
		{"id": "rage", "branch": "Berserker", "n": "Rage", "kind": "card", "card": "rage", "built": true},
		{"id": "wide_chop", "branch": "Ravager", "n": "Wide Chop", "kind": "card", "card": "wide_chop", "built": true}],
	"mace": [
		{"id": "marrowbreaker", "branch": "Bonecrusher", "n": "Marrowbreaker", "kind": "upgrade", "of": "bonebreaker", "text": "Bonebreaker also lowers the foe's STR for the fight.", "built": true},
		{"id": "smite", "branch": "Templar", "n": "Smite", "kind": "card", "card": "smite", "built": true}],
	"warhammer": [
		{"id": "sunder", "branch": "Siegebreaker", "n": "Sunder", "kind": "upgrade", "of": "shatter", "text": "Shatter also lowers the foe's armour for the fight.", "built": false},
		{"id": "ground_pound", "branch": "Earthshaker", "n": "Ground Pound", "kind": "card", "card": "ground_pound", "built": true}],
	"halberd": [
		{"id": "gaffing_hook", "branch": "Harrier", "n": "Gaffing Hook", "kind": "upgrade", "of": "hook", "text": "A hooked foe is easier to hit this turn.", "built": false},
		{"id": "sentinel", "branch": "Warden", "n": "Sentinel", "kind": "passive", "text": "Foes that enter your reach provoke a free attack.", "built": false}],
	"glaive": [
		{"id": "sweeping_circle", "branch": "Polearm Dancer", "n": "Sweeping Circle", "kind": "upgrade", "of": "sweeping_arc", "text": "Sweeping Arc becomes a full circle around you.", "built": true},
		{"id": "vault", "branch": "Vaulter", "n": "Vault", "kind": "card", "card": "vault", "built": true}],
	"gauntlets": [
		{"id": "grappling_guard", "branch": "Wrestler", "n": "Grappling Guard", "kind": "upgrade", "of": "guard_up", "text": "Guard Up's counter also grabs the attacker, so it can't move away (STR save to break free).", "built": false},
		{"id": "guard_up_plus", "branch": "Boxer", "n": "Guard Up+", "kind": "upgrade", "of": "guard_up", "text": "Guard Up also counters when an attack misses you, not just when it hits.", "built": true}],
	"knuckles": [
		{"id": "haymaker_stun", "branch": "Bruiser", "n": "Haymaker+", "kind": "upgrade", "of": "haymaker", "text": "Haymaker's stun save is harder.", "built": true},
		{"id": "haymaker_damage", "branch": "Slugger", "n": "Haymaker+", "kind": "upgrade", "of": "haymaker", "text": "Haymaker deals extra damage.", "built": true}],
	"wraps": [
		{"id": "flowing_strike", "branch": "Karateka", "n": "Flowing Strike", "kind": "upgrade", "of": "step_strike", "text": "When Step and Strike hits, your next wraps card this turn costs 1 less AP.", "built": true},
		{"id": "step_strike_plus", "branch": "Taekwondoin", "n": "Step and Strike+", "kind": "upgrade", "of": "step_strike", "text": "Step and Strike moves twice as far.", "built": true}],
	"crossbow": [
		{"id": "heavy_bolt", "branch": "Arbalist", "n": "Heavy Bolt", "kind": "card", "card": "heavy_bolt", "built": true},
		{"id": "bolas_bolt", "branch": "Trapper", "n": "Bolas Bolt", "kind": "card", "card": "bolas_bolt", "built": true}],
	"shield": [
		{"id": "steady_block", "branch": "Guardian", "n": "Steady Block", "kind": "upgrade", "of": "block", "text": "While Blocking you can't be pushed, pulled or knocked prone.", "built": false},
		{"id": "shield_charge", "branch": "Basher", "n": "Shield Charge", "kind": "card", "card": "shield_charge", "built": true}],
}
## Versatile weapons' third branch works only two-handed (04 -> Mastery tree framework).
const TWO_HANDED_BRANCHES := ["Blademaster", "Lancer", "Headsman"]

## Level-3 spells by school and order (03 -> Wizard spells; Cleric spells). Clerics pick from every order before level 5.
const WIZARD_3 := {"Summoner": ["stone_sentinel", "soul_swap"], "Blaster": ["flame_burst", "chain_spark", "ice_wall"],
	"Deceiver": ["mirror_burst", "whisper"], "Ritualist": ["blood_ward", "hemorrhage"]}
const CLERIC_3 := {"Order of Light": ["holy_brand", "dawn_pulse"], "Order of Night": ["darkness", "shadow_cloak"],
	"Order of Good": ["healing_word", "sanctuary"], "Order of Evil": ["curse_of_frailty", "life_transfer"]}
## Tier 1 (level 5+), the level-5 pick from the new school or order (03 -> Library spell picks; Cleric orders).
const WIZARD_T1 := {"Summoner": ["unbind", "animate_armor", "soul_jar"], "Blaster": ["fireball", "blizzard", "chain_lightning"],
	"Deceiver": ["now_you_see_me", "psychic_spike", "nightmare"], "Ritualist": ["soul_siphon", "blood_bond", "life_tap"]}
const CLERIC_T1 := {"Order of Light": ["burning_halo", "sunlit_ground", "lance_of_dawn"], "Order of Night": ["terror", "nightmare_shroud", "snuff_the_light"],
	"Order of Good": ["mass_heal", "miracle_of_plenty", "purify"], "Order of Evil": ["vampiric_aura", "siphon_strength", "curse_of_ruin"]}
## Level-1 spells the cleric orders give, so a cleric's level-3 list leaves out what it has (03).
const SCHOOL_ICON := {"Summoner": "M12 4a8 8 0 1 0 0 16 8 8 0 1 0 0-16 M12 8a4 4 0 0 1 4 4",
	"Blaster": "M12 2l1.8 4.6L18.5 4l-1.6 4.9 5 .9-4.2 2.7 3.4 3.7-5-.4.4 5L12.9 18 12 23l-.9-5-3.6 2.8.4-5-5 .4 3.4-3.7-4.2-2.7 5-.9L5.5 4l4.7 2.6z M12.7 8.6l-2.4 3.7h3.4l-2.4 3.7",
	"Deceiver": "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z M12 9a3 3 0 1 0 0 6a3 3 0 1 0 0-6",
	"Ritualist": "M12 3c3 4 6 8 6 11a6 6 0 0 1-12 0c0-3 3-7 6-11z",
	"Order of Light": "M12 4a8 8 0 1 0 0 16 8 8 0 1 0 0-16 M12 1v2 M12 21v2 M1 12h2 M21 12h2",   # PLACEHOLDER icons (07: subclass icons open)
	"Order of Night": "M20 14A8 8 0 1 1 10 4a6 6 0 0 0 10 10z",
	"Order of Good": "M12 21s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 11c0 5.5-7 10-7 10z",
	"Order of Evil": "M12 3l2.5 6H21l-5.2 4 2 6.5L12 15.6 6.2 19.5l2-6.5L3 9h6.5z"}

## Subclasses (03 -> Subclasses; blurbs: 03 -> Subclass blurbs). Martials: the level-5 card and the class-card upgrade
## (03 -> Martial class cards): of = the card it upgrades, n = its new name. Casters: their school or order.
const SUBCLASSES := {
	"fighter": {
		"Brawler": {"blurb": "A mighty warrior who won't go down without a fight.", "card": "bring_it", "of": "second_wind", "n": "Second Wind+", "text": "Second Wind can be used twice per fight.", "up_built": true},
		"Holy Defender": {"blurb": "A righteous champion who smites foes and heals friends.", "card": "divine_smite", "of": "second_wind", "n": "Blessed Wind", "text": "Second Wind also heals adjacent allies.", "up_built": true, "follow": "god"},
		"Tactician": {"blurb": "A watchful master of war who manipulates the battlefield.", "card": "reposition", "of": "action_surge", "n": "Battle Surge", "text": "Action Surge also gives every ally +1 bonus AP.", "up_built": true},
		"Arcane Knight": {"blurb": "A master of spell and blade, fusing the two arts into one.", "card": "arcane_shield", "of": "second_wind", "n": "Second Ward", "text": "Second Wind also grants a ward (a damage-absorbing barrier).", "up_built": true}},
	"rogue": {
		"Con Artist": {"blurb": "A silver-tongued swindler who talks foes into dropping their guard.", "card": "fake_surrender", "of": "poison_blade", "n": "Sleeping Draught", "text": "Hits this turn make foes drowsy: they flip one fewer coin.", "up_built": true},
		"Assassin": {"blurb": "A patient killer who strikes from the shadows, then vanishes.", "card": "vanish", "of": "poison_blade", "n": "Poison Blade+", "text": "Poison Blade's poison is deadlier.", "up_built": true},
		"Gambler": {"blurb": "A reckless risk-taker who bets everything on the flip of a coin.", "card": "raise_the_stakes", "of": "poison_blade", "n": "Wild Card", "text": "Every hit for the rest of this turn applies a random status (poison, bleed, slow or blind).", "up_built": true},
		"Arcane Trickster": {"blurb": "A sly thief who uses magic to gain the advantage.", "card": "mage_hand", "of": "poison_blade", "n": "Magical Blade", "text": "Poison Blade's hits this turn deal magic damage instead of poison.", "up_built": false}},
	"ranger": {
		"Hunter": {"blurb": "A relentless tracker who always brings down the biggest prey.", "card": "killing_shot", "of": "hunters_mark", "n": "Trophy Mark", "text": "Hunter's Mark's extra damage grows against large foes.", "up_built": true},
		"Shifter": {"blurb": "A wild warrior who unleashes the beast within.", "card": "shift", "of": "snare", "n": "Pounce", "text": "When your Snare springs, you may leap to the trapped foe for free.", "up_built": false, "follow": "form"},
		"Companion": {"blurb": "A loyal beast-friend who fights side by side with an animal ally.", "card": "command_beast", "of": "hunters_mark", "n": "Pack Mark", "text": "Hunter's Mark also boosts your beast's damage.", "up_built": false, "follow": "beast"},
		"Elementalist": {"blurb": "A nature-touched warrior whose every strike carries the elements.", "card": "infuse", "of": "snare", "n": "Primal Snare", "text": "Snare takes an element chosen when it's set: fire burns the trapped foe, ice also slows nearby foes, lightning jumps to a second foe.", "up_built": false}},
	"wizard": {
		"Summoner": {"blurb": "A binder of souls who calls spirits and steel to fight beside them."},
		"Blaster": {"blurb": "A volatile spellcaster who unleashes fire, ice and lightning."},
		"Deceiver": {"blurb": "A cunning illusionist who turns the enemy's own eyes against them."},
		"Ritualist": {"blurb": "A dark scholar who pays for power in their own blood."}},
	"cleric": {
		"Order of Light": {"blurb": "A radiant battle-priest who burns and blinds the wicked."},
		"Order of Night": {"blurb": "A shadowed mystic who hides allies in darkness and sows fear."},
		"Order of Good": {"blurb": "A humble miracle-worker whose prayers can turn the tide."},
		"Order of Evil": {"blurb": "A grim hexer who curses foes and drains their life away."}},
}
## Story companions' default subclass (01 -> Companions: Fluffy Blaster, Mel Con Artist, Chelmsford Order of Good), which the
## player can change at level 5 (01); the bots keep it.
const DEFAULT_SUBCLASS := {"Fluffy": "Blaster", "Mel": "Con Artist", "Chelmsford": "Order of Good"}
const COMPANION_GOD := {"Chelmsford": "Aurora"}   # DOCS (01: an Order of Good cleric of Aurora)

## The Shifter's forms (03 -> Shifter forms), the Companion ranger's beasts (03 -> Companion ranger's beast) and the gods
## (03 -> God spells) with the follow-up's card. Forms and beasts need their own rules (built = false).
const FORMS := {
	"Werewolf": {"feel": "Fast", "card": "hunt_down"},
	"Werebear": {"feel": "Tough", "card": "thick_hide"},
	"Werecat": {"feel": "Burst", "card": "shred"}}
const BEASTS := {
	"Wolf": {"text": "Fast, knocks foes down.", "card": "howl"},
	"Bear": {"text": "Sturdy, draws attacks.", "card": "roar"},
	"Hawk": {"text": "Flies, attacks at range, spots hidden foes.", "card": "dive"},
	"Panther": {"text": "Stealthy, bonus damage from behind.", "card": "ambush_strike"}}
const GODS := {"Aurora": "sunspot", "Selene": "moonveil", "Morin": "heat_metal", "Toyoko": "thorn_patch", "Adam": "stone_skin",
	"Canto": "hymn", "Eve": "sleight", "Tod": "toll_the_dead"}
const GOD_OF := {"Aurora": "sun", "Selene": "moon", "Morin": "forge", "Toyoko": "bounty and harvests", "Adam": "earth",
	"Canto": "music", "Eve": "trickery", "Tod": "death"}

## Level-4 feats (05 -> General feats). need: score [ability, at least], race (race id, or "Golem/Wood"), background.
## follow: a second pick in the details panel (07 -> Feat step): Skilled a proficiency, Weapon Training a weapon category.
const FEATS := [
	{"id": "tough", "n": "Tough", "group": "General", "text": "More max HP", "need": {"score": ["CON", 2]}, "built": true},
	{"id": "opening_strike", "n": "Opening Strike", "group": "General", "text": "Your first attack each fight flips +1 coin", "need": {}, "built": true},
	{"id": "speedy", "n": "Speedy", "group": "General", "text": "Move covers +1 hex", "need": {"score": ["DEX", 2]}, "built": true},
	{"id": "weapon_training", "n": "Weapon Training", "group": "General", "text": "Use one weapon category outside your class's list (no mastery for it)", "need": {}, "built": false, "follow": "weapon"},
	{"id": "heavy_hitter", "n": "Heavy Hitter", "group": "General", "text": "STR weapon basic attacks deal a little more damage", "need": {"score": ["STR", 2]}, "built": true},
	{"id": "keen_eye", "n": "Keen Eye", "group": "General", "text": "+1 sight range", "need": {"score": ["WIS", 2]}, "built": true},
	{"id": "forager", "n": "Forager", "group": "General", "text": "Resting can yield a healing consumable", "need": {}, "built": false},
	{"id": "surveyor", "n": "Surveyor", "group": "General", "text": "Peek at the top card of your map deck", "need": {"score": ["INT", 2]}, "built": false},
	{"id": "skilled", "n": "Skilled", "group": "General", "text": "Learn any one proficiency, or raise one a rank", "need": {}, "built": true, "follow": "proficiency"},
	{"id": "silver_tongue", "n": "Silver Tongue", "group": "General", "text": "Once per dialogue, reflip a failed social check", "need": {"score": ["CHA", 2]}, "built": false},
	{"id": "rallying_presence", "n": "Rallying Presence", "group": "General", "text": "Allies start each fight with a little temporary HP", "need": {"score": ["CHA", 2]}, "built": true},
	{"id": "quick_study", "n": "Quick Study", "group": "Race", "text": "Class location visits teach 2 skills instead of 1", "need": {"race": "Human"}, "built": false},
	{"id": "light_step", "n": "Light Step", "group": "Race", "text": "+1 coin on Stealth checks", "need": {"race": "Elf"}, "built": true},
	{"id": "unmovable", "n": "Unmovable", "group": "Race", "text": "Can't be pushed or pulled", "need": {"race": "Dwarf"}, "built": false},
	{"id": "born_lucky", "n": "Born Lucky", "group": "Race", "text": "Lucky gets +1 reflip per rest", "need": {"race": "Halfling"}, "built": true},
	{"id": "deep_breath", "n": "Deep Breath", "group": "Race", "text": "Breath weapon reaches 1 hex farther", "need": {"race": "Dragonborn"}, "built": true},
	{"id": "unsettling", "n": "Unsettling", "group": "Race", "text": "+1 coin on Intimidate checks", "need": {"race": "Tiefling"}, "built": false},
	{"id": "forest_rest", "n": "Forest Rest", "group": "Race", "text": "Rest on any forest tile without a camp kit by rooting into the ground, once per day cycle", "need": {"race": "Golem/Wood"}, "built": false},
	{"id": "drilled", "n": "Drilled", "group": "Background", "text": "Defend/brace also protects one adjacent ally", "need": {"background": "soldier"}, "built": true},
	{"id": "devout", "n": "Devout", "group": "Background", "text": "Meditation Rock's blessing lasts 2 fights instead of 1", "need": {"background": "acolyte"}, "built": false},
	{"id": "fence", "n": "Fence", "group": "Background", "text": "Sell loot for more gold", "need": {"background": "criminal"}, "built": false},
	{"id": "tower_ties", "n": "Tower Ties", "group": "Background", "text": "Wizard towers swap 2 cards per visit instead of 1", "need": {"background": "sage"}, "built": false},
	{"id": "local_hero", "n": "Local Hero", "group": "Background", "text": "Quest boards in villages and inns show 1 extra quest", "need": {"background": "folk_hero"}, "built": false},
	{"id": "merchant_ties", "n": "Merchant Ties", "group": "Background", "text": "Traveling merchants stay twice as long", "need": {"background": "noble"}, "built": false},
]
const BACKGROUND_NAMES := {"soldier": "Soldier", "acolyte": "Acolyte", "criminal": "Criminal", "sage": "Sage", "folk_hero": "Folk Hero", "noble": "Noble"}
const PROFICIENCY_LIST := ["Athletics", "Perception", "Intimidate", "Survival", "Stealth", "Thievery", "Deceive", "Persuade", "Lore", "Nature", "Animal"]
## Every weapon category (Gear.WEAPONS' ids), for Weapon Training's follow-up.
const ALL_WEAPONS := ["greatsword", "longsword", "shortsword", "rapier", "scimitar", "dagger", "battleaxe", "greataxe", "mace", "warhammer",
	"spear", "halberd", "glaive", "staff", "wand", "shortbow", "longbow", "crossbow", "gauntlets", "knuckles", "wraps"]


# --- Who a member is ---------------------------------------------------------------------

static func klass(m: Dictionary) -> String:
	var k: String = m.get("klass", "")
	return k if k != "" else Rules.COMPANION_CLASS.get(m.get("name", ""), "fighter")


static func martial(m: Dictionary) -> bool:
	return klass(m) in MARTIALS


static func has_mastery(m: Dictionary, cat: String, id: String) -> bool:
	return "%s.%s" % [cat, id] in m.get("mastery", [])


## A member's passive or upgrade on the weapon it's using now: the main weapon (or the shield in the off hand).
static func trained(m: Dictionary, id: String) -> bool:
	for n: String in m.get("mastery", []):
		var cat := n.get_slice(".", 0)
		if n.get_slice(".", 1) == id and cat in [m.get("weapon", ""), m.get("off", "")]:
			return true
	return false


static func feat(m: Dictionary) -> String:
	return m.get("feat", "")


static func sub(m: Dictionary) -> String:
	return m.get("subclass", "")


## The upgraded class card (Second Wind+ and the rest), when it's built.
static func upgraded(m: Dictionary, card_id: String) -> String:
	if sub(m) == "":
		return ""
	var s: Dictionary = SUBCLASSES.get(klass(m), {}).get(sub(m), {})
	return s.n if s.get("of", "") == card_id and s.get("up_built", false) else ""


# --- What a level asks of a member ---------------------------------------------------------

## The sections a member makes at this level, in order (07 -> Level-up: one character at a time).
static func sections(m: Dictionary, level: int, background := "") -> Array:
	var out := []
	var k := klass(m)
	if level in MASTERY_LEVELS.get(k, []) and level <= SUBCLASS_LEVEL and not mastery_options(m).is_empty():
		out.append("mastery")
	if level == CLASS_CARD_LEVEL:
		if k in MARTIALS:
			out.append("class_cards")
		elif k in CASTERS:
			out.append("spells")
	if level in FEAT_LEVELS:
		out.append("feat")
	if level == SUBCLASS_LEVEL and SUBCLASSES.has(k):
		out.append("subclass")
	return out


## The mastery nodes a member can train: the first node of each branch, for every weapon category it holds (main hand,
## off hand), not trained yet. Only Fighters mix branches (04), which needs more than one node per weapon.
static func mastery_options(m: Dictionary) -> Array:
	var out := []
	for cat: String in [m.get("weapon", ""), m.get("off", "")]:
		if not MASTERY.has(cat):
			continue
		var started: bool = m.get("mastery", []).any(func(n): return n.begins_with(cat + "."))
		if started and klass(m) != "fighter":
			continue
		for node: Dictionary in MASTERY[cat]:
			if not has_mastery(m, cat, node.id):
				out.append({"cat": cat, "node": node})
	return out


## The level-3 spells a caster can pick: every school's or order's, less those it has.
static func spell_groups_3(m: Dictionary) -> Dictionary:
	var src: Dictionary = WIZARD_3 if klass(m) == "wizard" else CLERIC_3
	var out := {}
	for g: String in src:
		out[g] = src[g].filter(func(id): return not id in m.get("cards", []) and id != LEVEL3_GRANT.get(m.get("name", ""), ""))
	return out


## The level-5 spell pick: the new school's or order's tier 1.
static func tier1(m: Dictionary) -> Array:
	var src: Dictionary = WIZARD_T1 if klass(m) == "wizard" else CLERIC_T1
	return src.get(sub(m), []).filter(func(id): return not id in m.get("cards", []))


static func feat_of(id: String) -> Dictionary:
	for f: Dictionary in FEATS:
		if f.id == id:
			return f
	return {}


## The requirement a member is missing for a feat, or "" if it qualifies (05: level, a score, race or background; never class).
static func missing(m: Dictionary, f: Dictionary, background := "") -> String:
	var need: Dictionary = f.need
	if need.has("score") and Races.score(m, need.score[0]) < int(need.score[1]):
		return "%s %d+" % need.score
	if need.has("race"):
		var r: String = need.race
		var ok: bool = m.get("race", "") == r if not r.contains("/") else (m.get("race", "") == r.get_slice("/", 0) and m.get("sub", "") == r.get_slice("/", 1))
		if not ok:
			return r.replace("Golem/Wood", "Wood golem")
	if need.has("background") and m.get("background", background) != need.background:
		return BACKGROUND_NAMES.get(need.background, need.background)
	return ""


## The requirement as its chip says it: "CON 2+", "Human", "Soldier", or "".
static func need_text(f: Dictionary) -> String:
	var need: Dictionary = f.need
	if need.has("score"):
		return "%s %d+" % need.score
	if need.has("race"):
		return String(need.race).replace("Golem/Wood", "Wood golem")
	if need.has("background"):
		return BACKGROUND_NAMES.get(need.background, "")
	return ""


## The follow-up choices a feat has for this member: proficiencies for Skilled, weapon categories outside the class's list
## for Weapon Training (none for a Human or a Fighter, who use every weapon: 05).
static func follow_options(m: Dictionary, f: Dictionary) -> Array:
	match f.get("follow", ""):
		"proficiency":
			return PROFICIENCY_LIST.duplicate()
		"weapon":
			if m.get("race", "") == "Human" or klass(m) == "fighter":
				return []
			var own: Array = Gear.weapons_for(klass(m)).map(func(w): return w.id)
			return ALL_WEAPONS.filter(func(w): return not w in own)
	return []


# --- Applying a pick ------------------------------------------------------------------------

## Adds a card the member gains; it goes on the hotbar if a slot is free, else into All actions (07 -> Combat screen).
static func gain_card(m: Dictionary, id: String) -> void:
	if id == "" or not Cards.ALL.has(id) or id in m.cards:
		return
	m.cards.append(id)
	if m.has("hot") and m.hot.size() < Rules.HOTBAR_SLOTS:
		m.hot.append(id)


static func apply_mastery(m: Dictionary, cat: String, node: Dictionary) -> void:
	if not m.has("mastery"):
		m.mastery = []
	m.mastery.append("%s.%s" % [cat, node.id])
	if node.kind == "card":
		gain_card(m, node.card)
	elif node.kind == "upgrade" and node.get("built", false) and Cards.ALL.has(node.of):
		if not m.has("renames"):
			m.renames = {}
		m.renames[node.of] = node.n if not m.renames.has(node.of) else m.renames[node.of] + "+"   # later upgrades add a "+" (04)


static func apply_level3(m: Dictionary, spells: Array) -> void:
	if martial(m):
		gain_card(m, LEVEL3_CARD.get(klass(m), ""))
	gain_card(m, LEVEL3_GRANT.get(m.get("name", ""), ""))
	for id: String in spells:
		gain_card(m, id)


static func apply_feat(m: Dictionary, id: String, follow := "") -> void:
	m.feat = id
	m.feat_pick = follow
	match id:
		"skilled":
			if follow != "" and not follow in m.get("proficiencies", []):
				if not m.has("proficiencies"):
					m.proficiencies = []
				m.proficiencies.append(follow)
		"born_lucky":
			m.lucky = int(m.get("lucky", 0)) + 1


## The subclass and what comes with it: a martial's card and upgrade, the follow-up's card (form, beast, god), a caster's
## tier-1 spell.
static func apply_subclass(m: Dictionary, name: String, follow := "", spell := "") -> void:
	m.subclass = name
	var s: Dictionary = SUBCLASSES[klass(m)][name]
	if s.has("card"):
		gain_card(m, s.card)
		if s.get("up_built", false):
			if not m.has("renames"):
				m.renames = {}
			m.renames[s.of] = s.n
	match s.get("follow", ""):
		"form":
			m.form = follow
		"beast":
			m.beast = follow
		"god":
			m.god = follow
			gain_card(m, GODS.get(follow, ""))   # the early god spell is free (03 -> God spells)
	gain_card(m, spell)


## A member's picks made the way the bots make them, for a level it skipped (joining late; the test button's companions
## in a bot run): the first option of each, a companion's default subclass. Returns nothing; the member's dict changes.
static func auto_level(m: Dictionary, level: int, background := "") -> void:
	for s: String in sections(m, level, background):
		match s:
			"mastery":
				var o: Dictionary = bot_mastery(m)
				apply_mastery(m, o.cat, o.node)
			"class_cards", "spells":
				apply_level3(m, bot_spells(m))
			"feat":
				var f := bot_feat(m, background)
				apply_feat(m, f, bot_follow(m, feat_of(f)))
			"subclass":
				var name := bot_subclass(m)
				apply_subclass(m, name, bot_follow_sub(m, name), bot_tier1(m, name))
	m.levelled = maxi(int(m.get("levelled", 1)), level)


## Every level from the member's last up to `level`, picked as the bots pick.
static func catch_up(m: Dictionary, level: int, background := "") -> void:
	for l in range(int(m.get("levelled", 1)) + 1, level + 1):
		auto_level(m, l, background)


# --- The bots' picks (the play checks): built options first ------------------------------------

static func bot_mastery(m: Dictionary) -> Dictionary:
	var opts := mastery_options(m)
	var built := opts.filter(func(o): return o.node.built and (not o.node.branch in TWO_HANDED_BRANCHES or m.get("off", "") in ["", "none"]))
	return built[0] if not built.is_empty() else opts[0]


static func bot_spells(m: Dictionary) -> Array:
	if not klass(m) in CASTERS:
		return []
	var all := []
	for g: String in spell_groups_3(m):
		all.append_array(spell_groups_3(m)[g])
	all.sort_custom(func(a, b): return int(Cards.ALL[a].get("built", true)) > int(Cards.ALL[b].get("built", true)))
	return all.slice(0, SPELL_PICKS_3)


static func bot_feat(m: Dictionary, background := "") -> String:
	var ok := FEATS.filter(func(f): return missing(m, f, background) == "" and f.built and (not f.has("follow") or not follow_options(m, f).is_empty()))
	return ok[0].id if not ok.is_empty() else "opening_strike"


static func bot_follow(m: Dictionary, f: Dictionary) -> String:
	var opts := follow_options(m, f).filter(func(p): return not p in m.get("proficiencies", []))
	return opts[0] if not opts.is_empty() else ""


static func bot_subclass(m: Dictionary) -> String:
	if DEFAULT_SUBCLASS.has(m.get("name", "")):
		return DEFAULT_SUBCLASS[m.name]
	var names: Array = SUBCLASSES[klass(m)].keys()
	var built := names.filter(func(n): return SUBCLASSES[klass(m)][n].get("up_built", true) and Cards.ALL.get(SUBCLASSES[klass(m)][n].get("card", ""), {}).get("built", true))
	return built[0] if not built.is_empty() else names[0]


static func bot_follow_sub(m: Dictionary, name: String) -> String:
	match SUBCLASSES[klass(m)][name].get("follow", ""):
		"form":
			return FORMS.keys()[0]
		"beast":
			return BEASTS.keys()[0]
		"god":
			return COMPANION_GOD.get(m.get("name", ""), "Adam")   # Adam's Stone Skin is built
	return ""


static func bot_tier1(m: Dictionary, name: String) -> String:
	if not klass(m) in CASTERS:
		return ""
	var src: Dictionary = WIZARD_T1 if klass(m) == "wizard" else CLERIC_T1
	var opts: Array = src.get(name, []).filter(func(id): return not id in m.get("cards", []))
	opts.sort_custom(func(a, b): return int(Cards.ALL[a].get("built", true)) > int(Cards.ALL[b].get("built", true)))
	return opts[0] if not opts.is_empty() else ""


# --- Effects the rest of the game reads -----------------------------------------------------------

## Extra max HP from feats (Tough: PLACEHOLDER, Rules.TOUGH_HP a level).
static func extra_hp(m: Dictionary, level: int) -> int:
	return Rules.TOUGH_HP * level if feat(m) == "tough" else 0


## Extra hexes per Move (Speedy).
static func move_bonus(m: Dictionary) -> int:
	return Rules.SPEEDY_HEXES if feat(m) == "speedy" else 0


## Extra sight for the party (Keen Eye on anyone in it: PLACEHOLDER, 05 doesn't say whose sight a companion's feat widens).
static func sight_bonus(party: Array) -> int:
	return Rules.KEEN_EYE if party.any(func(m): return feat(m) == "keen_eye") else 0


## A card as its holder has it: an upgrade's name, and its numbers (Throw+ range, Triple Shot, Step and Strike+).
static func card_for(m: Dictionary, c: Dictionary) -> Dictionary:
	if m.is_empty():
		return c
	var id: String = c.get("id", "")
	var rn: Dictionary = m.get("renames", {})
	if rn.has(id):
		c.n = rn[id]
	match id:
		"throw":
			if trained(m, "throw_plus") and m.get("weapon", "") == "dagger":
				c.range += Rules.THROW_PLUS_RANGE
		"double_shot":
			if trained(m, "triple_shot"):
				c.shots = 3
		"step_strike":
			if trained(m, "step_strike_plus"):
				c.step *= 2
		"second_wind":
			if sub(m) == "Brawler":
				c.uses = 2
		"attack":
			if trained(m, "reach_plus") and m.get("weapon", "") == "spear" and m.get("off", "") in ["", "none"]:
				c.range = 3
		"poison_blade":
			var s := sub(m)
			if s in ["Con Artist", "Gambler"]:
				c.desc = "Rogue: " + SUBCLASSES.rogue[s].text
	return c
