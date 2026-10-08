// Pokebox — the story script (generated from tools/story_text.py). lines: said when a step starts / when you talk / before a battle;
// after: said once the step is done, so every mission hands over to the next one.
export const SCRIPT = {
 "Arrive in Lumen Harbor": {
  "lines": [
   [
    "rho",
    "Hey! HEY! Over here! You must be the new Lattice Ranger — the ferry's three hours late, I was about to send a search Echo."
   ],
   [
    "rho",
    "I'm Rho. Relay courier, tour guide, part-time panic. I carry data cards between the towns — or I did, until the cards started walking out of my bag."
   ],
   [
    "you",
    "…walking out?"
   ],
   [
    "rho",
    "Yeah. That's why you're here. Dr. Vale will explain it better than me. Big building, satellite dish, can't miss it. Follow the gold beacon!"
   ]
  ]
 },
 "Meet Dr. Vale at Pokébox Labs": {
  "lines": [
   [
    "vale",
    "Welcome to Veyra, Ranger. I am Ione Vale. I run Pokébox Labs — and, I am afraid, I am the reason you were called here."
   ],
   [
    "vale",
    "Every Pokémon ever stored in a PC passed through Relay Node 7. And every one of them left a trace behind. An Echo."
   ],
   [
    "vale",
    "For thirty years those traces slept. Then, this spring, they woke. They gather in the grass, in the fog, in the storms — always where the land matches their type."
   ],
   [
    "vale",
    "My Lab learned to bind an Echo to blank crystal stock: a Lattice card. Bound, it can walk beside you and battle for you. Unbound… we do not know what it becomes."
   ],
   [
    "vale",
    "Every Ranger starts with one partner. I have three cards ready. Each one already chose its element. Now you choose them."
   ]
  ]
 },
 "Catch your first wild Echo in the tall grass north of town": {
  "lines": [
   [
    "vale",
    "Your partner is bound. Now see the other side of the job: the wild ones."
   ],
   [
    "vale",
    "Echoes gather in the tall grass north of town. Walk in slowly. When one challenges you, weaken it — then throw a Poké Ball and bind it to a blank card."
   ],
   [
    "rho",
    "And if it runs away, don't feel bad. Mine ran away nine times. In a row. Different Echoes."
   ]
  ],
  "after": [
   [
    "vale",
    "Your first capture. Feel that warmth on the card? That is a memory, settling in. Treat it kindly."
   ],
   [
    "rho",
    "Okay, okay, that was cool. But now I have to know how cool. Meet me at the north gate!"
   ]
  ]
 },
 "Rho wants a battle — meet him at the north gate": {
  "lines": [
   [
    "rho",
    "Here's the thing. Every Ranger needs a rival, and I've decided it's me."
   ],
   [
    "rho",
    "You caught one already? Let's see if it can take a hit. Rival battle — first of many!"
   ]
  ],
  "after": [
   [
    "rho",
    "Ow. Okay. Okay! That's one for you. I'm keeping score, by the way. Forever."
   ]
  ]
 },
 "Rest your team at the Lumen Harbor Relay Center": {
  "lines": [
   [
    "rho",
    "Rule one of being a Ranger: the Relay Center. Walk in, talk to the nurse, and your team is rested and your journey saved."
   ],
   [
    "rho",
    "Black out in the wild and you wake up at the last Relay Center you rested in. Trust me. I know. Ask me about the swamp sometime. Actually don't."
   ]
  ]
 },
 "Find Captain Maren on the docks": {
  "lines": [
   [
    "maren",
    "So you're Vale's new Ranger. Hm. Narrow shoulders. Good eyes, though."
   ],
   [
    "maren",
    "I'm Maren, Warden of the Tide Trial. Thirty years I've sailed these waters, and last week the sea glowed under my keel. Echoes, swimming in schools like fish."
   ],
   [
    "maren",
    "My Trial is simple. Beat my two dockhands. Bind a Water Echo from the west beach. Then face me — and the tide."
   ]
  ]
 },
 "Beat Dockhand Pim": {
  "lines": [
   [
    "deckA",
    "Captain says no one gets to her without getting past me first. I've been practising my angry face!"
   ]
  ],
  "after": [
   [
    "deckA",
    "…I'll tell the Captain you're the real deal."
   ]
  ]
 },
 "Beat Dockhand Sol": {
  "lines": [
   [
    "deckB",
    "Pim lost? Ha. Pim always loses. I'm the one who loads the cargo — and the cargo is HEAVY."
   ]
  ],
  "after": [
   [
    "deckB",
    "Fine, fine. The west beach is where the Water Echoes wash up. Good luck, Ranger."
   ]
  ]
 },
 "Catch a Water Echo on the west beach": {
  "lines": [
   [
    "maren",
    "Water Echoes wash up on the beach west of town at every tide. Weaken one, then bind it."
   ],
   [
    "maren",
    "Watch how they move. They remember the sea — even the ones that only ever lived in a PC."
   ]
  ]
 },
 "Tide Trial: battle Captain Maren": {
  "lines": [
   [
    "maren",
    "You bound a Water Echo without hurting it. Vale chose well."
   ],
   [
    "maren",
    "Now. The sea keeps nothing still — and neither will I!"
   ]
  ],
  "after": [
   [
    "maren",
    "Ha! You fight like the tide coming in — slow, then everywhere at once. That's a compliment."
   ]
  ]
 },
 "Visit the Card Shop by the plaza": {
  "lines": [
   [
    "maren",
    "One more thing, Ranger. The Card Shop just got in Ranger outfits — a new coat for a new Seal. Go see the clerk."
   ],
   [
    "maren",
    "And keep an eye on the chests out in the wild. Sailors stash all sorts of things in them. Clothes included."
   ]
  ]
 },
 "Travel west along Route 1": {
  "lines": [],
  "after": [
   [
    "rho",
    "Psst. Over here. Don't look now, but there's a guy in a black coat by the grass, and his machine is humming at the Echoes."
   ],
   [
    "rho",
    "That's a siphon. I've heard about those. They overcharge an Echo until it's terrified — and a terrified Echo prints a rare card."
   ]
  ]
 },
 "Someone in black is siphoning Echoes — stop the grunt": {
  "lines": [
   [
    "grunt",
    "Static Syndicate business. Every Echo we pump full of relay power prints a shiny card. Rare cards, rare money. Scram!"
   ],
   [
    "you",
    "…"
   ],
   [
    "grunt",
    "You're not scramming. Why is nobody ever scramming?!"
   ]
  ],
  "after": [
   [
    "grunt",
    "The Director's going to hear about this. And then YOU'LL hear about the Director!"
   ],
   [
    "rho",
    "The Director. Great. They have a Director. I'm going to Mistvale ahead of you — meet me at the waterwheel."
   ]
  ]
 },
 "Reach Mistvale and find Rho at the waterwheel": {
  "lines": [
   [
    "rho",
    "There you are! Look — the Syndicate hooked a second siphon into the waterwheel. The whole village's Echoes are being drained."
   ],
   [
    "rho",
    "And look at these stones by the water. Unown script, older than the relay. Mistvale people say the stones started glowing the same week the Echoes woke up."
   ],
   [
    "rho",
    "Record them with your Lattice. Dr. Vale needs to see this — I think it's a message."
   ]
  ]
 },
 "Record 2 glyph stones in Mistvale": {
  "lines": [],
  "after": [
   [
    "rho",
    "Two glyphs… they're the same shape, just mirrored. Like a door and its reflection. Okay, I hate that. Let's unplug that siphon."
   ]
  ]
 },
 "Unplug the siphon: beat the grunt at the waterwheel": {
  "lines": [
   [
    "grunt2",
    "Back off! This siphon was not my idea! But it IS my job!"
   ]
  ],
  "after": [
   [
    "grunt2",
    "Fine! Unplug it! The Echoes were giving me the creeps anyway. They kept… looking at me."
   ]
  ]
 },
 "Bloom Trial: battle Lass Mira": {
  "lines": [
   [
    "mira",
    "You cleared the siphon? The fog's lighter already. You can almost see the far bank."
   ],
   [
    "mira",
    "I'm Mira, Warden of the Bloom Trial. The fog here keeps what it loves. It loves you a little now. And so do I — a battle!"
   ]
  ],
  "after": [
   [
    "mira",
    "Wow. Your partner fights like it remembers you from somewhere."
   ]
  ]
 },
 "Climb Route 2 to the ranger checkpoint": {
  "lines": [
   [
    "ranger",
    "Checkpoint! Nobody climbs to Starfall at night without proving they can handle the night Echoes."
   ],
   [
    "ranger",
    "The Archivists up there are… intense. They think the relay is talking. Show me you can keep your head."
   ]
  ],
  "after": [
   [
    "ranger",
    "Go on up. And Ranger — if you hear someone whispering your name on the pass, it's just the wind. Probably."
   ]
  ]
 },
 "Enter Starfall — the Archivist at the edge of town knows the way": {
  "lines": [
   [
    "archivist",
    "You carry a Lattice licence. Then you carry the Lab's question with you: what are the Echoes?"
   ],
   [
    "archivist",
    "We Archivists have an answer. Warden Sable will give it to you, at the observatory — once the stars are up and the signal is clear."
   ],
   [
    "archivist",
    "Record the stones around town first. They are older than Starfall itself."
   ]
  ]
 },
 "Record 2 glyph stones around Starfall": {
  "lines": [],
  "after": [
   [
    "archivist",
    "Four glyphs now. Put them together and they spell a word in the old script: RE… ME… The rest is missing."
   ]
  ]
 },
 "Catch a Psychic or Metal Echo under the Starfall sky": {
  "lines": [
   [
    "archivist",
    "The sky here pulls Psychic and Metal Echoes out of the relay like iron to a lodestone. Bind one — Sable will want to see how it reacts to you."
   ]
  ]
 },
 "Meet Warden Sable at the observatory": {
  "lines": [
   [
    "sable",
    "Tonight the relay spelled a whole word in Unown: REMEMBER."
   ],
   [
    "sable",
    "The Echoes are not copies, Ranger. They are memories. Every Pokémon that passed through Node 7 left a piece of itself — the moment it was afraid, the moment it was happy, the face of its trainer."
   ],
   [
    "sable",
    "The Syndicate burns those memories for foil. Your Lab prints them on cards and sells them in packs. Show me what you are before I decide which side you stand on."
   ]
  ]
 },
 "Night Trial: battle Warden Sable": {
  "lines": [],
  "after": [
   [
    "sable",
    "…You battle as if the cards could feel it. Good. Keep that."
   ]
  ]
 },
 "Cross Signal Pass to Frostline": {
  "lines": [],
  "after": [
   [
    "rho",
    "There you are! Don't freak out. Something is down in the ice caves. Something BIG. Come see."
   ]
  ]
 },
 "Find Rho near the ice caverns": {
  "lines": [
   [
    "rho",
    "Two Echoes fused down there. Half Lapras, half something no Pokédex knows. It sings. Under the ice. You can feel it in your teeth."
   ],
   [
    "rho",
    "And there's a Syndicate admin herding it with a siphon whip. Admin Vex. She's the one who pays the grunts."
   ]
  ]
 },
 "Stop Admin Vex": {
  "lines": [
   [
    "vex",
    "A fused Echo prints a card nobody has ever seen. Do you know what a collector pays for 'nobody has ever seen'?"
   ],
   [
    "vex",
    "You are bad for business, Ranger. Let's fix that."
   ]
  ],
  "after": [
   [
    "vex",
    "Enjoy it. The Director is already digging somewhere much warmer than this."
   ]
  ]
 },
 "Record 2 glyph stones in the snow": {
  "lines": [],
  "after": [
   [
    "rho",
    "Six glyphs. RE-MEM-BER… and then a seventh glyph that keeps changing every time I blink. Okay. Orin. Let's go see Orin."
   ]
  ]
 },
 "Rime Trial: battle Elite Orin": {
  "lines": [
   [
    "orin",
    "The ice keeps what the relay throws away. I have watched it keep things for forty years."
   ],
   [
    "orin",
    "So do I. Show me what YOU keep."
   ]
  ]
 },
 "Follow the Stormrise Road to Voltspire": {
  "lines": [],
  "after": [
   [
    "kai",
    "Hey — over here, by the tower! You're the Ranger with four Seals, right? I need a hand, and fast."
   ]
  ]
 },
 "Stabilise 3 relay pylons": {
  "lines": [],
  "after": [
   [
    "kai",
    "Pylons are stable! Feel that? The storm's quieter. The Echoes are calming down too."
   ],
   [
    "kai",
    "The siphon trucks were heading south when I got here. Sandreach. Whatever the Director wants, it's there."
   ]
  ]
 },
 "Catch a Lightning Echo": {
  "lines": [
   [
    "kai",
    "The storm left a lot of Lightning Echoes out on the plateau. Vera will want to see one bound before she accepts your challenge."
   ]
  ]
 },
 "Surge Trial: battle Warden Vera": {
  "lines": [
   [
    "vera",
    "You stood in my storm and kept your cards dry. Kai says you fixed my pylons too. I owe you one."
   ],
   [
    "vera",
    "So I'll pay you back the only way I know. Hold a real charge!"
   ]
  ]
 },
 "Descend the Glassburn Steps to Sandreach": {
  "lines": [],
  "after": [
   [
    "vale",
    "Ranger! You came. Good. You need to see this with your own eyes, or you will not believe me."
   ]
  ]
 },
 "Meet Dr. Vale at the dig site": {
  "lines": [
   [
    "vale",
    "The dunes fused into glass — in the shape of Pokémon. A Charmander, mid-yawn. A Pidgey, wings open. Hundreds of them."
   ],
   [
    "vale",
    "Every silhouette matches a transfer through Node 7… thirty years ago. The night of the storm."
   ],
   [
    "vale",
    "Sable was right. They are memories. I have been printing memories and selling them in foil packs."
   ],
   [
    "vale",
    "…Record the silhouettes. All of them we can find. Somebody has to remember these properly."
   ]
  ]
 },
 "Record 3 glass silhouettes": {
  "lines": [],
  "after": [
   [
    "vale",
    "Thank you. I will make this right, Ranger. I do not know how yet. But I will."
   ]
  ]
 },
 "Glass Trial: battle Hiker Dom": {
  "lines": [
   [
    "dom",
    "Sand remembers heat, kid. Glass remembers everything. Let's see what your deck remembers."
   ]
  ],
  "after": [
   [
    "dom",
    "Hah! Good. Now go — the Syndicate dug into the old vents west of town. Their Director is down there with a drill the size of a house."
   ]
  ]
 },
 "Confront Director Kest at the vents": {
  "lines": [
   [
    "kest",
    "Ah. Vale's little Ranger. You've come a long way to see a hole in the ground."
   ],
   [
    "kest",
    "Memories? Echoes are ore, Ranger. The relay is a mine. Vale knows it — she just prints prettier labels."
   ],
   [
    "kest",
    "I am simply the only one honest enough to dig."
   ]
  ],
  "after": [
   [
    "kest",
    "…The relay will wake whether I dig or not. When it does, you will wish someone had kept a hand on the switch."
   ]
  ]
 },
 "Ember Trial: battle Kai at the vent rim": {
  "lines": [
   [
    "kai",
    "You shut down the Syndicate! Okay — now finish your seventh Trial. Fire against fire, Ranger!"
   ]
  ]
 },
 "Take Route 6 home and talk to Dr. Vale": {
  "lines": [
   [
    "vale",
    "Node 7 is waking up. The Echoes are drifting toward the Rift from every island. Sable calls what is gathering there GLYPH."
   ],
   [
    "vale",
    "The Archivists want GLYPH left free — the memories belong to the Pokémon. I want the relay shielded, sealed, safe. Both of us are a little bit right."
   ],
   [
    "vale",
    "Whoever reaches Node 7 first decides. That will be you, Ranger. I will accept whatever you choose."
   ],
   [
    "vale",
    "Only a Champion may cross the causeway. Lyra is waiting for you at Frostline."
   ]
  ]
 },
 "Go to the Relay Causeway at Frostline": {
  "lines": [],
  "after": [
   [
    "lyra",
    "So you're the one the relay keeps humming about. Come closer. I don't bite. My dragons do."
   ]
  ]
 },
 "Champion Trial: battle Champion Lyra": {
  "lines": [
   [
    "lyra",
    "Seven seals. Everyone who reaches Node 7 gets one match with me. Nobody has ever crossed this causeway."
   ],
   [
    "lyra",
    "Make it count."
   ]
  ]
 },
 "Cross the causeway to the Obsidian Rift": {
  "lines": [],
  "after": [
   [
    "glyph",
    "…R A N G E R …"
   ],
   [
    "glyph",
    "…Y O U  C A M E …"
   ]
  ]
 }
};
export const OUTROS = {
 "A Licence to Remember": [
  [
   "rho",
   "Not bad, Ranger. Not bad at all."
  ],
  [
   "vale",
   "The Circuit Wardens certify every Ranger. Eight Trials, eight seals. The first Warden is right here: Captain Maren, on the docks."
  ],
  [
   "vale",
   "And Ranger… if an Echo ever looks at you as if it knows you, write it down. Please."
  ]
 ]
};
