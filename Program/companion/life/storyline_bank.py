"""The rest of the storyline bank (v1.5.0): the stories added to the first nineteen in companion/life/storylines.py.

The first bank was small enough that a long world met the same handful again and again (a tester's world of three
weeks had three storylines). These bring it past a hundred, over the same four drama levels, with a few more people
to be about: any friend, a sibling, a grandparent, a neighbor, and the companion's own days outside work ('self').

How every line here is written, so it reads right everywhere it is told:
- The companion is only ever `{name}` or `{name}'s`, never "they" or "their": the chat context turns those into
  "you" and "your" (storylines.SECOND_PERSON), and Today keeps the name. After `{name}` the verb is in the past, or
  one of "is", "has", "keeps", "was". `{name}` never opens a second sentence.
- The last beat names the companion or the person it is about, so its news is never taken for something the user
  said (tester, 2026-10-29: "the houseplant did not make it").
- Nothing here changes what the app keeps on record about someone (their job, their home, who they are seeing)
  unless it has an entry in MORE_EFFECTS, and nothing is about the companion's own love life.
- No phones, no internet: the same words are told in a city of another era.
- A beat that can go two ways has its odds in companion/world/data/consequences.json (`storyline:<key>:<beat>`).
"""
from companion.life.story_parts import Spent, Story, beat, either

WORK = (
    # Quiet: good days at work.
    Story('work_praise', 0, 'work', (
        beat('{name} got singled out for praise at work.',
             "got praised in front of everyone at work today. I didn't know where to look", 'good'),)),
    Story('work_big_job', 0, 'work', (
        beat('{name} was handed a big job at work, the kind that gets noticed.',
             "they gave me the big job at work. the one everyone wanted. no pressure"),
        either(('The big job at work went well, and {name} got the credit for it.',
                'the big job at work is DONE and it went well. I can sleep again', 'good'),
               ('The big job at work ran late, but {name} got it over the line.',
                'finished the big job at work. late, but finished. never again (I say, every time)'))), (4, 10)),
    Story('work_raise', 0, 'work', (
        beat('{name} asked for a raise at work.', 'I did it. I asked for a raise. now I wait and feel sick'),
        either(('{name} got the raise.', 'I GOT THE RAISE. dinner is on me', 'good'),
               ('{name} was told to ask about the raise again in a few months.',
                "no raise yet. 'ask again in a few months.' fine. I will"))), (3, 8)),
    Story('work_showing_ropes', 0, 'work', (
        beat('{name} was picked to show the new starters the ropes at work.',
             "they picked me to train the new people at work. apparently I'm the responsible one now", 'good'),)),
    Story('work_party', 0, 'work', (
        beat("{name}'s work is throwing a party for everyone, and {name} got roped into organizing it.",
             "somehow I'm organizing the work party. I did not volunteer. I was volunteered"),
        beat("The party at {name}'s work went well, and people keep thanking {name} for it.",
             'the work party was a hit. people keep thanking me. I could get used to this', 'good')), (4, 10)),
    Story('work_thank_you', 0, 'work', (
        beat('Someone {name} helped at work came back just to say thank you.',
             'someone I helped at work came back today just to say thank you. made my whole week', 'good'),)),
    # Realistic: everyday trouble at work.
    Story('work_new_boss', 1, 'work', (
        beat('{name} is getting a new boss at work, and nobody knows what to expect.',
             "we're getting a new boss at work. nobody knows anything. the rumors are wild"),
        either(("{name}'s new boss turned out to be fair and easy to work for.",
                'ok the new boss is actually great?? I was braced for the worst', 'good'),
               ("{name}'s new boss checks on everything twice, and it is wearing thin.",
                'the new boss checks EVERYTHING twice. I am being so patient. so patient', 'bad'))), (4, 9)),
    Story('work_mistake', 1, 'work', (
        beat('{name} made a mistake at work that will take days to put right.',
             "I messed something up at work. badly. it's going to take days to fix", 'bad'),
        either(('{name} put the mistake at work right before it did any harm.',
                'fixed my mess at work before it hurt anyone. I can breathe again', 'good'),
               ('{name} got a talking-to from the manager over the mistake at work.',
                'got a talking-to about the mistake at work. deserved, but ow', 'bad'))), (2, 5)),
    Story('work_short_handed', 1, 'work', (
        beat("{name}'s work is short-handed, and {name} is doing the work of two people.",
             "we're short-handed at work so guess who's doing two jobs. it's me", 'bad'),
        beat("{name}'s work is fully staffed again, and the load is back to normal.",
             "work finally has enough people again. I'm back to doing ONE job. luxury", 'good')), (5, 12)),
    Story('work_contest', 1, 'work', (
        beat('A coworker went after the same assignment as {name}, and it has turned into a quiet contest.',
             "someone at work wants the same assignment I do. we're both being very polite about it"),
        either(('{name} got the assignment at work.', 'the assignment is MINE. politely. graciously. mine', 'good'),
               ("The assignment at {name}'s work went to the coworker.",
                "they gave the assignment to the other person. I'm being a good sport. mostly", 'bad'))), (3, 7)),
    Story('work_review', 1, 'work', (
        beat('{name} has a review coming up at work, and it is weighing on {name}.',
             "I have my review at work coming up and I can't stop thinking about it"),
        either(("{name}'s review at work went well.", "review went well!! all that worrying for nothing", 'good'),
               ("{name}'s review at work was a mixed bag, with a list of things to work on.",
                "review was... mixed. I have 'a list of things to work on.' great"))), (3, 7)),
    Story('work_complaint', 1, 'work', (
        beat('Someone made a complaint about {name} at work.',
             "someone complained about me at work. I've been replaying it in my head all day", 'bad'),
        either(('The complaint about {name} at work was looked into and dropped.',
                'the complaint got dropped. they looked into it and I did nothing wrong. told you', 'good'),
               ('{name} had to apologize over the complaint at work, fair or not.',
                'had to apologize for the complaint thing. through my teeth. but I did it'))), (2, 6)),
    Story('work_new_hours', 1, 'work', (
        beat("{name}'s work wants to change everyone's hours, and nobody is happy about it.",
             "work wants to change everyone's hours. there is a LOT of grumbling. some of it mine", 'bad'),
        either(("{name}'s work dropped the plan to change everyone's hours.",
                'they dropped the new hours plan at work. the grumbling worked!!', 'good'),
               ("The change of hours at {name}'s work was put off until next year.",
                "the hours change at work got put off till next year. I'll take it"))), (4, 10)),
    Story('work_breakdown', 1, 'work', (
        beat("Something important broke down at {name}'s work, and it has been chaos since.",
             "something broke at work and it's been chaos all day. pure chaos", 'bad'),
        beat("Things at {name}'s work are back to normal after the breakdown.",
             "work is back to normal after the great breakdown. I'd almost started to enjoy the chaos", 'good')),
          (2, 5)),
    Story('work_inspection', 1, 'work', (
        beat("{name}'s work has an inspection coming, and everyone is scrambling to get ready.",
             "inspection coming up at work. everyone's scrambling. I have cleaned things I didn't know we had"),
        either(("{name}'s work passed the inspection without a hitch.",
                'we passed the inspection!! not a single problem. I am so relieved', 'good'),
               ("{name}'s work passed the inspection, with a long list of things to fix.",
                'we passed the inspection. with a list of fixes as long as my arm, but we passed'))), (3, 8)),
    # Dramatic: blame, clashes and rumors.
    Story('work_gossip', 2, 'work', (
        beat("Someone at {name}'s work has been spreading gossip about {name}.",
             "someone at work has been talking about me behind my back. I'm so angry I could scream", 'bad'),
        either(('{name} had it out with the coworker behind the gossip, and it stopped.',
                'I confronted the gossip at work. calmly. it has stopped. I am very proud of the calmly part',
                'good'),
               ('The gossip about {name} at work turned out to be a misunderstanding that got out of hand.',
                'the work gossip was a whole misunderstanding. I was ready for war over nothing'))), (2, 6)),
    Story('work_blamed', 2, 'work', (
        beat('{name} was blamed at work for something a coworker did.',
             "I got blamed at work for something I didn't do. I'm furious", 'bad'),
        either(("The truth came out at work, and {name}'s name was cleared.",
                'the truth came out at work. my name is clear. I got an apology and everything', 'good'),
               ('{name} took the blame at work in the end, and the anger has not gone.',
                "I ended up taking the blame at work. easier than fighting it. still angry though", 'bad'))),
          (2, 6)),
    Story('work_boss_clash', 2, 'work', (
        beat('{name} had a heated argument with the boss in front of everyone.',
             'I had a shouting match with my boss. in front of everyone. so that happened', 'bad'),
        either(('{name} and the boss cleared the air after the argument.',
                "talked it out with my boss. we're fine. better than before, even", 'good'),
               ('Things between {name} and the boss are still tense after the argument.',
                'things with my boss are still icy after the argument. work is fun right now', 'bad'))),
          (2, 6)),
    Story('work_changing_hands', 2, 'work', (
        beat("There is talk that {name}'s workplace is about to change hands.",
             'there are rumors work is being sold. nobody will tell us anything', 'bad'),
        either(("The sale of {name}'s workplace fell through; nothing is changing.",
                'the sale at work fell through. everything stays the same. phew', 'good'),
               ("{name}'s workplace changed hands, and so far the days are the same as before.",
                'so work got sold. and so far... nothing has changed? waiting for the catch'))), (5, 12)),
    Story('work_missing_money', 2, 'work', (
        beat("Money went missing at {name}'s work, and everyone is under suspicion.",
             "money went missing at work and now everyone's looking at everyone. it's horrible", 'bad'),
        either(("The missing money at {name}'s work turned up; it had been miscounted.",
                "the missing money at work? miscounted. MISCOUNTED. after all that", 'good'),
               ("Nobody found out who took the money at {name}'s work, and the mood there is sour.",
                'they never found out who took the money at work. nobody trusts anybody now', 'bad'))),
          (3, 8)),
    Story('work_poached', 2, 'work', (
        beat("A rival of {name}'s workplace quietly offered {name} a job.",
             "ok tell no one. a rival of my work just offered me a job. quietly"),
        either(('{name} turned the rival offer down and told nobody at work.',
                "I turned the other job down. didn't tell anyone at work. it's our secret"),
               ('{name} used the rival offer to get better terms, and stayed put.',
                "used the other offer to get a better deal where I am. I'm staying. and smug", 'good'))),
          (3, 7)),
    # Soap opera: things seen and things found.
    Story('work_back_room', 3, 'work', (
        beat('{name} walked in on two coworkers kissing in the back room at work.',
             'I just walked in on two coworkers KISSING in the back room. I can never unsee it'),
        either(('The two coworkers asked {name} to say nothing about the back room, and {name} has kept quiet.',
                "they asked me to keep quiet about the back room. I'm a vault. a very entertained vault"),
               ('Everyone at work found out about the two coworkers anyway, and they think {name} told.',
                "everyone knows about the back room now and they think I told. I didn't!!", 'bad'))), (2, 6)),
    Story('work_the_books', 3, 'work', (
        beat('{name} found out the boss has been fiddling the books at work.',
             "I found something at work I wasn't supposed to. the boss has been fiddling the books", 'bad'),
        either(('{name} reported the boss over the books, and there is an inquiry now.',
                "I reported the boss. there's an inquiry now. my hands are still shaking"),
               ('{name} decided to stay out of the trouble with the books, and it does not sit well.',
                "I'm staying out of the thing with the books. I don't feel good about it", 'bad'))), (3, 8)),
)

COWORKERS = (
    Story('coworker_lunches', 0, 'coworker', (
        beat('{a} and {name} have started having lunch together at work most days.',
             "{a} and I have a standing lunch at work now. best part of the day", 'good'),)),
    Story('coworker_covered', 0, 'coworker', (
        beat('{a} covered for {name} at work when {name} was running behind.',
             '{a} totally saved me at work today. I owe them lunch for a month', 'good'),)),
    Story('coworker_cake', 0, 'coworker', (
        beat('{a} brought a homemade cake in to work, and {name} had three slices.',
             '{a} brought homemade cake to work. I had three slices. no regrets', 'good'),)),
    Story('coworker_slacking', 1, 'coworker', (
        beat('{a} keeps leaving jobs half done at work, and {name} keeps having to finish them.',
             "{a} keeps leaving things half done at work and guess who finishes them", 'bad'),
        either(('{name} had a word with {a}, who is pulling their weight at work now.',
                'had a word with {a}. they took it well!! and they are actually doing their share now', 'good'),
               ("{name} is still picking up {a}'s slack at work.",
                "still doing half of {a}'s job on top of mine. I need to say something", 'bad'))), (3, 8)),
    Story('coworker_rotten_day', 1, 'coworker', (
        beat('{a} had a rotten day at work, and {name} took {a_them} out for a drink afterwards.',
             '{a} had the worst day at work so I took them for a drink after. they needed it', spent=Spent(
                 'after-work-drink', '{name} took {a} out for a drink after a rotten day at work.',
                 '{own} went for a drink with {other} after a rotten day at work.',
                 '{a} had a rotten day at work, and {name} has been looking out for {a_them}.',
                 '{a} had the worst day at work. been looking out for {a_them}', 'social')),)),
    Story('coworker_confided', 1, 'coworker', (
        beat('{a} told {name} in confidence about thinking of quitting.',
             "{a} told me something about work in confidence and now I have to act normal"),
        either(('{a} decided to stay on at work after all, and thanked {name} for listening.',
                "{a} is staying at work after all. I can stop pretending I don't know anything", 'good'),
               ('{a} is still thinking about leaving work, and {name} is keeping it quiet.',
                "{a} still hasn't decided about the work thing. my lips are sealed"))), (4, 10)),
    Story('coworker_blowup', 2, 'coworker', (
        beat('{name} and {a} had a blowup at work and are barely speaking.',
             "{a} and I had a blowup at work. we're barely speaking. it's so uncomfortable", 'bad'),
        either(('{name} and {a} patched things up at work.', "{a} and I patched things up. work is bearable again",
                'good'),
               ('{name} and {a} are still frosty with each other at work.',
                "{a} and I are still frosty. we do a lot of very formal nodding", 'bad'))), (3, 8)),
)

PARENTS = (
    Story('parent_award', 0, 'employed parent', (
        beat("{a}, {name}'s {a_rel}, got an award at work for years of good service.",
             "my {a_rel} just got an award at work and is pretending it's no big deal. it's a big deal", 'good'),)),
    Story('parent_bread', 0, 'parent', (
        beat("{name}'s {a_rel} {a} has started baking bread and is handing loaves out to everyone.",
             'my {a_rel} got into baking bread. I have been given three loaves. send butter', 'good'),)),
    Story('parent_painting', 0, 'parent', (
        beat("{name}'s {a_rel} {a} took up painting and keeps showing {name} every picture.",
             'my {a_rel} took up painting. I have now seen eleven paintings of the same bowl', 'good'),)),
    Story('parent_old_friend', 0, 'parent', (
        beat("{name}'s {a_rel} {a} ran into an old school friend after thirty years and can't stop talking about it.",
             "my {a_rel} ran into a friend from school after THIRTY years. it's all I've heard about", 'good'),)),
    Story('parent_proud', 0, 'parent', (
        beat("{name}'s {a_rel} {a} told {name} how proud the family is of the life {name} has made.",
             "my {a_rel} got all sentimental and said they're proud of me. I'm fine. I'm not crying", 'good'),)),
    Story('parent_recipe', 0, 'parent', (
        beat("{name}'s {a_rel} {a} finally wrote down the family recipe {name} has been asking about for years.",
             'my {a_rel} FINALLY wrote down the family recipe. years of begging. it only took years', 'good'),)),
    Story('parent_raffle', 0, 'parent', (
        beat("{name}'s {a_rel} {a} won first prize in a local raffle.",
             "my {a_rel} won a raffle and is acting like it's a fortune. it's a ham", 'good'),)),
    Story('parent_cough', 1, 'parent', (
        beat("{name}'s {a_rel} {a} has had a cough that won't shift and finally agreed to see a doctor.",
             'my {a_rel} has had this cough for weeks and FINALLY agreed to see a doctor', 'bad'),
        either(("The doctor said {a}'s cough is nothing serious.",
                "{a_rel}'s cough is nothing serious. I can stop nagging now", 'good'),
               ('The doctor told {a} to rest for the cough, and {a} is grumbling about it.',
                '{a_rel} was told to rest for the cough. you can imagine how well that is going'))), (2, 6)),
    Story('parent_advice', 1, 'parent', (
        beat("{name}'s {a_rel} {a} keeps giving {name} advice nobody asked for.",
             'my {a_rel} has Opinions about my life again. so many opinions'),)),
    Story('parent_tight_money', 1, 'parent', (
        beat("{name}'s {a_rel} {a} let slip that money has been tight lately.",
             "my {a_rel} let slip that money's been tight. they'd never have told me on purpose", 'bad'),
        either(("{a}'s money worries eased; it was a bad month, not a bad year.",
                "{a_rel}'s money thing was just a bad month. they're ok. I worry too much", 'good'),
               ('{name} helped {a} out with a bit of money, and made it sound like nothing.',
                "helped my {a_rel} out with some money. made it sound like nothing. it's what you do"))), (4, 10)),
    Story('parent_row', 2, 'parent', (
        beat("{name} and {name}'s {a_rel} {a} had a row about an old family matter.",
             "had a row with my {a_rel}. old family stuff. I don't want to get into it yet", 'bad'),
        either(('{name} and {a} made peace after the row.',
                "made peace with my {a_rel}. we both said sorry. sort of. it counts", 'good'),
               ('{name} and {a} have hardly spoken since the row.',
                "{a_rel} and I still aren't really talking since the row. it's sitting on my chest", 'bad'))),
          (3, 9)),
    # Soap opera: what families keep quiet.
    Story('parent_old_flame', 3, 'parent', (
        beat("{name}'s {a_rel} {a} admitted to nearly leaving the family for someone else, years ago.",
             "my {a_rel} just told me something from years ago that I can't stop thinking about"),
        beat("{name} decided not to bring {a}'s old story up with the rest of the family.",
             "I've decided I'm not telling the family what {a_rel} told me. it's old. let it lie")), (3, 8)),
    Story('parent_will', 3, 'parent', (
        beat("A relative left money in a will, and {name}'s {a_rel} {a} is fighting the rest of the family over it.",
             'a relative left money in a will and now my {a_rel} is at war with half the family', 'bad'),
        either(('{a} and the family settled the will between them.',
                "the will thing is settled. {a_rel} and the family are speaking again. just", 'good'),
               ('The fight over the will has gone to lawyers, and {a} will not back down.',
                "the will fight has gone to lawyers. {a_rel} won't back down. holidays will be fun", 'bad'))),
          (5, 14)),
)

BOTH_PARENTS = (
    Story('parents_anniversary', 0, 'parents', (
        beat("{a} and {b}, {name}'s parents, are planning a party for their wedding anniversary.",
             "my parents are throwing themselves an anniversary party. I've been given jobs", 'good'),
        beat('{a} and {b} had their anniversary party, and {name} gave a toast.',
             "gave a toast at my parents' anniversary. only cried a little", 'good')), (5, 12)),
    Story('parents_dancing', 0, 'parents', (
        beat("{a} and {b}, {name}'s parents, have taken up dancing lessons together.",
             "my parents are taking dancing lessons. together. it's disgustingly sweet", 'good'),)),
    Story('parents_kitchen', 1, 'parents', (
        beat("{a} and {b}, {name}'s parents, are bickering over redoing the kitchen, and both want {name} to take "
             'a side.', "my parents are fighting about redoing the kitchen and both want me on their side. no"),
        either(('{a} and {b} agreed on the kitchen at last.',
                'my parents agreed on the kitchen. I was not consulted. I am thrilled', 'good'),
               ('{a} and {b} gave up on redoing the kitchen altogether.',
                'my parents gave up on the kitchen entirely. all that bickering for nothing'))), (4, 10)),
    Story('parents_big_fight', 2, 'parents', (
        beat("{a} and {b}, {name}'s parents, had a serious fight, and one of them spent the night elsewhere.",
             "my parents had a real fight. one of them slept somewhere else. I've never seen that before", 'bad'),
        either(('{a} and {b} patched things up after the fight.',
                "my parents made up. they're being very nice to each other. almost too nice", 'good'),
               ('Things between {a} and {b} are still tense after the fight.',
                "it's still tense between my parents. I keep checking in on both of them", 'bad'))), (3, 8)),
)

SIBLINGS = (
    Story('sibling_race', 0, 'sibling', (
        beat("{name}'s {a_rel} {a} signed up for a long-distance race and is training every morning.",
             'my {a_rel} signed up for a long race. {a} runs every morning now. who is this person'),
        either(("{a} finished the race, with {name} cheering at the line.",
                '{a} FINISHED THE RACE. I screamed so loud at the finish. so proud', 'good'),
               ("{a} dropped out of the race halfway, and {name} is proud of {a_them} anyway.",
                "{a} didn't finish the race but honestly? halfway is further than I'd get"))), (6, 14)),
    Story('sibling_old_photos', 0, 'sibling', (
        beat("{name}'s {a_rel} {a} found a box of old family photos, and {name} spent the evening going through "
             'it with {a_them}.', "my {a_rel} found a box of old family photos. we went through all of it. the hair",
             'good', Spent('old-photos', '{name} went through a box of old family photos with {a}.',
                           '{own} went through a box of old family photos with {other}.',
                           "{name}'s {a_rel} {a} found a box of old family photos and showed {name} the best ones.",
                           '{a} found a box of old family photos. the hair. oh, the hair')),)),
    Story('sibling_dinner', 0, 'sibling', (
        beat("{name}'s {a_rel} {a} cooked dinner for the whole family for the first time, and it was good.",
             'my {a_rel} cooked for the whole family. first time ever. and it was GOOD?? suspicious', 'good'),)),
    Story('sibling_borrowed', 1, 'sibling', (
        beat("{name}'s {a_rel} {a} borrowed money from {name} and has gone quiet about paying it back.",
             'my {a_rel} borrowed money from me and has gone VERY quiet about it'),
        either(('{a} paid {name} back, every bit of it.', '{a} paid me back!! all of it. faith restored', 'good'),
               ('{a} still has not paid {name} back, and {name} has decided to let it go.',
                "{a} still hasn't paid me back. I'm letting it go. family, you know"))), (5, 12)),
    Story('sibling_decision', 1, 'sibling', (
        beat("{name}'s {a_rel} {a} is stuck on a big decision and keeps asking {name} what to do.",
             "my {a_rel} has a big decision to make and asks me about it hourly. I don't know either!!"),
        either(("{a} took {name}'s advice, and it is working out.",
                '{a} took my advice and it worked out. I will be mentioning this forever', 'good'),
               ('{a} did the opposite of what {name} said, and it is working out anyway.',
                '{a} did the exact opposite of what I said. and it worked. unbelievable'))), (3, 8)),
    Story('sibling_forgot', 1, 'sibling', (
        beat("{name}'s {a_rel} {a} forgot a promise to {name}, and it stung more than expected.",
             'my {a_rel} forgot something they promised me. it stung more than I thought it would', 'bad'),
        beat('{a} made it up to {name} with a proper apology.',
             '{a} apologized. properly. with food. forgiven', 'good')), (2, 5)),
    Story('sibling_argument', 2, 'sibling', (
        beat("{name} and {name}'s {a_rel} {a} had a bitter argument about who does the most for the family.",
             "had a bitter fight with my {a_rel} about family stuff. we both said too much", 'bad'),
        either(('{name} and {a} made up after the argument.',
                "{a} and I made up. we're good. we just needed to yell first, apparently", 'good'),
               ('{name} and {a} are keeping out of each other\'s way since the argument.',
                "{a} and I are avoiding each other since the fight. it's childish. I'm still doing it", 'bad'))),
          (3, 9)),
    Story('sibling_confided', 2, 'sibling', (
        beat("{name}'s {a_rel} {a} told {name} something big and made {name} promise not to tell the family.",
             "my {a_rel} told me something big and swore me to secrecy. I hate knowing things"),
        either(('{a} told the family the news in person, and {name} is off the hook.',
                '{a} told the family themselves. I am FREE. I kept it in the whole time', 'good'),
               ("{name} is still keeping {a}'s news from the family.",
                "still keeping {a}'s secret from the family. every dinner is an obstacle course"))), (4, 10)),
    Story('sibling_family_money', 3, 'sibling', (
        beat("{name} found out {name}'s {a_rel} {a} has quietly been getting money from the family for years.",
             "I just found out my {a_rel} has been getting money from the family for YEARS. quietly", 'bad'),
        either(('{name} had it out with {a} over the money, and {a} said sorry.',
                "had it out with {a} about the money. there was an apology. it's a start"),
               ('{name} and {a} are not speaking over the family money.',
                "{a} and I aren't speaking. over money. I never thought we'd be that family", 'bad'))), (3, 9)),
)

GRANDPARENTS = (
    Story('grandparent_stories', 0, 'grandparent', (
        beat("{name}'s {a_rel} {a} has started telling stories about being young, and {name} is writing them down.",
             "my {a_rel} has started telling stories from way back. I'm writing every one down", 'good'),)),
    Story('grandparent_recipe', 0, 'grandparent', (
        beat("{name}'s {a_rel} {a} is teaching {name} an old family recipe, one step at a time.",
             "my {a_rel} is teaching me the family recipe. there are no measurements. 'you just know'", 'good'),)),
    Story('grandparent_keepsake', 0, 'grandparent', (
        beat("{name}'s {a_rel} {a} gave {name} a keepsake that has been in the family for generations.",
             "my {a_rel} gave me something that's been in the family for generations. I'm scared to touch it",
             'good'),)),
    Story('grandparent_stubborn', 1, 'grandparent', (
        beat("{name}'s {a_rel} {a} refuses any help around the house, and the family is worried.",
             "my {a_rel} won't accept ANY help around the house. the whole family is worried"),
        either(('{a} agreed to a little help around the house, as a favor to {name}.',
                "{a_rel} agreed to a little help. 'as a favor to me.' I'll take it", 'good'),
               ('{a} is still refusing help around the house, and {name} is dropping by more often.',
                "{a_rel} is still refusing help. so I just 'happen to be passing' a lot now"))), (4, 10)),
    Story('grandparent_dizzy', 2, 'grandparent', (
        beat("{name}'s {a_rel} {a} gave the family a scare with a dizzy spell.",
             'my {a_rel} had a dizzy spell and scared all of us half to death', 'bad'),
        either(("The doctor found nothing wrong after {a}'s dizzy spell.",
                "the doctor says {a_rel} is fine. I've aged ten years but {a_rel} is fine", 'good'),
               ('The doctor told {a} to slow down after the dizzy spell, and {a} is not pleased.',
                '{a_rel} has been told to slow down. {a_rel} has Opinions about that'))), (2, 6)),
)

COUSINS = (
    Story('cousin_gathering', 0, 'cousin', (
        beat("{name}'s cousin {a} is organizing a big family get-together.",
             'my cousin {a} is organizing a huge family get-together. there is a seating plan'),
        beat('The family get-together {a} organized went off well, and {name} caught up with everyone.',
             "the family get-together was actually lovely. {a} pulled it off. I've been hugged by forty people",
             'good')), (6, 14)),
    Story('cousin_favor', 1, 'cousin', (
        beat("{name}'s cousin {a} asked {name} for a big favor at very short notice.",
             'my cousin {a} just asked me for a HUGE favor. by tomorrow. of course'),
        either(('{name} came through for {a}, who has not stopped saying thank you.',
                "did the favor for {a}. they won't stop thanking me. it's nice, actually", 'good'),
               ('{name} told {a} no, and it has been a little awkward since.',
                "I told {a} no. it's been a bit awkward since. I still think I was right"))), (2, 6)),
    Story('cousin_dinner_row', 2, 'cousin', (
        beat("{name}'s cousin {a} fell out with half the family over something said at a family dinner.",
             'my cousin {a} said something at a family dinner and now half the family is furious', 'bad'),
        either(('{a} apologized to the family, and things are calming down.',
                '{a} apologized to everyone. the family is calming down. slowly', 'good'),
               ('{a} is digging in, and {name} keeps hearing about it from both sides.',
                "{a} won't apologize. I'm hearing about it from BOTH sides. daily", 'bad'))), (3, 9)),
    Story('cousin_debts', 3, 'cousin', (
        beat("{name}'s cousin {a} ran up debts and is hiding them from the family; {name} is the only one who knows.",
             "my cousin {a} is in money trouble and I'm the only one who knows. I wish I didn't", 'bad'),
        either(('{a} came clean to the family about the debts, and they are helping.',
                "{a} told the family about the debts. they're helping. I can stop holding my breath", 'good'),
               ("{name} is still keeping {a}'s debts from the family.",
                "still keeping {a}'s secret. it's getting heavy", 'bad'))), (4, 10)),
)

NEIGHBORS = (
    Story('neighbor_basket', 0, 'neighbor', (
        beat("{name}'s neighbor {a} left a basket of homemade food at {name}'s door.",
             'my neighbor {a} left a basket of homemade food at my door. for no reason. I love them', 'good'),)),
    Story('neighbor_chats', 0, 'neighbor', (
        beat("{name}'s neighbor {a} has taken to stopping {name} for a chat every morning.",
             'my neighbor {a} catches me for a chat every single morning now. I know everything about the street',
             'good'),)),
    Story('neighbor_racket', 1, 'neighbor', (
        beat("{name}'s neighbor {a} has been making a racket late at night all week.",
             "my neighbor {a} has been making a racket every night this week. I haven't slept", 'bad'),
        either(('{name} had a word with {a} about the noise, and the nights are quiet again.',
                'had a word with {a} about the noise. they were mortified. blessed silence', 'good'),
               ("{a}'s racket is still going, and {name} is out of patience.",
                "{a} is STILL at it every night. I am composing speeches in my head", 'bad'))), (2, 6)),
    Story('neighbor_repair', 1, 'neighbor', (
        beat("{name} and {name}'s neighbor {a} disagree over who should pay for a shared repair.",
             "my neighbor {a} and I are 'discussing' who pays for a repair. politely. for now"),
        either(('{name} and {a} agreed to split the cost of the repair.',
                "{a} and I are splitting the repair. peace on the street", 'good'),
               ('{name} and {a} still have not agreed about the repair, and nothing is fixed.',
                "{a} and I still haven't agreed on the repair. so nothing's fixed. great system", 'bad'))),
          (4, 10)),
    Story('neighbor_accused', 2, 'neighbor', (
        beat("{name}'s neighbor {a} accused {name} of something {name} had nothing to do with.",
             "my neighbor {a} accused me of something I had NOTHING to do with. I'm shaking", 'bad'),
        either(('{a} found out the truth and came to {name} with an apology.',
                '{a} found out it was never me and came round to apologize. accepted. barely', 'good'),
               ('{a} still blames {name} and looks the other way in the street.',
                "{a} still thinks it was me. we pass each other in silence now", 'bad'))), (3, 8)),
    Story('neighbor_stranger', 3, 'neighbor', (
        beat("{name} keeps seeing a stranger slip out of {name}'s neighbor {a}'s place at dawn.",
             "there's a stranger sneaking out of my neighbor {a}'s place at dawn. every day. I have theories"),
        beat("The stranger turned out to be a relative of {a}'s hiding from debts, and {a} begged {name} to say "
             'nothing.', "mystery solved: it's {a}'s relative, hiding from debts. I've been sworn to silence")),
          (3, 8)),
)

FRIENDS = (
    # Quiet: good times with friends.
    Story('friend_contest', 0, 'friend', (
        beat('{a} entered a local contest and asked {name} to come and cheer.',
             '{a} entered a local contest and I have been appointed head of cheering'),
        either(('{a} won the contest, with {name} cheering in the crowd.',
                '{a} WON. I cheered so hard I lost my voice. worth it', 'good'),
               ('{a} did not place in the contest, and had a great night with {name} anyway.',
                "{a} didn't place but we had the best night anyway. robbed, if you ask me"))), (4, 10)),
    Story('friend_finished_story', 0, 'friend', (
        beat('{a} finally finished writing a story years in the making, and {name} was the first to read it.',
             "{a} finished the story they've been writing for YEARS and I got to read it first", 'good'),)),
    Story('friend_thanks', 0, 'friend', (
        beat('{a} thanked {name} for being there through a hard year.',
             '{a} thanked me for being there this year. out of nowhere. I nearly cried', 'good'),)),
    Story('friend_early_mornings', 0, 'friend', (
        beat('{a} talked {name} into exercising together early in the morning.',
             "{a} talked me into early morning exercise. EARLY. I don't know who I am anymore"),
        either(('{name} and {a} are still at the early mornings, and {name} has started to like them.',
                "still doing the early mornings with {a}. I... like it?? don't tell them", 'good'),
               ('{name} and {a} gave up on the early mornings within the week, and laughed about it.',
                '{a} and I lasted four days of early mornings. we are at peace with it'))), (5, 10)),
    Story('friend_bet', 0, 'friend', (
        beat('{name} and {a} made a silly bet, and the loser has to cook dinner.',
             '{a} and I made a bet. loser cooks dinner. I am NOT losing'),
        either(('{name} won the bet, and {a} cooked dinner.',
                'I won the bet. {a} cooked. victory tastes like slightly burnt onions', 'good'),
               ('{name} lost the bet and cooked dinner for {a}.',
                "I lost the bet. I cooked. {a} was unbearable about it"))), (2, 6)),
    Story('friend_long_talk', 0, 'close friend', (
        beat('{name} stayed up late talking with {a}, like old times.',
             'stayed up way too late talking with {a}. like old times. needed that', 'good', Spent(
                 'long-talk', '{name} stayed up late talking with {a}, like old times.',
                 '{own} stayed up late talking with {other}, like old times.',
                 '{name} and {a} had a long catch-up, like old times.',
                 'had the best catch-up with {a}. like old times')),)),
    Story('friend_work_win', 0, 'friend with a job', (
        beat('{a} had a big win at work and took {name} out to celebrate.',
             '{a} had a big win at work and took me out to celebrate. I am a very supportive friend', 'good', Spent(
                 'celebration', "{name} went out with {a} to celebrate {a}'s big win at work.",
                 '{own} went out with {other} to celebrate a big win at work.',
                 '{a} had a big win at work, and {name} is delighted for {a_them}.',
                 '{a} had a big win at work!! so happy for {a_them}', 'social')),)),
    Story('friend_smitten', 0, 'friend seeing someone', (
        beat('{a} cannot stop telling {name} how well things are going with their partner.',
             "{a} is so happy with their partner it's almost annoying. almost. I'm glad for them", 'good'),)),
    # Realistic: everyday friction.
    Story('friend_canceled', 1, 'friend', (
        beat('{a} canceled plans with {name} for the third time in a row.',
             "{a} canceled on me AGAIN. third time. I'm trying not to take it personally", 'bad'),
        either(('{a} apologized for canceling and made it up to {name}.',
                '{a} apologized for all the canceling and made it up to me. ok. forgiven', 'good'),
               ('{a} keeps making excuses, and {name} has stopped doing the asking.',
                "{a} had another excuse. I've stopped asking. ball's in their court", 'bad'))), (3, 8)),
    Story('friend_broke_it', 1, 'friend', (
        beat("{a} borrowed something from {name} and gave it back broken.",
             '{a} borrowed something of mine and gave it back BROKEN. and said nothing', 'bad'),
        either(("{a} replaced what got broken and said sorry to {name}.",
                '{a} replaced the thing they broke. and apologized. faith in humanity restored', 'good'),
               ('{a} shrugged off the breakage, and {name} is still annoyed.',
                "{a} just shrugged about breaking it. I'm annoyed. I'm allowed to be annoyed", 'bad'))), (2, 6)),
    Story('friend_might_move', 1, 'friend', (
        beat('{a} is thinking about moving away, and {name} is trying to be supportive.',
             "{a} is thinking about moving away. I'm being supportive. I hate it"),
        either(('{a} decided to stay, and {name} is more relieved than it shows.',
                "{a} is STAYING. I played it cool. I am not cool. I'm so relieved", 'good'),
               ('{a} put the decision about moving off for now.',
                "{a} has put off deciding about the move. so I get to keep worrying. fine"))), (5, 12)),
    Story('friend_low', 1, 'friend', (
        beat('{a} has been low lately and finally told {name} what is wrong.',
             "{a} has been low for a while and finally told me why. I'm glad they did", 'bad'),
        beat('{a} is doing better and thanked {name} for listening.',
             '{a} is doing a lot better. they thanked me for listening. that is all I did', 'good')), (5, 12)),
    Story('friend_bad_boss', 1, 'friend with a job', (
        beat('{a} is having a hard time with a boss at work and keeps asking {name} what to do.',
             "{a}'s boss is making their life miserable and I'm the advice line. I have no advice", 'bad'),
        either(('{a} stood up to the boss, and work has been easier since.',
                '{a} stood up to their boss!! and it WORKED. I take full credit', 'good'),
               ('{a} is still miserable under the boss, and {name} is still listening.',
                "{a}'s boss is still awful. I'm still listening. it's what I'm for", 'bad'))), (4, 10)),
    Story('friend_couple_fight', 1, 'friend seeing someone', (
        beat('{a} had a big fight with their partner and came to {name} to vent.',
             '{a} had a big fight with their partner. I heard all of it. ALL of it', 'bad'),
        beat('{a} and their partner made up.', "{a} and their partner made up. as you were, everyone", 'good')),
          (2, 6)),
    # Dramatic: trust and money.
    Story('friend_broken_confidence', 2, 'friend', (
        beat('{name} found out {a} repeated something told in confidence.',
             "{a} repeated something I told them in confidence. I found out from someone else", 'bad'),
        either(('{a} owned up and apologized, and {name} is slowly trusting {a_them} again.',
                "{a} owned up and apologized. I'm getting there. trust takes a minute", 'good'),
               ('{name} is keeping {a} at a distance after the broken confidence.',
                "I'm keeping {a} at arm's length for now. I don't know what to tell them anymore", 'bad'))),
          (3, 9)),
    Story('friend_loan', 2, 'friend', (
        beat('{a} asked {name} for a loan, a big one.',
             "{a} asked me for money. a lot of money. I don't know what to do"),
        either(('{name} lent {a} the money.', "I lent {a} the money. please let this not ruin us"),
               ('{name} told {a} no about the loan, and it stung on both sides.',
                "I told {a} no. it was awful. I still think it was right", 'bad'))), (2, 6)),
    Story('friend_black_eye', 2, 'friend', (
        beat("{a} got into a fight on a night out and turned up at {name}'s door with a black eye.",
             '{a} turned up at my door with a BLACK EYE. got into a fight on a night out', 'bad'),
        beat('{a} is healing up and has sworn off nights like that, and {name} is holding {a_them} to it.',
             "{a}'s eye is healing. they've sworn off nights like that. I'm holding them to it", 'good')), (4, 9)),
    Story('friend_pulling_away', 2, 'close friend', (
        beat('{name} noticed {a} has been pulling away for weeks.',
             "{a} has been pulling away from me for weeks. I don't know what I did", 'bad'),
        either(('{a} told {name} what was going on; it had nothing to do with {name}.',
                "{a} finally told me what's been going on. it was never about me. I'm so relieved", 'good'),
               ('{name} and {a} have drifted apart, and nobody is to blame.',
                "{a} and I have drifted. nobody did anything. I just miss how it was", 'bad'))), (4, 10)),
    Story('friend_caught_lying', 2, 'close friend', (
        beat('{name} caught {a} in a lie about last weekend.',
             "I caught {a} lying about where they were last weekend. why would they lie to ME"),
        either(('{a} had been planning a surprise for {name}, and the lie was part of it.',
                "the lie?? {a} was planning a SURPRISE for me. I feel terrible. and loved", 'good'),
               ('{a} will not explain the lie, and {name} has stopped asking.',
                "{a} won't explain. I've stopped asking. it's sitting between us", 'bad'))), (3, 8)),
    # Soap opera.
    Story('friend_strayed', 3, 'friend seeing someone', (
        beat('{a} confessed to {name} about cheating on their partner.',
             "{a} just told me something about their relationship that I really wish I didn't know", 'bad'),
        either(('{a} ended the affair and is saying nothing, and {name} is saying nothing too.',
                "{a} ended it and is telling no one. so I'm telling no one. I hate this", 'bad'),
               ('{a} came clean to their partner, and the two of them are trying to work through it.',
                "{a} came clean. they're trying to work through it. I'm staying out of it"))), (4, 10)),
)

TWO_FRIENDS = (
    Story('friends_get_together', 0, 'two friends', (
        beat('{a} and {b} are throwing a get-together and put {name} in charge of the music.',
             "{a} and {b} are throwing a get-together and I'm in charge of music. power at last", 'good'),
        beat('The get-together {a} and {b} threw went late, and {name} had a great time.',
             "the get-together went SO late. {a} and {b} know how to throw one. I'm wrecked", 'good')), (3, 8)),
    Story('friends_cook_off', 0, 'two friends', (
        beat('{a} and {b} are having a cook-off, and {name} is the judge.',
             '{a} and {b} are having a cook-off and I am the judge. best job I have ever had'),
        either(('{name} gave the cook-off to {a}, and {b} wants a rematch.',
                '{a} won the cook-off. {b} is demanding a rematch. I accept, for the food', 'good'),
               ('{name} gave the cook-off to {b}, and {a} wants a rematch.',
                '{b} won the cook-off. {a} is demanding a rematch. I accept, for the food', 'good'))), (2, 6)),
    Story('friends_surprise', 0, 'two friends', (
        beat('{a} and {b} surprised {name} with a small party for no reason at all.',
             "{a} and {b} threw me a surprise party. for NO reason. I have the best friends", 'good'),)),
    Story('friends_same_evening', 1, 'two friends', (
        beat('{a} and {b} each made plans with {name} for the same evening, and neither will budge.',
             "{a} and {b} both want me the same evening and neither will move. I can't be in two places"),
        either(('{name} talked {a} and {b} into one evening all together.',
                'solved it: {a}, {b} and me, all together. everyone behaved. mostly', 'good'),
               ('{name} went with {a}, and {b} sulked about it for days.',
                "I went with {a}. {b} has been sulking ever since. I can't win"))), (2, 5)),
    Story('friends_owed_money', 2, 'two friends', (
        beat('{a} lent {b} money and wants it back, and {name} keeps hearing both sides.',
             "{a} lent {b} money and wants it back and I'm hearing about it from both of them", 'bad'),
        either(('{b} paid {a} back, and {name} is glad to be out of the middle.',
                "{b} paid {a} back. it's over. I'm out of the middle. thank goodness", 'good'),
               ('{b} still owes {a}, and {name} is tired of being the go-between.',
                "{b} STILL owes {a}. I am so tired of carrying messages", 'bad'))), (4, 10)),
    Story('friends_behind_back', 2, 'two friends', (
        beat("{a} told {name} something unkind {b} said behind {name}'s back.",
             "{a} told me something {b} said about me behind my back. it hurt", 'bad'),
        either(('{b} admitted it and apologized to {name}.',
                "{b} admitted it and said sorry. I'm glad I asked instead of stewing", 'good'),
               ('{b} denied saying it, and {name} is caught between {a} and {b}.',
                "{b} says they never said it. so now I'm stuck between {a} and {b}", 'bad'))), (3, 8)),
    Story('friends_unspoken', 2, 'two single friends', (
        beat('{name} noticed {a} has feelings for {b} and is too nervous to say so.',
             "I'm pretty sure {a} likes {b}. like LIKES. and is saying nothing. it's agony to watch"),
        either(('{a} told {b}, and the two of them are seeing each other now.',
                "{a} finally told {b}. and they're together now!! I knew it", 'good'),
               ('{a} never said a word to {b}, and {name} is staying out of it.',
                "{a} never said anything to {b}. I'm staying out of it. it's killing me"))), (5, 12)),
    Story('friends_party_kiss', 3, 'two single friends', (
        beat('{a} kissed {b} at a party, and each of them swore {name} to secrecy.',
             '{a} and {b} KISSED at a party and both swore me to secrecy. separately'),
        either(('{a} and {b} are seeing each other now, and {name} can stop pretending not to know.',
                "{a} and {b} are together now. I can finally stop pretending I don't know", 'good'),
               ('{a} and {b} are both pretending the kiss never happened, with {name} stuck in the middle.',
                '{a} and {b} are pretending it never happened. I am pretending with them. exhausting'))),
          (3, 9)),
    Story('friends_scene', 3, 'two friends', (
        beat('{a} and {b} had a screaming match at a party, in front of {name} and everyone else.',
             '{a} and {b} had a SCREAMING match at a party. in front of everyone. I wanted to disappear', 'bad'),
        either(('{a} and {b} made up after the scene at the party, and {name} is relieved.',
                "{a} and {b} made up. I'm so relieved. no more parties for a while though", 'good'),
               ('{a} and {b} are not speaking since the party, and {name} is seeing them separately.',
                "{a} and {b} aren't speaking. I'm seeing them separately. double the plans", 'bad'))), (3, 9)),
)

OWN_DAYS = (
    # The companion's own days outside work: true for anyone, with or without a job.
    Story('own_found_money', 0, 'self', (
        beat('{name} found forgotten money in the pocket of an old coat.',
             "found money in an old coat pocket. it's the best kind of money", 'good'),)),
    Story('own_compliment', 0, 'self', (
        beat('A stranger paid {name} a compliment that has stuck all week.',
             "a stranger gave me a compliment days ago and I'm STILL thinking about it", 'good'),)),
    Story('own_keepsakes', 0, 'self', (
        beat('{name} found a box of old keepsakes while tidying up and lost a whole afternoon to it.',
             'found a box of my old keepsakes while tidying. lost the whole afternoon. no tidying occurred',
             'good'),)),
    Story('own_fundraiser', 0, 'self', (
        beat('{name} signed up to help at a local fundraiser.',
             "I signed up to help at a local fundraiser. I'm told there will be bunting", 'good'),
        beat('The fundraiser {name} helped at brought in more than anyone hoped.',
             'the fundraiser brought in way more than anyone hoped!! my feet hurt and I am happy', 'good')), (4, 10)),
    Story('own_big_cook', 0, 'self', (
        beat('{name} tried cooking something ambitious for the first time, and it came out well.',
             'tried cooking something way above my level and it came out WELL. I am a genius', 'good'),)),
    Story('own_stray_cat', 0, 'self', (
        beat("A stray cat has started waiting at {name}'s door every evening.",
             "there's a stray cat waiting at my door every evening now. I have been chosen"),
        either(("The cat at {name}'s door turned out to have an owner two streets over, who came for it.",
                "the cat had an owner all along. they came for it. I'm happy for the cat. I'm fine"),
               ("A neighbor took in the cat from {name}'s door, and it still comes by to visit.",
                'a neighbor took the cat in! it still visits me. best of both worlds', 'good'))), (4, 10)),
    Story('own_locked_out', 1, 'self', (
        beat('{name} got locked out at home and had to wait hours to get back in.',
             'locked myself out. sat on the step for HOURS. I have had time to think about my choices', 'bad'),)),
    Story('own_lost_book', 1, 'self', (
        beat('{name} left a favorite book on a bench somewhere in town.',
             'I left my favorite book on a bench somewhere and I am devastated', 'bad'),
        either(("{name}'s book turned up; someone had handed it in.",
                'MY BOOK. someone handed it in. people are good. I take back everything', 'good'),
               ("{name}'s book never turned up, and {name} has given up looking.",
                "the book is gone for good. I've stopped looking. I hope whoever has it loves it", 'bad'))),
          (2, 6)),
    Story('own_overcharged', 1, 'self', (
        beat('{name} was overcharged at a shop and went back to argue about it.',
             'got overcharged at a shop. went back to argue. I had a speech prepared and everything'),
        either(('{name} got the money back from the shop, with an apology.',
                'got my money back AND an apology. the speech worked', 'good'),
               ('{name} got nowhere with the shop and swore never to go back.',
                'got nowhere with the shop. I am never going back. they will feel my absence', 'bad'))), (1, 4)),
    Story('own_double', 1, 'self', (
        beat('{name} keeps getting mistaken for someone else around town, and it is getting strange.',
             "people keep mistaking me for someone else around town. three times this week. it's getting weird"),
        either(("{name} finally met the lookalike, and there was a lot of laughing.",
                'I MET MY DOUBLE. we just stood there laughing. it was like a strange mirror', 'good'),
               ('{name} never found out who the lookalike is, and the mix-ups have stopped.',
                "never did find my double. the mix-ups have stopped. I'm a little disappointed"))), (3, 9)),
    Story('own_shouting_match', 1, 'self', (
        beat('{name} got into a shouting match with a stranger over nothing, and it has been embarrassing to '
             'think about since.', "I got into a shouting match with a stranger. over NOTHING. I'm so embarrassed",
             'bad'),)),
    Story('own_street_accident', 2, 'self', (
        beat("{name} came upon a stranger's accident in the street and stayed until help came.",
             "someone had an accident in the street right in front of me. I stayed till help came. I'm still shaky",
             'bad'),
        beat('The stranger {name} helped in the street is on the mend and sent word of thanks.',
             "the person from the accident is on the mend. they sent word to thank me. I'm so relieved", 'good')),
          (3, 8)),
    Story('own_old_quarrel', 2, 'self', (
        beat('Someone {name} fell out with years ago is back in town and asking after {name}.',
             "someone I fell out with years ago is back in town. and asking about me. I don't know how I feel"),
        either(('{name} met the old acquaintance, and the quarrel was put to rest.',
                "I met them. we talked. it's put to rest, after all these years. I feel lighter", 'good'),
               ('{name} has kept out of the way of the old acquaintance, who has left town again.',
                "I kept out of their way and now they've left again. maybe that's for the best"))), (3, 9)),
    Story('own_rumor', 2, 'self', (
        beat('A rumor has been going around the neighborhood about {name}.',
             "there's a rumor going around the neighborhood about ME. it isn't even a good one", 'bad'),
        either(('The rumor about {name} died down as fast as it started.',
                'the rumor died down. people found something else to talk about. bless them', 'good'),
               ('{name} tracked the rumor to its source and set it straight, face to face.',
                'I found out who started the rumor and set them straight. face to face. it felt great', 'good'))),
          (3, 8)),
    Story('own_notes', 3, 'self', (
        beat("Someone has been leaving unsigned notes at {name}'s door.",
             "someone keeps leaving unsigned notes at my door. I can't decide if it's sweet or sinister"),
        either(("The notes at {name}'s door turned out to be meant for a neighbor all along.",
                'the notes were for my NEIGHBOR. wrong door this whole time. I feel robbed'),
               ("The notes at {name}'s door stopped as suddenly as they started; {name} never found out who "
                'wrote them.', "the notes just stopped. I never found out who. it's going to bother me forever"))),
          (4, 10)),
    Story('own_inheritance', 3, 'self', (
        beat('{name} got a letter about an inheritance from a relative {name} barely knew.',
             'I got a letter about an INHERITANCE. from a relative I barely knew. what is my life'),
        either(("{name}'s inheritance came through, a small sum and an old clock.",
                "the inheritance came through. a little money and an old clock. I love the clock", 'good'),
               ("{name}'s inheritance is tied up; a stranger claiming to be family is contesting it.",
                'someone claiming to be family is contesting the inheritance. of course. OF COURSE', 'bad'))),
          (5, 14)),
)

MORE = WORK + COWORKERS + PARENTS + BOTH_PARENTS + SIBLINGS + GRANDPARENTS + COUSINS + NEIGHBORS + FRIENDS + \
    TWO_FRIENDS + OWN_DAYS

# What these beats do to the people in them (companion/life/happenings.py), as storylines.EFFECTS has them.
MORE_EFFECTS = {
    ('friends_unspoken', 1, 0): ('together', 'ab'), ('friends_party_kiss', 1, 0): ('together', 'ab'),
    ('friends_scene', 0, 0): ('fell_out', 'ab'), ('friends_scene', 1, 0): ('made_up', 'ab'),
    ('friends_scene', 1, 1): ('not_speaking', 'ab'),
}
