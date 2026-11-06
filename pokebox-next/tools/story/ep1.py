# Sigil & Spark — Episode 1 "The Unwritten" (draft 1, 2026-11-06) — the playable form of claude/sigil-and-spark-ep1-script.md
# python build_story.py ep1   → out/ep1.json + branch bot report. Copy ep1.json to Content/PBX/Story/.
from story_dsl import *

S = Story('ep1', start='s1_harbour', title='Episode 1 · The Unwritten')
S.stage('Pier', (120000, 0, 0))   # v4 set #1: the pier at dusk (tools/sets/set_pier.py → pbx_sets.import_set)
def P(x, y, z=0): return f'stage:Pier:{x},{y},{z}'
S.cast('rho', 'Rho', 'rho', (.4, .75, 1))
S.cast('bruce', 'Captain Bruce', 'guard', (.75, .7, .6))
S.cast('vale', 'Archivist Vale', 'vale', (.8, .8, .85))
S.cast('kelvin', 'Scribe Kelvin', 'aide', (.6, .8, .5))
S.cast('gus', 'Old Gus', 'fisher', (.85, .7, .45))
S.cast('omari', 'Omari', 'kid', (1, .75, .3))
S.cast('eraser', 'The Eraser', 'eraser', (.95, .95, .95))
S.cast('town', 'Someone', 'town', (.7, .7, .7))
S.cast('zuri', 'Zuri', 'merchant', (.9, .55, .35))
S.cast('sunita', 'Sunita', 'gardener', (.55, .8, .45))

def rho_ends_alone():
    """Rho walks away alone: with all three pages he hunts them his own way; torn, the fog takes him"""
    return if_('rho_pages>=3',
               [setf('END_ALONE'), nar('He walked north along the cliffs, three small lights circling him. He did not look back.')],
               [setf('END_TAKEN'), wait(1.0), sfx('ui_page'), nar('Far off on the cliff road, a white light. A shout, cut short. Then only the sea.')])

# =============================================================== prologue (owner 2026-11-06: "at the start, in simple words,
# explain the basics — what kind of game it is and what it will be about, without details")
S.prologue('Sigil & Spark is a story game.', 'You will not win it by fighting. You will write it by choosing.')
S.prologue('Every choice you make is remembered.', 'Some change how people see you. Some change who lives... and who is lost.')
S.prologue('Sometimes there is no time to think.', 'When the line of ink burns down, silence is a choice too.')
S.prologue('There are no right answers.', 'Only the story you write.')
S.prologue('In a small harbour town, on the night every sixteen-year-old opens a book of magic...', 'something is coming to erase it all.')
S.prologue('Your book is blank.', 'What you write in it is up to you.')

# =============================================================== SCENE 1 — Before the Rite
S.scene('s1_harbour', 'Before the Rite',
    setf('rho', v=2), setf('gus', v=3), setf('omari', v=2), setf('rho_pages', v=0),
    blanked(False), place(P(-420, 340) + ':15'), sun(-7, 250, 0.75, (1.0, .58, .36)), music('harbour'), {'amb': 'harbour'},
    npc('gus', P(-250, 430), 200), npc('rho', P(760, 930), 160), npc('omari', P(-450, 330), 30), npc('bruce', P(480, 150), 250),
    npc('zuri', P(-900, 220), 10), npc('sunita', P(-330, 140), 0), npc('kelvin', P(300, 430), 300),
    title('EPISODE ONE', 'The Unwritten'),
    nar('Tonight every sixteen-year-old in Lumen Harbor opens a Codex for the first time.'),
    nar('Tonight the Script decides who you are.'),
    say('gus', "Lamp's trimmed. Oil's in. You did all that before I woke. Nervous?"),
    choice('', 8, [
        opt('"Terrified."', say('gus', 'Good. Means you know it matters.'), rel(gus=1)),
        opt('"No. It\'s just a book."', say('gus', "That's what I said. Forty years ago."), say('gus', '...')),
        opt('"What did your book say, Gus?"', say('gus', 'Two pages. A gull and a bad temper.'),
            say('gus', "Ask me tomorrow and I'll tell you about the third one."), rel(gus=1), setf('GUS_THIRD_PAGE')),
    ], silent=say('gus', "Go on. They won't start without the lantern-keeper's kid."), id='1a'),
    hub(objective='Find Rho before the bell', exit='seen.rho && seen.omari && seen.bruce', spots=[
        spot('lamp', 'Look at the green lamp', P(560, 60), note('The all-clear lamp. Only the watch may light it.')),
        spot('gate', 'Look at the sea gate', P(-1150, 120), note('Iron, older than the town. Opens only from inside, with the Archivist\'s key... or the watch\'s.')),
        spot('poster', 'Read the poster', P(-120, 40), note('THE RITE OF PAGES — TONIGHT — BRING NOTHING BUT YOURSELF.')),
        spot('dice', 'Look at the dice', P(300, 140), note('Someone lost here. Badly.')),
        spot('boat', "Look at Gus's boat", P(820, 1250), note("Gus never ties a bowline that lazy. Unless he left in a hurry.")),
        spot('zuri', 'Talk to Zuri', 'npc:zuri',
            say('zuri', 'Rite night! Ink pens, ribbons, lucky charms. Half price for the lantern-keeper\'s kid.'),
            say('zuri', 'The White Page never came back in thirty years, you know. My mother still sold charms against them. I sell them for the joke.'),
            choice('', 8, [
                opt('"I\'ll take one. For the joke."', say('zuri', 'A white ribbon. Tie it on your book. If they come, they\'ll think you\'re one of them.'), say('zuri', '...That\'s the joke.'), setf('ZURI_RIBBON'), rel(town=1)),
                opt('"Who still believes in the White Page?"', say('zuri', 'Old Gus. And the Captain. He buys one every year and never wears it.'), setf('ZURI_HINT')),
                opt('"Maybe later."', say('zuri', 'Later is when they sell out.')),
            ], silent=say('zuri', 'Suit yourself.'), id='zuri')),
        spot('sunita', 'Talk to Sunita', 'npc:sunita',
            say('sunita', 'Careful, those are night lilies. They only open on Rite night. Old Script in their roots.'),
            say('sunita', 'My daughter woke one page, years ago. A moth. She cried for a week. She wanted a dragon.'),
            choice('', 8, [
                opt('"What happened to her?"', say('sunita', 'She sails with the Pellings now. The moth sits on the mast and finds them fish.'), say('sunita', 'One page is enough, if it\'s the right one.'), rel(town=1)),
                opt('"What if mine wakes nothing?"', say('sunita', 'Then you\'ll be the first person in this harbour I\'ve envied.'), say('sunita', 'Nothing written means nothing decided.')),
            ], silent=say('sunita', 'Go on. The lilies are watching.'), id='sunita')),
        spot('kelvin0', 'Talk to Kelvin', 'npc:kelvin',
            say('kelvin', 'Don\'t look at me. I am not here. I am carrying ink to the hall and I am NOT here.'),
            say('kelvin', 'Vale told me to fetch the Archivist\'s key from the vault and I have — absolutely — got it. Somewhere.'),
            choice('', 8, [
                opt('"You lost it, didn\'t you?"', say('kelvin', 'I MISPLACED it. At dice. Temporarily. It\'ll come back. Things come back.'), setf('KELVIN_DICE')),
                opt('"Want help finding it?"', say('kelvin', 'You\'re kind. Don\'t be kind to me tonight, I\'ll cry into the ink.'), rel(kelvin=1)),
            ], silent=say('kelvin', 'I\'m not here!'), id='kelvin0')),
        # --- 1c Rho
        spot('rho', 'Talk to Rho', 'npc:rho',
            say('rho', '"By ink and by breath, I open." Ink and breath. Who writes these? A poet with a head cold?'),
            say('rho', 'Dad says the Calders always wake three pages. Three. No pressure. Just my whole family history.'),
            choice('', 8, [
                opt('"You\'ll wake four. Just to annoy him."', say('rho', "Four. Yeah. I'd have it framed."), rel(rho=1)),
                opt('"And if you don\'t?"', say('rho', "Then I'll be a Calder with two pages and a very long face."), say('rho', "Don't."), rel(rho=-1)),
                opt('"Your dad will be proud whatever happens."', say('rho', "You've met him, right?"), say('rho', '...Thanks.'), rel(rho=1)),
            ], silent=say('rho', 'Great talk. Really. I feel ready now.'), id='1c'),
            say('rho', 'Whatever happens in there — same as always? You and me against the whole stupid world?'),
            choice('', 8, [
                opt('"Always."', setf('PROMISE_ALWAYS'), rel(rho=1), remember('Rho')),
                opt('"Let\'s see who wakes more pages first."', say('rho', "Oh, it's ON."), setf('PROMISE_RIVAL')),
            ], silent=[say('rho', 'Yeah. Okay.'), rel(rho=-1)], id='1c_promise')),
        # --- 1d Omari and the egg
        spot('omari', 'Talk to Omari', 'npc:omari',
            say('omari', "Psst! Behind the net sheds. Come ON."),
            say('omari', "I found it in the rocks under the lighthouse! It's alive, feel it."),
            say('omari', "If the watch finds it they'll put it in a jar at the Scriptorium. Please. Nobody checks the lighthouse."),
            choice('A Spark egg, warm, ink veins glowing under the shell.', 0, [
                opt('Hide the egg in the lighthouse.', say('omari', 'I knew it. I KNEW it. You\'re the best.'),
                    rel(omari=1), setf('EGG_HIDDEN'), remember('Omari')),
                opt('"I can\'t. Give it to Vale, she\'ll know what to do."', say('omari', "She'll put it in a jar."),
                    nar('He runs off with the egg under his coat.'), rel(omari=-1), setf('EGG_REFUSED')),
                opt('Call the watch over.', say('bruce', 'Good {lad}. Rules are rules, Omari.'), nar('The Captain takes the egg. Omari won\'t look at you.'),
                    rel(omari=-2, town=1), setf('EGG_REPORTED')),
            ], id='egg')),
        # --- 1e Captain Bruce
        spot('bruce', 'Talk to Captain Bruce', 'npc:bruce',
            say('bruce', "There's the lantern-keeper's kid. Big night."),
            say('bruce', "Wind's from the north. Fog by nine."),
            choice('', 8, [
                opt('"You look worried, Captain."', say('bruce', "I'm always worried. That's the job."), setf('BRUCE_SEED')),
                opt('"Rho\'s scared he\'ll let you down."', say('bruce', "He couldn't. Not if he tried."), say('bruce', "Tell him... no. I'll tell him."),
                    rel(rho=1), setf('BRUCE_SEED')),
                opt('"See you inside."', say('bruce', "I'll be on watch tonight. Somebody has to be.")),
            ], silent=say('bruce', "Go on. Bell's about to ring."), id='1e')),
    ]),
    sfx('bell'), nar('The Scriptorium bell rings three times.'), music('', fade=3.0),
    fade(1, .8), goto('s2_rite'))

# =============================================================== SCENE 2 — The Rite
S.scene('s2_rite', 'The Rite of Pages',
    {'npc_home': True}, sun(-35, 35, 1.0, (.86, .88, .95)), place('door:lab:in'), {'amb': 'hall'}, music('calm'), fade(0, 1.0),
    nar('Candles. Six lecterns in a ring, a closed Codex on each. The whole harbour on the benches. Rain on the high windows.'),
    say('rho', 'Benches are full. Dad\'s seat is empty. He said he\'d be here.'),
    choice('', 8, [
        opt('"He\'s on watch. He\'ll come."', say('rho', 'Yeah. Yeah, he\'ll come.'), rel(rho=1)),
        opt('"Forget him. This is your night."', say('rho', '...Easy for you to say. Nobody\'s watching yours.'), rel(rho=-1)),
    ], silent=say('rho', 'Say something. Anything.'), id='rite_wait'),
    say('kelvin', 'Ink wells, ink wells, nobody touch the ink wells—'),
    say('vale', 'Kelvin. Breathe.'),
    say('vale', 'By ink and by breath. Each of you will open your book. The Script will write what it finds in you.'),
    say('vale', 'Do not be afraid of what it writes. Be afraid of lying about it.'),
    nar('Two books open. A page each. A small Gale Spark and a Bloom Spark flicker into the air. Applause.'),
    say('vale', 'Rho Calder.'), music('riser', fade=1.0),
    nar('Light. One page writes itself — two — three. Three small Sparks circle him. The hall stands.'),
    nar('Rho looks for his father on the benches. Captain Bruce is not there.'),
    say('rho', 'Three. Three! Where\'s Dad?'),
    setf('rho_pages', v=3),
    say('vale', '{hero}.'),
    nar('You open your Codex. The page is white. It stays white.'),
    say('town', 'Blank...'),
    music('', fade=1.5), panel('Your hands on the white page.'),
    say('vale', 'Look at me. Did it write anything? Anything at all?'),
    choice('', 8, [
        opt('"It glowed. For a moment. I saw a mark."', say('vale', '...Then the Script is slow tonight.'),
            say('vale', 'The Script is slow tonight!'), setf('RITE_LIE'), rel(town=1, vale=-1), toast('Vale noticed.')),
        opt('"No. Nothing."', say('vale', 'Thank you.'), say('vale', 'The book is unwritten. It happens. Rarely.'),
            setf('RITE_TRUTH'), rel(vale=1, town=-1)),
        opt('Close the book and say nothing.', say('vale', 'Sit down, child.'), setf('RITE_SILENT'), rel(town=-1)),
    ], silent=[say('vale', 'Sit down, child.'), setf('RITE_SILENT'), rel(town=-1)], id='rite'),
    if_('RITE_LIE', [say('rho', "You're a terrible liar. I won't tell."), rel(rho=1), setf('RHO_KNOWS_LIE')],
        if_('RITE_TRUTH', [say('rho', 'That was brave. Stupid. Brave.'), rel(rho=1)],
            say('rho', "Hey. It doesn't mean anything."))),
    say('omari', 'BLANK IS COOL!'),
    nar('Laughter, the good kind. Then every candle in the hall leans toward the sea windows at once.'),
    goto('s3_white'))

# =============================================================== SCENE 3 — The White Page
S.scene('s3_white', 'The White Page',
    sfx('white'), music('action', fade=0.5), flash(1, 1, 1), nar('The high windows turn white. Not bright. White, like paper.'),
    nar('Below the hall, the sea gate grinds open. Fog pours in at floor level.'),
    say('eraser', 'No one will be hurt who does not hold on.'),
    blanked(True),
    nar('Light from their open palms. Where it touches, people go chalk-white and still.'),
    say('vale', 'Out! Through the stacks! Kelvin, the children!'),
    nar('Kelvin is already gone.'),
    nar('An Eraser steps in front of Omari. Another grabs Rho\'s Codex and begins to pull the pages out.'),
    sfx('tear'), say('rho', 'AAAH—!'),
    nar('Where the pages tear, the stubs bleed. Not ink. Blood, running down the spine of the book and over his fingers.'),
    panel('Rho\'s hands on the book, red to the wrists.'),
    choice('', 5, [
        opt('Pull Omari out of the light.', nar('You tackle Omari behind a lectern. The light misses him by a hand.'),
            nar('Behind you, two pages tear.'), setf('SAVED_OMARI'), setf('rho_pages', v=1), rel(rho=-2, omari=3),
            remember('Rho'), say('rho', '...You chose.')),
        opt("Hold Rho's Codex shut.", nar("You slam both hands on Rho's book. The Eraser lets go, surprised."),
            nar('Behind you, Omari goes white mid-shout, his mouth still open on a word.'),
            setf('SAVED_PAGES', 'OMARI_BLANKED'), setf('rho_pages', v=3), rel(rho=2), toast('Omari will not remember anything.'),
            say('rho', '...Oh no. No, no, no.')),
    ], silent=[nar('You freeze. Vale throws herself between them.'), nar('Omari goes white. One of Rho\'s pages tears. The light strikes Vale\'s arm.'),
               setf('FROZE', 'OMARI_BLANKED', 'VALE_GRAVE'), setf('rho_pages', v=2), rel(rho=-1, vale=-1), toast('You did nothing. Everyone saw.')],
       id='light'),
    say('eraser', '...{hero}. There you are.'),
    nar('It reaches for your blank book — and the light slides off it, like water off oil.'),
    nar('An Eraser\'s blade of light opens Vale\'s forearm. She doesn\'t scream. She writes faster.'),
    say('vale', 'RUN!'),
    fade(1, .5), goto('s4_spark'))

# =============================================================== SCENE 4 — The Spark
S.scene('s4_spark', 'The Spark',
    {'amb': 'fire'}, music('suspense'), fade(0, .8),
    nar('The stacks. Tall shelves, jars of sleeping Sparks. Fire in one aisle. Kelvin\'s lantern on the floor, still lit.'),
    if_('SAVED_PAGES', nar("Rho carries Omari's white, weightless body. He won't talk.")),
    nar('A shelf of jars breaks. Three young Sparks spill out and scatter. An Eraser\'s light sweeps the aisle.'),
    choice('You can only shield one.', 12, [
        opt('Cindril', setf('partner', v=1), setf('SPARK_CINDRIL'), hint='Ember · a little red dragon that bites the air. Proud, reckless, loyal.'),
        opt('Glublet', setf('partner', v=2), setf('SPARK_GLUBLET'), hint='Tide · a round blue fish hiding under a desk. Frightened, funny, honest.'),
        opt('Sporrow', setf('partner', v=3), setf('SPARK_SPORROW'), hint='Bloom · a mushroom sprite, standing still, watching you. Quiet, old, fair.'),
    ], silent=[nar('The closest one jumps into your arms.'), setf('partner', v=2), setf('SPARK_GLUBLET')], id='spark'),
    nar('The light hits your back and slides off. Your blank Codex opens by itself.'),
    nar("For the first time, ink appears on your page. It isn't the Script's handwriting."),
    panel('The first line of ink on the white page.'),
    spark('I DID NOT NEED SAVING. ... THANK YOU.', "are they gone?? are they GONE?? ok. ok. hi. i'm glublet. hi.", 'You. ... Stood. ... Still.'),
    nar("It wasn't the Script that wrote your first page. It was a friend."),
    choice('', 8, [
        opt('"You\'re safe. I\'ve got you."', spark('I HAVE YOU. GET IT RIGHT.', 'ok. ok ok ok. ok.', 'Yes.'), rel(spark=1)),
        opt('"We have to move. Now."', spark('FINALLY. SOMEONE WITH SENSE.', 'MOVING!!', 'Go.'), if_('partner==1', rel(spark=1))),
        opt('"Why can\'t they touch my book?"', spark('WHO CARES. RUN.', 'idk!!! run!!!', 'Because. There. Is. Nothing. To. Erase.'), setf('ASKED_BOOK')),
    ], silent=spark(all='?'), id='first_words'),
    goto('s5_alley'))

# =============================================================== SCENE 5 — The Alley (Pact moment)
S.scene('s5_alley', 'The Alley',
    place('spot:rho_gate'),
    {'amb': 'rain'}, music('action'),
    nar('The fish-market alley. Fog. A Blanked Spark, big, grey, eyeless, blocks the only way to the lighthouse.'),
    spark('WRITE WITH ME.', "there's a word!! write the word!!", 'Trace. With. Me.'),
    pact('WRITE THE GLYPH',
         win=[nar('The grey Spark shudders. Colour seeps back into one eye. It lies down and lets you pass.'),
              setf('WROTE_FIRST_GLYPH'), rel(spark=1), spark('...NOT BAD.', 'WE DID THAT?!?!', 'Again. Someday.')],
         lose=[nar("Its light rakes your Spark's side before you push through. A white scar stays."),
               setf('SPARK_SCARRED'), rel(spark=-1), spark("IT'S NOTHING.", "ow. ow. it's ok. ow.", 'Slow. ... Learn.')]),
    fade(1, .8), goto('s6_dawn'))

# =============================================================== SCENE 6 — Dawn
S.scene('s6_dawn', 'Dawn',
    place('door:house:in'),
    {'amb': 'sea'}, music('lullaby'), fade(0, 1.2),
    nar('Grey dawn. Half the town stands in the streets, white and still. The White Page ships are gone.'),
    say('gus', "Thirty years I kept this lamp lit so I'd see them coming. And they came in fog."),
    say('gus', "Who's missing?"),
    if_('SAVED_OMARI', say('gus', "The boy's fine. Kept asking for you."),
        [nar('Omari stands on the lighthouse steps, white, looking at nothing.'), panel("Omari's chalk-white face, still smiling at last night's joke.")]),
    if_('VALE_GRAVE', nar("Vale arrives. Her arm hangs in Kelvin's scarf. She can't lift her Codex."), nar('Vale arrives, her arm bound.')),
    say('vale', 'The archive is gone. Every Codex we held, every name.'),
    say('vale', 'They knew exactly where the sea gate was. And they knew it would be open.'),
    say('vale', 'Show me your book.'),
    if_('WROTE_FIRST_GLYPH', [say('vale', 'A glyph. Written back. Not erased... written.'), say('vale', 'Nobody has done that in three hundred years.'), rel(vale=1)]),
    if_('RITE_LIE', [say('vale', "You told the hall it glowed. It didn't."), say('vale', "I'm not angry. I need you to stop lying to me. Now.")]),
    if_('ASKED_BOOK', say('vale', 'You want to know why their light slid off you. So do I.')),
    say('vale', 'Did any of them speak to you? Anything. A word.'),
    choice('', 0, [
        opt('"One of them said my name. Like it was looking for me."', say('vale', "Then it wasn't a raid. It was a search."),
            say('vale', 'And you are what they came for.'), say('vale', 'Take this. The Archivist\'s key. You may need doors opened.'),
            setf('NAME_TOLD'), rel(vale=2), remember('Vale')),
        opt('"No. Nothing."', say('vale', '...Alright.'), setf('NAME_HIDDEN'), rel(vale=-1, spark=-1),
            spark('LIAR.', "why didn't you tell her??", 'Why.')),
        opt('"Why does it matter? Look outside."', say('vale', 'Because what happened outside will happen again.'), setf('NAME_HIDDEN')),
    ], id='name'),
    nar('Rho walks in, wet, holding his Codex.'),
    say('rho', "My dad's not at the watchhouse. Not at home. Nobody's seen him since the bell."),
    say('rho', 'Help me find him. And find whoever opened that gate.'),
    say('vale', 'Not today. Today you sleep, both of you. The harbour will still be white tomorrow.'),
    fade(1, .8), goto('s6b_night'))

# =============================================================== SCENE 6b — The lighthouse at night (quiet scene)
S.scene('s6b_night', 'The Lamp Room',
    {'amb': 'rain'}, music('calm'), fade(0, 1.0),
    nar('Night. The lamp room at the top of the lighthouse. The beam sweeps over a harbour full of white statues.'),
    if_('partner==1', nar('Cindril sleeps curled in the warm brass of the lamp, smoking a little.'),
        if_('partner==2', nar('Glublet sleeps in the bucket of rain water, blowing bubbles.'), nar('Sporrow sits on the window sill, not sleeping, watching the beam.'))),
    nar('Footsteps on the stair. Rho, with a blanket and two cups of Gus\'s terrible tea.'),
    say('rho', 'Couldn\'t sleep. Every time I close my eyes I see the hands on my book.'),
    if_('rho_pages<3', [say('rho', 'It still hurts. Where the pages were. Like a tooth that\'s gone.'), nar('The stubs in his book are dark and crusted.')]),
    choice('', 8, [
        opt('"Show me."', nar('He opens the book. You look at what\'s left for a long time.'), say('rho', 'Don\'t make that face. I\'m not dead.'), rel(rho=1)),
        opt('"I\'m sorry."', if_('SAVED_OMARI', say('rho', 'Are you? You\'d do it again.'), say('rho', 'Not your fault. Not all of it.'))),
        opt('Hand him your tea too.', say('rho', 'That bad, huh. ...Thanks.'), rel(rho=1)),
    ], silent=say('rho', 'Yeah. Me neither.'), id='night_1'),
    say('rho', 'When I was small, Dad used to bring me up here. He said the lamp was the only thing in the harbour that never lied.'),
    say('rho', 'He was weird last night. Before. He hugged me at breakfast. He never hugs.'),
    choice('', 8, [
        opt('"Maybe he knew something was coming."', say('rho', '...Don\'t.'), say('rho', 'Don\'t say it like that.'), setf('NIGHT_DOUBT')),
        opt('"He loves you. That\'s all it was."', say('rho', 'Yeah.'), rel(rho=1)),
        opt('"Where would he go, if he ran?"', say('rho', 'The cliffs. The old Hollowmere road. He goes there when he can\'t breathe.'), setf('KNOW_CLIFFS')),
    ], silent=say('rho', '...'), id='night_2'),
    say('rho', 'Can I ask you something? The Eraser. It knew your name. Why?'),
    choice('', 8, [
        opt('"I don\'t know. That scares me more than anything."', say('rho', 'Okay. Okay. We find out together.'), rel(rho=1), setf('TOLD_RHO_NAME')),
        opt('"It didn\'t. You heard wrong."', say('rho', 'I heard what I heard.'), rel(rho=-1), remember('Rho')),
    ], silent=[say('rho', 'Right. Secrets. Great.'), rel(rho=-1)], id='night_3'),
    spark('HE IS AFRAID. SO ARE YOU. STOP PRETENDING.', 'he\'s sad. can i sit on him. i\'m going to sit on him.', 'The. Lamp. Does. Not. Lie.'),
    nar('Rho falls asleep against the window. You watch the beam go round until it\'s grey outside.'),
    if_('EGG_HIDDEN', [nar('In the oil cupboard, the egg ticks once. Like a clock. Like something counting.')]),
    fade(1, 1.0), goto('s7_gate'))

# =============================================================== SCENE 7 — Who opened the gate?
def clue(flag, *lines):
    return [setf(flag), add('CLUES'), lines, toast('A clue is written in your Codex.')]

S.scene('s7_gate', 'Who Opened the Gate?',
    setf('CLUES', v=0), place('spot:rho_greet'), {'amb': 'rain'}, music('suspense'), fade(0, 1.0),
    nar('Morning. The harbour in daylight, silent. White figures everywhere, frozen mid-step.'),
    hub(objective='Find out who opened the sea gate', exit='seen.square', spots=[
        spot('c1', 'Climb to the green lamp', 'npc:bruce', clue('C1', note('The wick is burnt. Someone lit the all-clear at nine. Only the watch can.'))),
        spot('c2', 'Look in the watchhouse stove', 'npc:bruce',
            spark('MOVE. I WILL DRY IT.', "i'll lift the ash!! gently!!", 'Roots. Will. Pull.'),
            clue('C2', note('The last page of the watch log, half-burnt: "21:00 — lamp lit — B."'))),
        spot('c3', 'Examine the sea gate', 'spot:rho_gate',
            if_('NAME_TOLD', clue('C3', note("No break. A key, from the inside. Not the Archivist's wards — the watch's key.")),
                note('No break. Someone opened it with a key, from the inside. You can\'t tell whose.'))),
        spot('c4', 'Walk through the watchhouse', 'npc:bruce', clue('C4', note('Everyone around it is white. Inside, not even the cat.'))),
        spot('c5', "Open the Captain's drawer", 'npc:bruce',
            clue('C5', note("A white silk ribbon stitched with Hollowmere's sign. The White Page's token.")),
            if_('EGG_REPORTED', note("And Omari's egg, safe and warm in a padded box. Kept for someone."))),
        spot('r1', 'Look in the tavern', '', note("Kelvin's key, in the tavern keeper's white hand. Lost at dice before the Rite. Not Kelvin, then.")),
        spot('r2', "Read Gus's logbook", 'npc:gus',
            note('"Out at sunset. Saw sails to the north. White." Gus went to look, not to open doors.'),
            if_('GUS_THIRD_PAGE', [say('gus', 'My third page. A ship with white sails. I\'ve waited my whole life for it.'), rel(gus=1)])),
        spot('kelvin', 'Talk to Kelvin', 'npc:kelvin',
            say('kelvin', "I ran. I ran and I left the children and I'll never—"),
            choice('', 8, [
                opt('"You\'re alive. That\'s something."', rel(kelvin=1), say('kelvin', '...Thank you.')),
                opt('"You left them."', rel(kelvin=-1), say('kelvin', 'I know.')),
            ], silent=say('kelvin', '...'), id='kelvin')),
        spot('gus7', 'Question Gus', 'npc:gus',
            say('gus', 'Ask what you came to ask, {lad}. You never could hide a question.'),
            choice('', 8, [
                opt('"Your boat was out last night. Why?"', say('gus', 'Saw sails at sunset. White ones. I rowed out to be sure I wasn\'t mad.'), say('gus', 'I wasn\'t.'), setf('GUS_ALIBI')),
                opt('"Who has a key to the sea gate?"', say('gus', 'The Archivist. And the Captain of the watch. Always has been, since the gate was cast.'), setf('KNOW_KEYS')),
                opt('"Did you open it, Gus?"', say('gus', '...'), say('gus', 'Thirty years I watched for them, and you ask me that.'), rel(gus=-2), remember('Gus')),
            ], silent=say('gus', 'Well? Ask.'), id='gus7')),
        spot('zuri7', 'Question Zuri', 'npc:zuri',
            say('zuri', 'Half my stock is white now. Ha. Ha.'),
            say('zuri', 'You want to know about the Captain\'s ribbon? He bought it last week. First time in thirty years he wore one out of my shop.'),
            clue('C6', note('Bruce bought a white ribbon last week — and wore it.')), cond='ZURI_HINT || ZURI_RIBBON'),
        spot('rho1', 'Talk to Rho', 'npc:rho',
            say('rho', "Nothing at the cliffs. Nothing at the pier. Where IS he?"),
            if_('KNOW_CLIFFS', say('rho', 'I checked the Hollowmere road. His boot prints, going up. Coming back. Fresh.')),
            if_('C2 || C5', choice('What you found points at his father.', 8, [
                opt('Show him.', setf('RHO_SAW_PROOF'), say('rho', '...No.'), say('rho', "That's — no. Somebody put that there.")),
                opt('Hide it.', setf('RHO_KEPT_IN_DARK'), say('rho', 'Keep looking. Please.')),
            ], silent=[setf('RHO_KEPT_IN_DARK'), say('rho', 'Keep looking. Please.')], id='show_rho')), cond='CLUES>=1'),
        spot('square', 'Go to the square (Vale is waiting)', 'npc:vale',
            say('vale', 'Someone opened the gate. Before the town does something stupid, I\'d like it to do something correct.'),
            say('vale', 'You went through the harbour. Tell us.'),
            choice('', 0, [
                opt('Accuse Captain Bruce.', if_('CLUES>=3 && C2 || CLUES>=3 && C5 || CLUES>=3 && C6', [
                        nar('The square turns. Captain Bruce walks in from the cliffs, soaked. He does not deny it.'),
                        say('bruce', 'I was six when the words drowned Hollowmere. They promised it would never happen again.'),
                        say('bruce', 'They promised they\'d spare my boy.'),
                        say('rho', 'Dad.'),
                        say('bruce', 'I\'m sorry, Rho. I would do it again. That\'s the worst of it.'),
                        setf('ACCUSED_BRUCE_PROOF'), rel(town=1, vale=1),
                        if_('RHO_SAW_PROOF', rel(rho=-1), rel(rho=-3)), remember('Rho'),
                        nar('The watch locks their own Captain in the watchhouse.')],
                    [say('bruce', 'The kid with the blank book is accusing the man who held the north wall all night?'),
                     nar('Uneasy laughter. Bruce looks at you a long time. He knows that you know.'),
                     setf('ACCUSED_BRUCE_WEAK'), rel(town=-1, rho=-2)])),
                opt('Accuse Old Gus.', say('gus', "If that's what you think of me."), nar('The watch takes him. Captain Bruce leads the arrest.'),
                    setf('ACCUSED_GUS'), rel(gus=-3, town=1), remember('Gus')),
                opt('Accuse Scribe Kelvin.', say('kelvin', '...Maybe it was my fault. Maybe it was.'), nar('Kelvin leaves town that night.'),
                    setf('ACCUSED_KELVIN'), rel(vale=-1)),
                opt('"I don\'t know yet."', say('vale', 'Honest. Useless, but honest.'), setf('ACCUSED_NONE'), rel(vale=1)),
            ], id='accuse'), cond='CLUES>=1'),
    ]),
    fade(1, .8), goto('s8_road'))

# =============================================================== SCENE 8 — The Road
S.scene('s8_road', 'The Road',
    place('spot:rho_gate'),
    {'amb': 'wind'}, music('lullaby'), fade(0, 1.0),
    say('vale', 'They went north. They took the archive. They will come back for you.'),
    if_('ACCUSED_GUS', say('vale', 'Gus asked me to give you his coat. Even now.'), say('gus', 'Take the coat. North wind bites.')),
    if_('EGG_HIDDEN', note('In the coat pocket, the egg. Warm.')),
    nar('Rho is waiting at the milestone.'),
    if_('ACCUSED_BRUCE_PROOF', say('rho', 'You stood in the square and gave them my father.'),
        if_('SAVED_OMARI', [say('rho', 'I had three pages for one night. Three.'), say('rho', "You chose a kid over me. I know that was right. I don't care that it was right.")],
            if_('SAVED_PAGES', say('rho', "You saved my book. You lost Omari for it. I can't decide if I owe you or hate you."),
                say('rho', 'You just stood there. Two pages. Two.')))),
    if_('PROMISE_ALWAYS', say('rho', '"You and me against the whole stupid world." You said that. Yesterday.')),
    if_('TOLD_RHO_NAME', say('rho', 'You told me the truth last night. About the name. I keep thinking about that.'), None),
    choice('', 8, [
        opt('"I made the choices I could live with."', say('rho', 'Lucky you.'), rel(rho=-1)),
        opt('"I would take it back if I could."', if_('rho>=1', say('rho', '...I know.'), say('rho', 'You can\'t. That\'s the point.')), rel(rho=1)),
        opt('"Everything that happened is the White Page\'s fault. Not mine. Not yours."', say('rho', 'And my father\'s.'), say('rho', 'Say it. And my father\'s.'), cond='ACCUSED_BRUCE_PROOF || ACCUSED_BRUCE_WEAK'),
    ], silent=say('rho', 'Nothing? Really?'), id='road_0'),
    choice('', 8, [
        opt('"Come with me. We find them together. We bring everyone back."',
            if_('rho>=2', [setf('END_TOGETHER'), say('rho', '...Together. Fine. Together.')],
                [say('rho', 'No. Not with you.'), rho_ends_alone()])),
        opt('"Go. Do what you have to. I won\'t stop you."', say('rho', 'I wasn\'t asking.'), rho_ends_alone()),
        opt('"You want to hit someone? Hit me."',
            pact("RHO'S SPARKS",
                 win=[nar('He lies in the road, laughing and crying.'), say('rho', "...Fine. Fine. I'm coming. Someone has to watch you lie."),
                      setf('END_TOGETHER', 'RHO_RESENTS')],
                 lose=[say('rho', 'Stay out of my way.'), rel(spark=-1), setf('END_ALONE'),
                       nar('He walks north along the cliffs. You stay in the road until the light is gone.')],
                 steps=4, window=1.4)),
    ], silent=[say('rho', "That's what I thought."), rho_ends_alone()], id='road'),
    if_('END_TOGETHER', nar('Two books. One blank. One torn. Enough to start.'),
        if_('END_TAKEN', [panel("Rho's last page blows down the road and lands at your feet."),
                          nar("The White Page doesn't take what it fears. It takes what's alone.")],
            nar('He had his pages. You had yours. Neither of you had the other.'))),
    fade(1, 1.0), wait(.6), fade(0, .8),
    if_('EGG_HIDDEN', [nar('Night. In the pocket of Gus\'s coat, the egg cracks.'), panel('One ink-black eye opens.')],
        [nar('Night. On a white ship, the Eraser in the porcelain mask holds torn pages up to a lantern.'), say('eraser', 'Unwritten. How... interesting.')]),
    music('riser', fade=1.0), title('END OF EPISODE ONE', 'Your choices wrote these pages.'),
    end())

# =============================================================== "Your Codex"
S.codex('The Egg', ('EGG_HIDDEN', 'You kept it'), ('EGG_REFUSED', 'You refused'), ('EGG_REPORTED', 'You reported it'))
S.codex('The First Lie', ('RITE_LIE', 'You lied'), ('RITE_TRUTH', 'You told the truth'), ('RITE_SILENT', 'You said nothing'))
S.codex('The White Light', ('SAVED_OMARI', 'You saved Omari'), ('SAVED_PAGES', "You saved Rho's pages"), ('FROZE', 'You froze'))
S.codex('The Friend', ('partner==1', 'Cindril'), ('partner==2', 'Glublet'), ('partner==3', 'Sporrow'))
S.codex('The Alley', ('WROTE_FIRST_GLYPH', 'You wrote a word back'), ('SPARK_SCARRED', 'Your Spark was scarred'))
S.codex('The Name', ('NAME_TOLD', 'You told Vale'), ('NAME_HIDDEN', 'You kept it'))
S.codex('The Gate', ('ACCUSED_BRUCE_PROOF', 'Bruce, with proof'), ('ACCUSED_BRUCE_WEAK', 'Bruce, without proof'), ('ACCUSED_GUS', 'Old Gus'),
        ('ACCUSED_KELVIN', 'Scribe Kelvin'), ('ACCUSED_NONE', 'No one'))
S.codex('The Road', ('END_TOGETHER', 'Rho walks with you'), ('END_ALONE', 'Rho walks alone'), ('END_TAKEN', 'Rho was taken'))
