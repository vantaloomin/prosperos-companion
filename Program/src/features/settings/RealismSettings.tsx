import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { SETTINGS_KEY, useWorkspaceSettings } from '../../companion'
import type { ChatList, Closeness as ClosenessState, WorkspaceSettings } from '../../types'
import { CHATS_KEY } from '../chats/useChats'
import { CLOSENESS_KEY } from '../memories/closenessText'
import { ClosenessRows } from '../memories/Closeness'
import { firstName } from '../watch/watchText'
import { DRAMA_LEVELS } from '../today/storyText'
import { LOOKS_LEVELS } from '../character/looksLatelyText'
import { KITCHEN_LEVELS } from '../character/kitchenText'
import { WORK_LEVELS } from '../character/workText'
import { MEDIA_LEVELS } from '../character/mediaText'
import { HOBBY_LEVELS } from '../character/hobbiesText'
import { ONWARD_LEVELS, TOGETHER_LEVELS } from '../conversation/whereText'
import { ROUGH_PATCH_LEVELS } from '../profile/roughPatchText'
import { PACE_LEVELS } from '../character/stepsText'
import { BREAKUPS_HINT } from '../character/breakupText'
import { LOVE_LIFE_LEVELS } from '../character/loveLifeText'
import { FAMILY_LEVELS, FAMILY_LIFE_LEVELS, FAMILY_SHAPES_LEVELS } from '../character/familiesText'
import { TURN_LEVELS } from '../character/turnsText'
import { LOSS_LEVELS, PASS_AWAY_HINT, PASS_AWAY_TIP } from '../character/lossText'
import { INNER_VOICE_LEVELS } from '../watch/watchText'
import { LOOK_LEVELS, LOOK_TIP } from '../character/theirLookText'
import { WAKING_LEVELS } from '../character/theirHoursText'
import { READ_LEVELS, READ_TIP } from './readPaceText'
import { POLITICS_LEVELS, POLITICS_TIP } from '../today/politicsText'
import { TROLL_LEVELS, TROLLS_TIP } from '../feed/trollsText'
import { Notice } from '../../components/Feedback'
import { SettingRow, SliderRow, SwitchRow } from '../../components/Rows'
import { ErrorNotice } from '../../components/ErrorNotice'
import { SectionPending } from '../../components/SectionPending'
import { useLifeSettings, type SaveResult } from './useLifeSettings'
import { RealismPresets } from './RealismPresets'
import { useWorlds } from '../worlds/useWorlds'

/** Life admin (companion/life/admin.py) on the home features' shared scale: how much of the boring stuff fills their weeks. */
const ADMIN_LEVELS = [
  { label: 'Off', hint: 'No appointments, errands or paperwork of their own.' },
  { label: 'Light', hint: 'Only what comes due: the dentist, taxes, the lease. Nothing gets put off, no surprise bills, and anything moves for plans with you.' },
  { label: 'True to life', hint: 'What comes due, plus an errand or some paperwork most weeks. Now and then a chore gets put off, never past its deadline. The dentist and the vet keep their time; you can still move them.' },
  { label: 'Dramatic', hint: 'Errands and paperwork every week, and surprises like a parking ticket or a bank mix-up to sort out. Anything due that day holds too.' },
]

/** Group chat guests (companion/group_guests.py PULL_CHANCE): how often someone named in a group chat is brought in. */
const GUEST_LEVELS = [
  { label: 'Only when you add them', hint: 'Nobody joins a group chat on their own. You can still add anyone the group knows from People in this group.' },
  { label: 'Now and then', hint: 'Once in a while, when a friend, relative or familiar face comes up in a group chat, whoever knows them brings them in for a bit. Every few days at most.' },
  { label: 'True to life', hint: 'When someone comes up in a group chat, whoever knows them sometimes brings them in for a while. Guests slip out once the chat goes quiet; one who keeps coming back stays.' },
  { label: 'Often', hint: 'Friends, family and familiar faces get pulled into group chats often, a few times a day at most.' },
]

/** Memes and GIFs (companion/images/photos.py MEME_LEVELS): how often memes come unasked. Pictures nobody asked for stay a few a day. */
const MEME_LEVELS = [
  { label: 'Never', hint: 'No memes or GIFs, even when you ask. They answer in words.' },
  { label: 'Now and then', hint: 'A meme when you ask, and once in a while one to cheer you up when you sound down.' },
  { label: 'True to life', hint: 'A meme or a GIF when you ask, and often one when you sound bored or down. A few pictures a day at most.' },
  { label: 'Often', hint: 'Memes come often when you sound down, and now and then out of the blue. Still a few pictures a day at most.' },
]

/** Weather (companion/world/skies.py): how the city's climate comes in spells. There is no Off: the climate is always
 * there. Kept in this world only, like its drama. */
const WEATHER_LEVELS = [
  { label: 'Gentle', hint: 'Weather changes every day or two. Storms are rare, and snow comes lightly.' },
  { label: 'True to life', hint: "Rain, fog or sunshine settles in for a few days at a time, as the city's climate has it, with storms and snow in their season." },
  { label: 'Stormy', hint: 'Long wet spells, more storms, and more snow in winter.' },
]

/** The top of Settings > Realism: one segmented control of presets; picking one moves the sliders below. */
export function RealismIntro() {
  return <RealismPresets heading="presets-heading" title="Start from" compact />
}

/** A switch's longer explanation and its rule in one tip, since rows carry no paragraph. */
const both = (hint: string, tip?: string) => (tip ? `${hint} ${tip}` : hint)

/** How much drama, their pace and plans that go off course. Drama is this world's own (companion/life/world_drama.py). */
export function PaceSettings({ name }: { name: string }) {
  const { settings, data, save, result } = useLifeSettings()
  const world = useWorlds().data?.world.name
  if (!data) return <SectionPending queries={[settings]} heading="pace-heading" title="Their days" />
  const alone = data.alone && name ? ` ${name} is the only companion here, so a little more happens to them.` : ''
  return (
    <section className="row-group" aria-labelledby="pace-heading">
      <h2 id="pace-heading" className="visually-hidden">Their days</h2>
      <h3 className="row-group-label">Their life</h3>
      <div className="row-list">
        <SliderRow label={`Drama in ${world ?? 'this world'}`} levels={DRAMA_LEVELS} fallback={1} value={data.drama} onChange={(drama) => void save({ drama })}
          tip={`Only this world. Each of your worlds keeps its own drama level.${alone}`} />
        <SliderRow label={`Weather in ${world ?? 'this world'}`} levels={WEATHER_LEVELS} fallback={1} value={data.weather_realism} onChange={(weather_realism) => void save({ weather_realism })}
          tip={'Only this world, from tomorrow on. Their plans follow the weather, so a stormy day keeps them in.\n\nIn a real city, turning on their weather in World > Real-world lookups uses the real weather instead.'} />
        <SliderRow label="Their looks change" levels={LOOKS_LEVELS} value={data.looks_realism} onChange={(looks_realism) => void save({ looks_realism })}
          tip="Only looks the app picked change. Anything you wrote about how someone looks stays exactly as you wrote it." />
        <SliderRow label="Work life" levels={WORK_LEVELS} value={data.work_realism} onChange={(work_realism) => void save({ work_realism })} />
        <SliderRow label="Life's big turns" levels={TURN_LEVELS} value={data.life_turns} onChange={(life_turns) => void save({ life_turns })}
          tip="Undo any big turn on Today, or make it go another way under Hidden values." />
        <SwitchRow label="People can pass away" checked={data.people_pass_away} onChange={(value) => void save({ people_pass_away: value })} tip={both(PASS_AWAY_HINT, PASS_AWAY_TIP)}>
          <SliderRow nested label="Loss" levels={LOSS_LEVELS} value={data.loss} onChange={(loss) => void save({ loss })} />
        </SwitchRow>
        <SliderRow label="Their pastimes" levels={HOBBY_LEVELS} value={data.hobbies_realism} onChange={(hobbies_realism) => void save({ hobbies_realism })}
          tip="Pastimes from their interests, and ones you add, are never given up on their own." />
        <SliderRow label="Reading, watching, listening" levels={MEDIA_LEVELS} value={data.media_realism} onChange={(media_realism) => void save({ media_realism })} />
        <SwitchRow label="Let their days go off plan" checked={data.day_shifts} onChange={(value) => void save({ day_shifts: value })}
          tip="Now and then they run late, stay late, have plans fall through, have something come up or get a surprise visit. Rolled with fixed dice, so a day never changes after the fact. Off: every day goes as planned." />
      </div>
      <h3 className="row-group-label">People around them</h3>
      <div className="row-list">
        <SliderRow label="Getting together" levels={TOGETHER_LEVELS} value={data.together_realism} onChange={(together_realism) => void save({ together_realism })}
          tip="You can always ask them over or out yourself, and say not now when someone knocks." />
        <SliderRow label="Moving on" levels={ONWARD_LEVELS} value={data.onward_realism} onChange={(onward_realism) => void save({ onward_realism })}
          tip="You can always keep them where they are with Stay longer, or ask to go on somewhere yourself." />
        <SliderRow label="Their love life" levels={LOVE_LIFE_LEVELS} value={data.love_life} onChange={(love_life) => void save({ love_life })}
          tip="Anyone they start seeing joins the people in their life. You can remove them there, or undo it on Today. Someone in a relationship with you only sees other people in an open relationship, or in secret on Drama." />
        <SliderRow label="Growing families" levels={FAMILY_LEVELS} value={data.growing_families} onChange={(growing_families) => void save({ growing_families })}
          tip="Babies and children are only ever mentioned in words, never pictured. Town babies show up in the paper." />
        <SliderRow label="Family life" levels={FAMILY_LIFE_LEVELS} value={data.family_life} onChange={(family_life) => void save({ family_life })}
          tip="Your own children with them, once you two have one. Children are only ever mentioned in words, never pictured." />
        <SliderRow label="Family shapes" levels={FAMILY_SHAPES_LEVELS} value={data.family_shapes} onChange={(family_shapes) => void save({ family_shapes })}
          tip="Change anyone in their family on Today > People." />
        <SliderRow label="Local politics" levels={POLITICS_LEVELS} value={data.politics_realism} onChange={(politics_realism) => void save({ politics_realism })} tip={POLITICS_TIP} />
        <SliderRow label="Trolls and snark on posts" levels={TROLL_LEVELS} fallback={1} value={data.trolls_realism} onChange={(trolls_realism) => void save({ trolls_realism })} tip={TROLLS_TIP} />
        <SliderRow label="Guests in group chats" levels={GUEST_LEVELS} value={data.guests_realism} onChange={(guests_realism) => void save({ guests_realism })} />
      </div>
      <h3 className="row-group-label">In chat</h3>
      <div className="row-list">
        <SliderRow label="Memes and GIFs" levels={MEME_LEVELS} value={data.memes_realism} onChange={(memes_realism) => void save({ memes_realism })}
          tip="Memes need no image backend. Reaction GIFs need your own GIPHY key, in Settings > Pictures." />
        <SliderRow label="Their look in chat" levels={LOOK_LEVELS} value={data.their_look} onChange={(their_look) => void save({ their_look })} tip={LOOK_TIP} />
        <SliderRow label="Inner voice" levels={INNER_VOICE_LEVELS} value={data.inner_voice} onChange={(inner_voice) => void save({ inner_voice })}
          tip="What the Watching page tells while you just watch a world. Feelings come through in words; numbers show only with Hidden values on." />
        <SwitchRow label="Reply at their own pace" checked={data.paced_replies} onChange={(value) => void save({ paced_replies: value })}
          tip={'When a companion is busy they decide how to answer: later, a quick holding text first, or a short note now. Asleep, they answer when they wake, unless a second text, "wake up" or a call wakes them. In group chats, each reply shows after the time it would take to read and type it. Off: busy companions answer right away too.'}>
          <SliderRow nested label="Waking them" levels={WAKING_LEVELS} value={data.waking_realism} onChange={(waking_realism) => void save({ waking_realism })}
            tip="A companion in another time zone can live on your clock instead: the switch is on their Character page." />
        </SwitchRow>
        <SliderRow label="How quickly they read your texts" levels={READ_LEVELS} value={data.read_pace} onChange={(read_pace) => void save({ read_pace })} tip={READ_TIP} />
      </div>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

/** Love and friendship (companion/life/steps.py): how soon companions bring up the next step, whether a close
 * friend can fall for you, rough patches and breakups. */
export function LoveSettings() {
  const { settings, data, save, result } = useLifeSettings()
  if (!data) return <SectionPending queries={[settings]} heading="love-heading" title="Love and friendship" />
  return (
    <section className="row-group" aria-labelledby="love-heading">
      <div className="row-list">
        <SliderRow label="Relationship pace" levels={PACE_LEVELS} value={data.steps_pace} onChange={(steps_pace) => void save({ steps_pace })} />
        <SwitchRow label="Friends can fall for you" checked={data.friends_fall} onChange={(value) => void save({ friends_fall: value })}
          tip="Now and then a close friend falls for you and tells you. Say yes and you start dating; say no and the friendship carries on after a few awkward days. Rare on a real life, likelier with more drama. Keep a friend as just friends on their Character page." />
        {/* Next to Breaks and breakups, which needs rough patches at true to life or more (Iris). */}
        <SliderRow label="Rough patches" levels={ROUGH_PATCH_LEVELS} value={data.rough_patches_realism} onChange={(rough_patches_realism) => void save({ rough_patches_realism })}
          tip="You can always clear the air yourself. Companions can be the ones at fault too, and then they apologise first." />
        <SwitchRow label="Breaks and breakups" checked={data.breakups} onChange={(value) => void save({ breakups: value })}
          tip={both(BREAKUPS_HINT, 'Either of you can end it, and getting back together is possible later. Nothing is deleted.')} />
      </div>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

/** Around the home: one slider for each home feature (Vanta, 2026-10-13), each its own life setting. */
export function HomeLifeSettings() {
  const { settings, data, save, result } = useLifeSettings()
  if (!data) return <SectionPending queries={[settings]} heading="home-life-heading" title="Around the home" />
  return (
    <section className="row-group" aria-labelledby="home-life-heading">
      <div className="row-list">
        <SliderRow label="Housework" levels={UPKEEP_LEVELS} value={data.upkeep_realism} onChange={(upkeep_realism) => void save({ upkeep_realism })} />
        <SliderRow label="Kitchen" levels={KITCHEN_LEVELS} value={data.kitchen_realism} onChange={(kitchen_realism) => void save({ kitchen_realism })} />
        <SliderRow label="Pets" levels={PET_LEVELS} value={data.pets_realism} onChange={(pets_realism) => void save({ pets_realism })} />
        <SwitchRow nested label="Pets can die" checked={data.pets_can_die} disabled={data.pets_realism === 0} onChange={(value) => void save({ pets_can_die: value })}
          tip="Rarely, and only late in life: of old age, or a serious illness when they are very old. Off: pets still grow old but are always there. A pet that died can be brought back on the Character page." />
        <SliderRow label="Life admin" levels={ADMIN_LEVELS} value={data.admin_realism} onChange={(admin_realism) => void save({ admin_realism })} />
      </div>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

/** The Housework slider's steps (companion/life/upkeep.py SCALE). */
const UPKEEP_LEVELS = [
  { label: 'Off', hint: 'Laundry, dishes and clutter never come up. Their place stays as it is.' },
  { label: 'Light', hint: 'Mess builds slowly and they deal with it early. A tidy, easy home.' },
  { label: 'True to life', hint: 'Laundry, dishes and clutter build up with their week, and they catch up the way their habit says, with a big clean on a day off.' },
  { label: 'Messy', hint: 'More mess, piling up longer, and big cleans that wait until the place is a real mess.' },
]

/**
 * Closeness for any companion, picked from a list that starts on the open one (picking never changes the open chat):
 * Set it to, Never closer than, steps, Keep it at and gentle cooling. Nickname, running jokes and Start over stay
 * with the stages in Memories.
 */
export function ClosenessSettings({ name }: { name: string }) {
  const chats = useQuery({ queryKey: CHATS_KEY, queryFn: () => api<ChatList>('/chats') })
  const companions = (chats.data?.chats ?? []).filter((chat) => chat.kind === 'companion')
  const [picked, setPicked] = useState('')
  const [filter, setFilter] = useState('')
  const chosen = companions.find((chat) => chat.id === picked) ?? companions.find((chat) => chat.focus) ?? companions[0]
  const words = filter.trim().toLowerCase()
  const shown = companions.filter((chat) => chat.id === chosen?.id || chat.name.toLowerCase().includes(words))
  return (
    <section className="row-group" aria-labelledby="closeness-settings-heading">
      {companions.length > 1 && <div className="row-list">
        {companions.length > SEARCH_FROM && <SettingRow label="Find a companion">
          {(id) => <input id={id} type="search" autoComplete="off" value={filter} maxLength={60} onChange={(event) => setFilter(event.target.value)} />}
        </SettingRow>}
        <SettingRow label="Companion" tip="Shows their closeness here. Your open chat stays as it is.">{(id) => (
          <select id={id} value={chosen?.id ?? ''} onChange={(event) => setPicked(event.target.value)}>
            {shown.map((chat) => <option key={chat.id} value={chat.id}>{chat.name}</option>)}
          </select>
        )}</SettingRow>
      </div>}
      {chosen ? <CompanionCloseness key={chosen.id} id={chosen.id} name={chosen.name} open={chosen.focus} /> : <CompanionCloseness id="" name={name} open />}
    </section>
  )
}

/** More companions than this and the picker gets a search box (100+ companions are supported). */
const SEARCH_FROM = 8

function CompanionCloseness({ id, name, open }: { id: string; name: string; open: boolean }) {
  const client = useQueryClient()
  const path = id ? `/closeness?companion=${encodeURIComponent(id)}` : '/closeness'
  const key = [...CLOSENESS_KEY, id]
  const closeness = useQuery({ queryKey: key, queryFn: () => api<ClosenessState>(path) })
  const [result, setResult] = useState<SaveResult>(null)
  const change = async (action: () => Promise<ClosenessState>, done: string) => {
    try {
      client.setQueryData(key, await action())
      setResult({ tone: 'info', text: done })
    } catch (error) {
      setResult({ tone: 'error', text: error instanceof Error ? error.message : 'Not saved.' })
    }
    // Memories shows the open companion's stages from its own copy.
    void client.invalidateQueries({ queryKey: CLOSENESS_KEY, exact: true })
  }
  if (closeness.isError) return <ErrorNotice error={closeness.error} />
  if (!closeness.data) return null
  return (
    <div className="row-group">
      <ClosenessRows name={name} state={closeness.data} change={change} path={path} />
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
      {open
        ? <p className="subtle">Nickname, running jokes and starting over are in <a className="inline-link" href="#memories">{firstName(name)}&apos;s Memories</a>.</p>
        : <p className="subtle">Nickname, running jokes and starting over are in {firstName(name)}&apos;s Memories, once their chat is open.</p>}
    </div>
  )
}

/** The adult side of life (companion/world/intimacy.py): off until turned on, adults only, private to each person. */
export function AdultSideSettings() {
  const client = useQueryClient()
  const settings = useWorkspaceSettings()
  const [error, setError] = useState('')
  const save = async (adult_side: boolean) => {
    setError('')
    try {
      client.setQueryData(SETTINGS_KEY, await api<WorkspaceSettings>('/settings', { adult_side }, 'PUT'))
      void client.invalidateQueries({ queryKey: ['townsfolk'] })
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'That setting was not saved.') }
  }
  return (
    <section className="row-group" aria-labelledby="adult-side-heading">
      <div className="row-list">
        <SwitchRow label="Give adults an adult side" checked={settings.data?.adult_side === true} disabled={!settings.data} onChange={(checked) => void save(checked)}
          tip="Every adult townsperson and companion gets who they're drawn to, how adventurous they are, their drive and a few things they're into, rolled by the app. Adults only: nobody under 18 ever gets one. It stays private to each person and only shapes them when romance or intimacy comes up. It never goes into pictures, the town paper or the feed. Change a companion's on their Character page, under Life details. Hidden values can show what townsfolk are like this way." />
      </div>
      {error && <Notice tone="error">{error}</Notice>}
    </section>
  )
}

/** How much happens to pets (companion/life/pets.py), from nothing at all to a dramatic life. */
const PET_LEVELS = [
  { label: 'Off', hint: 'Pets stay well: no off days, vet visits or losses.' },
  { label: 'Light', hint: 'Now and then a pet has an off day or a checkup. Short spells and few vet visits.' },
  { label: 'True to life', hint: 'Off days, vet visits and checkups about as often as real pets have them, more as they grow old.' },
  { label: 'Dramatic', hint: 'More illnesses and longer spells, so more vet visits and more vet bills.' },
]
