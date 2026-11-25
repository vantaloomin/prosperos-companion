"""Stories for a companion in charge at work (v1.5.0): one who runs the place, and one who manages people.

Where the companion stands at work comes from companion/life/position.py. Before it, every work story was an
employee's, so the owner of the fighting pits heard rumors of layoffs at work. The stories that need a boss above them
are `positions=BOSSED` (companion/life/storyline_bank.py); these are the ones for the rest, so nobody in charge has a
thinner bank than someone who works for someone:
- the same troubles from the other side of the counter: a slow stretch instead of layoff rumors, an offer to buy the
  place instead of the place changing hands, a worker skimming instead of the boss fiddling the books;
- what only an owner meets: a supplier's prices, a rival opening nearby, the landlord, a slow season, a record week;
- what only a manager meets: caught between the team and the bosses, a hard review to give, a target hit.

They are written by the same rules as the rest of the bank (see companion/life/storyline_bank.py): the companion is
only ever `{name}`, a past-tense verb or "is", "has", "keeps", "was" after it, and nothing changes what the app keeps on
record: no story here closes the place, sells it or promotes anyone. "The place" is their workplace in any era: a bar,
a forge, a fighting pit or a noodle bar.
"""
from companion.life.story_parts import Story, beat, either

OWNER = ('owner',)
LEAD = ('lead',)

RUNS_THE_PLACE = (
    # Quiet: good days at the place.
    Story('owner_talked_up', 0, 'work', (
        beat("{name}'s place got talked up all over town, and new faces keep coming in.",
             'someone has been talking my place up all over town. new faces every day. who do I thank', 'good'),),
          positions=OWNER),
    Story('owner_big_order', 0, 'work', (
        beat("{name}'s place landed a big order, the kind that makes a month.",
             'we landed a big order at my place. the kind that makes the whole month. I may cry'),
        either(("{name} got the big order out on time, and the customer wants more.",
                "big order DONE and the customer already wants another one. we're good at this", 'good'),
               ("{name} got the big order out a day late, but the customer was happy all the same.",
                "big order out the door. a day late but they were happy. I'll take it"))), (4, 10),
          positions=OWNER),
    Story('owner_staff_party', 0, 'work', (
        beat('{name} is throwing a party for the staff at the place.',
             "throwing a party for my people at the place. they've earned it. I've earned it"),
        beat("The staff party at {name}'s place went well, and the staff keep thanking {name} for it.",
             "the staff party was a hit. everyone keeps thanking me. best money I've spent", 'good')), (4, 10),
          positions=OWNER),
    Story('owner_new_hire', 0, 'work', (
        beat('{name} took on someone new at the place.', 'took on someone new at my place. fingers crossed'),
        either(("{name}'s new hire turned out to be a natural.", 'the new hire is a natural. I got lucky', 'good'),
               ("{name}'s new hire is still learning the ropes, slowly.",
                "the new hire is... learning. slowly. we were all new once"))), (5, 12),
          positions=OWNER),
    Story('owner_record_week', 0, 'work', (
        beat("{name}'s place had its best week ever.",
             "best week EVER at my place. I counted the till twice to be sure", 'good'),), positions=OWNER),
    Story('owner_books', 0, 'work', (
        beat('{name} has been up late catching up on the books for the place.',
             'up late doing the books for the place. numbers are swimming'),
        beat("{name}'s books for the place are up to date at last.",
             'books are DONE. every penny where it should be. I feel like a new person', 'good')), (2, 5),
          positions=OWNER),
    Story('owner_day_off', 0, 'work', (
        beat('{name} took a whole day off from the place for the first time in months.',
             "took a whole day off from my place. first time in months. I don't know what to do with my hands"),
        beat("{name}'s place ran fine for a day without {name}.",
             'the place ran fine without me for a day. good. I think. good', 'good')), (1, 2),
          positions=OWNER),
    # Realistic: everyday trouble when it is yours.
    Story('owner_thin_takings', 1, 'work', (
        beat("Business at {name}'s place has been slow, and {name} may have to let someone go.",
             "business has been slow for weeks. I might have to let someone go and I feel sick about it", 'bad'),
        either(("{name} found the money to keep everyone on at the place.",
                'found the money. everyone stays. I will live on noodles for a month, worth it', 'good'),
               ("{name} had to let one of the staff go, and it weighs on {name}.",
                'had to let someone go today. worst part of running the place', 'bad'))), (3, 8),
          positions=OWNER),
    Story('owner_mistake', 1, 'work', (
        beat('{name} made a mistake at the place that will take days to put right.',
             "I messed something up at my place. badly. it's going to take days to fix", 'bad'),
        either(('{name} put the mistake at the place right before it did any harm.',
                'fixed my mess before anyone noticed. I can breathe again', 'good'),
               ("The mistake at {name}'s place cost a good customer.",
                'that mistake cost me a good customer. lesson learned the expensive way', 'bad'))), (2, 5),
          positions=OWNER),
    Story('owner_complaint', 1, 'work', (
        beat("Someone made a complaint about {name}'s place.",
             "someone complained about my place. I've been replaying it all day", 'bad'),
        either(('{name} looked into the complaint about the place, and it came to nothing.',
                'looked into the complaint. nothing in it. I still checked everything twice', 'good'),
               ('{name} made it up to the customer who complained about the place, fair or not.',
                'made it up to the customer who complained. through my teeth. but I did it'))), (2, 6),
          positions=OWNER),
    Story('owner_best_worker_leaving', 1, 'work', (
        beat("{name}'s best worker gave notice at the place.",
             'my best worker gave notice. I knew it would happen one day. I hate that it is today', 'bad'),
        either(("{name} found someone good to take over from the worker who left.",
                "found someone good to step in. they're not the same but they're good", 'good'),
               ("{name} is still covering the shifts of the worker who left.",
                'still covering the shifts myself. I live at my place now. send food', 'bad'))), (5, 12),
          positions=OWNER),
    Story('owner_supplier_prices', 1, 'work', (
        beat("{name}'s main supplier put the prices up.",
             'my main supplier just put the prices up. again. I said a word I will not repeat', 'bad'),
        either(('{name} found a new supplier at the old prices.',
                'found a new supplier at the old prices. victory is mine', 'good'),
               ("{name} put the prices up at the place to keep up, and a few regulars grumbled.",
                'had to put my prices up. a few regulars grumbled. they still came back though'))), (3, 8),
          positions=OWNER),
    Story('owner_rival_opens', 1, 'work', (
        beat("A rival opened up near {name}'s place.",
             'someone opened up right near my place. doing the same thing. RIGHT near it', 'bad'),
        either(("The rival near {name}'s place has not taken much of the trade so far.",
                "the new place nearby hasn't taken much of my trade. my regulars are loyal", 'good'),
               ("The rival near {name}'s place has taken some of the trade, and {name} is working out what to do.",
                "the new place has taken some of my trade. thinking hard about what to do", 'bad'))), (5, 12),
          positions=OWNER),
    Story('owner_landlord', 1, 'work', (
        beat("The landlord of {name}'s place wants more rent from next year.",
             'my landlord wants more rent for the place next year. how much more? too much', 'bad'),
        either(('{name} talked the landlord down to something fair.',
                'talked the landlord down. not all the way, but to something fair', 'good'),
               ("{name} agreed to the higher rent for the place, through gritted teeth.",
                'agreed to the new rent. through gritted teeth. we will manage', 'bad'))), (4, 10),
          positions=OWNER),
    Story('owner_slow_season', 1, 'work', (
        beat("Trade at {name}'s place has gone slow for the season.",
             "it's dead quiet at my place this time of year. I've cleaned everything twice", 'bad'),
        beat("Trade at {name}'s place picked up again after the slow spell.",
             'trade is back at my place!! the slow spell is over. I missed the noise', 'good')), (10, 20),
          positions=OWNER),
    Story('owner_unpaid_tab', 1, 'work', (
        beat("A regular at {name}'s place has run up a tab and keeps not paying it.",
             "one of my regulars has a tab as long as my arm and keeps 'forgetting'", 'bad'),
        either(('The regular at {name}\'s place paid the tab off in full.',
                'the regular paid the whole tab!! with an apology!! miracles happen', 'good'),
               ("{name} wrote off the regular's tab and stopped giving credit at the place.",
                'wrote the tab off. no more credit at my place, for anyone. sorry everyone'))), (4, 10),
          positions=OWNER),
    Story('owner_raise_asked', 1, 'work', (
        beat("One of the staff at {name}'s place asked {name} for a raise.",
             'one of my people asked me for a raise. they deserve it. can I afford it. hmm'),
        either(("{name} gave the raise, and the worker at the place is over the moon.",
                'gave the raise. their face! worth every penny', 'good'),
               ("{name} could not stretch to the raise yet and promised to look again in a few months.",
                "couldn't do the raise yet. told them the truth and promised to look again. hated it"))), (3, 8),
          positions=OWNER),
    # Dramatic: the bigger turns of running a place.
    Story('owner_right_hand', 2, 'work', (
        beat("{name} had a shouting match with the right hand at the place, in front of the staff.",
             'had a shouting match with my right hand at the place. in front of everyone. so that happened',
             'bad'),
        either(("{name} and the right hand at the place cleared the air.",
                "talked it out with my right hand. we're fine. better than before, even", 'good'),
               ("Things between {name} and the right hand at the place are still tense.",
                'things with my right hand are still icy. running a place is fun right now', 'bad'))), (2, 6),
          positions=OWNER),
    Story('owner_offer_to_buy', 2, 'work', (
        beat('Someone made {name} an offer to buy the place.',
             "someone just offered to BUY my place. I didn't even know it was for sale. it isn't. is it?"),
        either(('{name} turned the offer for the place down, and was flattered to be asked.',
                "turned the offer down. it's mine. still, nice to be asked", 'good'),
               ('{name} turned the offer for the place down after a week of lying awake over it.',
                'said no to the offer in the end. a week of no sleep over it. still mine'))), (5, 12),
          positions=OWNER),
    Story('owner_poached_worker', 2, 'work', (
        beat("A rival tried to hire away {name}'s best worker.",
             'a rival just tried to steal my best worker. the nerve. the absolute nerve', 'bad'),
        either(("{name}'s best worker turned the rival down and is staying put.",
                'my best worker turned them down!! told them they like it here. I may cry', 'good'),
               ("{name}'s best worker left for the rival, and {name} is a pair of hands short.",
                'my best worker took the other offer. good luck to them. I mean it. mostly', 'bad'))), (3, 7),
          positions=OWNER),
    Story('owner_expand', 2, 'work', (
        beat('{name} was offered the chance to take on the place next door and grow.',
             "the place next door is going and they asked if I want it. bigger. scarier. tempting"),
        either(('{name} decided the place is the right size as it is.',
                "decided against growing. my place is the right size. I like knowing everyone's name"),
               ('{name} is saving up to take the place next door when the chance comes round again.',
                'not this time. but I am saving for next time. watch this space', 'good'))), (4, 10),
          positions=OWNER),
    # Soap opera: things found and things that won't take no.
    Story('owner_skimming', 3, 'work', (
        beat("{name} found out that someone on the staff has been skimming from the till.",
             "someone at my place has been skimming. one of my own people. I feel sick", 'bad'),
        either(('{name} caught the one who was skimming and let them go.',
                "caught who it was. let them go. they cried. I didn't, until later"),
               ('{name} never found out who was skimming and now counts the till twice a night.',
                "never found out who it was. I count everything twice now. I hate it", 'bad'))), (3, 8),
          positions=OWNER),
    Story('owner_barred_regular', 3, 'work', (
        beat("A regular at {name}'s place keeps hitting on {name}, and it is getting uncomfortable.",
             'one of my regulars keeps hitting on me. at my OWN place. it is getting old', 'bad'),
        beat('{name} barred the regular who would not take no, and he has not been back.',
             'barred him. told him to his face. he has not been back and I feel ten feet tall', 'good')), (2, 5),
          positions=OWNER),
)

MANAGES_PEOPLE = (
    # Quiet: good days with the team.
    Story('lead_team_party', 0, 'work', (
        beat('{name} is throwing a party for the team at work.',
             "throwing a party for my team. they've earned it. I'm buying the first round"),
        beat("The party {name} threw for the team went well, and the team keeps thanking {name} for it.",
             'the team party was a hit. everyone keeps thanking me. I could get used to this', 'good')), (4, 10),
          positions=LEAD),
    Story('lead_good_hire', 0, 'work', (
        beat('{name} hired someone new for the team at work, who turned out to be a natural.',
             "the new person I hired is a natural. trust my gut, I keep telling everyone", 'good'),),
          positions=LEAD),
    Story('lead_target', 0, 'work', (
        beat("{name}'s team at work hit its target for the season.",
             'my team hit our target!! I am so proud of them I could burst', 'good'),), positions=LEAD),
    # Realistic: in the middle.
    Story('lead_cut_team', 1, 'work', (
        beat('{name} was told to cut someone from the team at work.',
             "I've been told to cut someone from my team. I've been staring at the wall all evening", 'bad'),
        either(('{name} argued for the team and kept everyone.',
                'I fought for my team and I WON. everyone stays', 'good'),
               ('{name} had to let one of the team go, and it weighs on {name}.',
                'had to let one of my team go today. worst part of the job, by miles', 'bad'))), (3, 8),
          positions=LEAD),
    Story('lead_caught_between', 1, 'work', (
        beat('{name} is caught between the team and the bosses over a change nobody wants.',
             "stuck between my team and the bosses over a change nobody wants. fun. so fun", 'bad'),
        either(('{name} got the change softened for the team.',
                'got the change softened for my team. small win, but a win', 'good'),
               ('{name} had to push the change through, and the team is sore about it.',
                'had to push the change through. the team is not thrilled with me', 'bad'))), (3, 8),
          positions=LEAD),
    Story('lead_hard_review', 1, 'work', (
        beat('{name} has to give someone on the team a hard review.',
             "I have to give someone on my team a hard review this week. dreading it"),
        either(('The hard review {name} gave went better than {name} feared.',
                'the hard review went better than I feared. they even thanked me', 'good'),
               ('The person {name} reviewed took it badly and has been sulking.',
                'the review went badly. they are sulking. I am also sulking, a bit', 'bad'))), (2, 5),
          positions=LEAD),
    Story('lead_covering', 1, 'work', (
        beat("Someone on {name}'s team is having a rough time, and {name} has been quietly covering for them.",
             "someone on my team is going through it. covering for them quietly. don't tell"),
        beat("The person {name} covered for is back on their feet and thanked {name} for it.",
             'the person I was covering for is doing better. they thanked me. I got a bit choked up', 'good')),
          (5, 12), positions=LEAD),
    Story('lead_fewer_people', 1, 'work', (
        beat('{name} was told to get the same work done with fewer people.',
             "they want the same work out of my team with fewer people. sure. why not. magic", 'bad'),
        beat("{name}'s team got through the month short-handed.",
             'we got through the month short-handed. the team was amazing. I am exhausted')), (10, 20),
          positions=LEAD),
    Story('lead_creep', 3, 'work', (
        beat("A new guy at {name}'s work keeps hitting on {name}, and it is getting uncomfortable.",
             'the new guy at work keeps hitting on me. I run the team he is on. it is getting old', 'bad'),
        either(('{name} told the new guy to knock it off, and he finally backed off.',
                'told the new guy to knock it off. firmly. he actually did', 'good'),
               ('{name} wrote the new guy up, and he has kept his distance since.',
                'wrote the new guy up. he keeps his distance now. good'))), (2, 5),
          positions=LEAD),
    # Dramatic: rivals and feuds.
    Story('lead_not_speaking', 2, 'work', (
        beat("Two people on {name}'s team are not speaking to each other.",
             "two people on my team aren't speaking. I am a manager, not a referee. apparently both", 'bad'),
        either(('{name} sat the two down, and they are civil again.',
                'sat the two of them down. they are civil again. I deserve a medal', 'good'),
               ("{name} split the shifts of the two on the team who still are not speaking.",
                'gave up and split their shifts. peace through scheduling', 'bad'))), (3, 8),
          positions=LEAD),
    Story('lead_passed_over', 2, 'work', (
        beat('{name} was in the running for the top job at work.',
             'I might be in the running for the top job. trying very hard not to want it too much'),
        beat("The top job at {name}'s work went to someone else, and {name} is taking it on the chin.",
             "didn't get the top job. it went to someone else. I'm taking it on the chin. mostly", 'bad')),
          (5, 12), positions=LEAD),
)

# The companion's own staff, in their circle as coworkers: the two coworker stories that read wrong from the one in
# charge ("who am I supposed to eat lunch with", "guess who finishes them") in an owner's words.
STAFF = (
    Story('staff_leaving', 1, 'coworker', (
        beat('{a} told {name} they are leaving the place.',
             "{a} is leaving my place. I'm happy for them. I'm devastated for me", 'bad'),
        beat("{a} worked a last shift at {name}'s place, and {name} gave {a_them} a proper send-off.",
             "{a}'s last shift today. we gave them a proper send-off. it won't be the same")), (5, 12),
          positions=OWNER),
    Story('staff_slacking', 1, 'coworker', (
        beat("{a} keeps leaving jobs half done at {name}'s place.",
             "{a} keeps leaving things half done at my place. time for a talk", 'bad'),
        either(('{name} had a word with {a}, who is pulling their weight at the place now.',
                'had a word with {a}. they took it well and they are doing their share now', 'good'),
               ("{name} is still finishing {a}'s jobs at the place and will have to say more.",
                "still finishing {a}'s jobs. next talk won't be so gentle", 'bad'))), (3, 8),
          positions=OWNER),
)

IN_CHARGE = RUNS_THE_PLACE + MANAGES_PEOPLE + STAFF
