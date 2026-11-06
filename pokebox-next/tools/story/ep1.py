# Sigil & Spark — Episode 1 "The Unwritten" (draft 1, 2026-11-06) — the playable form of claude/sigil-and-spark-ep1-script.md
# python build_story.py ep1   → out/ep1.json + branch bot report. Copy ep1.json to Content/PBX/Story/.
from story_dsl import *

S = Story('ep1', start='s1_harbour', title='Episode 1 · The Unwritten')
S.cast('rho', 'Rho', 'rho', (.4, .75, 1))
S.cast('bruce', 'Captain Bruce', 'guard', (.75, .7, .6))
S.cast('vale', 'Archivist Vale', 'vale', (.8, .8, .85))
S.cast('kelvin', 'Scribe Kelvin', 'aide', (.6, .8, .5))
S.cast('gus', 'Old Gus', 'fisher', (.85, .7, .45))
S.cast('omari', 'Omari', 'kid', (1, .75, .3))
S.cast('eraser', 'The Eraser', 'eraser', (.95, .95, .95))
S.cast('town', 'Someone', 'town', (.7, .7, .7))

def rho_ends_alone():
    """Rho walks away alone: with all three pages he hunts them his own way; torn, the fog takes him"""
    return if_('rho_pages>=3',
               [setf('END_ALONE'), nar('He walked north along the cliffs, three small lights circling him. He did not look back.')],
               [setf('END_TAKEN'), wait(1.0), sfx('ui_page'), nar('Far off on the cliff road, a white light. A shout, cut short. Then only the sea.')])

# =============================================================== SCENE 1 — Before the Rite
S.scene('s1_harbour', 'Before the Rite',
    setf('rho', v=2), setf('gus', v=3), setf('omari', v=2), setf('rho_pages', v=0),
    blanked(False),
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
        spot('lamp', 'Look at the green lamp', 'npc:bruce', note('The all-clear lamp. Only the watch may light it.')),
        spot('gate', 'Look at the sea gate', 'spot:rho_gate', note('Iron, older than the town. Opens only from inside, with the Archivist\'s key... or the watch\'s.')),
        spot('poster', 'Read the poster', '', note('THE RITE OF PAGES — TONIGHT — BRING NOTHING BUT YOURSELF.')),
        spot('dice', 'Look at the dice', '', note('Someone lost here. Badly.')),
        spot('boat', "Look at Gus's boat", 'npc:gus', note("Gus never ties a bowline that lazy. Unless he left in a hurry.")),
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
    sfx('ui_page'), nar('The Scriptorium bell rings three times.'),
    fade(1, .8), goto('s2_rite'))

# =============================================================== SCENE 2 — The Rite
S.scene('s2_rite', 'The Rite of Pages',
    fade(0, 1.0),
    say('vale', 'By ink and by breath. Each of you will open your book. The Script will write what it finds in you.'),
    say('vale', 'Do not be afraid of what it writes. Be afraid of lying about it.'),
    nar('Two books open. A page each. A small Gale Spark and a Bloom Spark flicker into the air. Applause.'),
    say('vale', 'Rho Calder.'),
    nar('Light. One page writes itself — two — three. Three small Sparks circle him. The hall stands.'),
    nar('Rho looks for his father on the benches. Captain Bruce is not there.'),
    say('rho', 'Three. Three! Where\'s Dad?'),
    setf('rho_pages', v=3),
    say('vale', '{hero}.'),
    nar('You open your Codex. The page is white. It stays white.'),
    say('town', 'Blank...'),
    panel('Your hands on the white page.'),
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
    flash(1, 1, 1), nar('The high windows turn white. Not bright. White, like paper.'),
    nar('Below the hall, the sea gate grinds open. Fog pours in at floor level.'),
    say('eraser', 'No one will be hurt who does not hold on.'),
    blanked(True),
    nar('Light from their open palms. Where it touches, people go chalk-white and still.'),
    say('vale', 'Out! Through the stacks! Kelvin, the children!'),
    nar('Kelvin is already gone.'),
    nar('An Eraser steps in front of Omari. Another grabs Rho\'s Codex and begins to pull the pages out.'),
    say('rho', 'AAAH—!'),
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
    say('vale', 'RUN!'),
    fade(1, .5), goto('s4_spark'))

# =============================================================== SCENE 4 — The Spark
S.scene('s4_spark', 'The Spark',
    fade(0, .8),
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
    fade(0, 1.2),
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
    goto('s7_gate'))

# =============================================================== SCENE 7 — Who opened the gate?
def clue(flag, *lines):
    return [setf(flag), add('CLUES'), lines, toast('A clue is written in your Codex.')]

S.scene('s7_gate', 'Who Opened the Gate?',
    setf('CLUES', v=0),
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
        spot('rho1', 'Talk to Rho', 'npc:rho',
            say('rho', "Nothing at the cliffs. Nothing at the pier. Where IS he?"),
            if_('C2 || C5', choice('What you found points at his father.', 8, [
                opt('Show him.', setf('RHO_SAW_PROOF'), say('rho', '...No.'), say('rho', "That's — no. Somebody put that there.")),
                opt('Hide it.', setf('RHO_KEPT_IN_DARK'), say('rho', 'Keep looking. Please.')),
            ], silent=[setf('RHO_KEPT_IN_DARK'), say('rho', 'Keep looking. Please.')], id='show_rho')), cond='CLUES>=1'),
        spot('square', 'Go to the square (Vale is waiting)', 'npc:vale',
            say('vale', 'Someone opened the gate. Before the town does something stupid, I\'d like it to do something correct.'),
            say('vale', 'You went through the harbour. Tell us.'),
            choice('', 0, [
                opt('Accuse Captain Bruce.', if_('CLUES>=3 && C2 || CLUES>=3 && C5', [
                        nar('The square turns. Captain Bruce walks in from the cliffs, soaked. He does not deny it.'),
                        say('bruce', 'I was six when the words drowned Hollowmere. They promised it would never happen again.'),
                        say('bruce', 'They promised they\'d spare my boy.'),
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
    fade(0, 1.0),
    say('vale', 'They went north. They took the archive. They will come back for you.'),
    if_('ACCUSED_GUS', say('vale', 'Gus asked me to give you his coat. Even now.'), say('gus', 'Take the coat. North wind bites.')),
    if_('EGG_HIDDEN', note('In the coat pocket, the egg. Warm.')),
    nar('Rho is waiting at the milestone.'),
    if_('ACCUSED_BRUCE_PROOF', say('rho', 'You stood in the square and gave them my father.'),
        if_('SAVED_OMARI', [say('rho', 'I had three pages for one night. Three.'), say('rho', "You chose a kid over me. I know that was right. I don't care that it was right.")],
            if_('SAVED_PAGES', say('rho', "You saved my book. You lost Omari for it. I can't decide if I owe you or hate you."),
                say('rho', 'You just stood there. Two pages. Two.')))),
    if_('PROMISE_ALWAYS', say('rho', '"You and me against the whole stupid world." You said that. Yesterday.')),
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
    title('END OF EPISODE ONE', 'Your choices wrote these pages.'),
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
