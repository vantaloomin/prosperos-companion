import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api'
import { SETTINGS_KEY, useWorkspaceSettings } from '../../companion'
import type { ChatList, Closeness as ClosenessState, WorkspaceSettings } from '../../types'
import { CHATS_KEY } from '../chats/useChats'
import { CLOSENESS_KEY } from '../memories/closenessText'
import { StageControls } from '../memories/Closeness'
import { DRAMA_LEVELS } from '../today/storyText'
import { LOOKS_LEVELS } from '../character/looksLatelyText'
import { KITCHEN_LEVELS } from '../character/kitchenText'
import { WORK_LEVELS } from '../character/workText'
import { MEDIA_LEVELS } from '../character/mediaText'
import { HOBBY_LEVELS } from '../character/hobbiesText'
import { TOGETHER_LEVELS } from '../conversation/whereText'
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
import { Notice } from '../../components/Feedback'
import { Field, TextInput, Toggle } from '../../components/Fields'
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

/** The top of Settings > Realism: Iris's opening line and one-tap presets for the world-wide settings below. */
export function RealismIntro() {
  return (
    <>
      <p className="subtle settings-intro">How true to life the world is. Everything here can be changed back any time.</p>
      <RealismPresets heading="presets-heading" title="Start from" />
    </>
  )
}

/** How much drama, their pace and plans that go off course: world-wide settings, so they come first. */
export function PaceSettings() {
  const { settings, data, save, result } = useLifeSettings()
  const world = useWorlds().data?.world.name
  if (!data) return <SectionPending queries={[settings]} heading="pace-heading" title="Their days" />
  const level = step(DRAMA_LEVELS, data.drama, 1)
  const looks = step(LOOKS_LEVELS, data.looks_realism, 2)
  const work = step(WORK_LEVELS, data.work_realism, 2)
  const guests = step(GUEST_LEVELS, data.guests_realism, 2)
  const media = step(MEDIA_LEVELS, data.media_realism, 2)
  const pastimes = step(HOBBY_LEVELS, data.hobbies_realism, 2)
  const memes = step(MEME_LEVELS, data.memes_realism, 2)
  const voice = step(INNER_VOICE_LEVELS, data.inner_voice, 2)
  const look = step(LOOK_LEVELS, data.their_look, 2)
  const waking = step(WAKING_LEVELS, data.waking_realism, 2)
  const reading = step(READ_LEVELS, data.read_pace, 2)
  const together = step(TOGETHER_LEVELS, data.together_realism, 2)
  const families = step(FAMILY_LEVELS, data.growing_families, 2)
  const familyLife = step(FAMILY_LIFE_LEVELS, data.family_life, 2)
  const shapes = step(FAMILY_SHAPES_LEVELS, data.family_shapes, 2)
  const turns = step(TURN_LEVELS, data.life_turns, 2)
  const loss = step(LOSS_LEVELS, data.loss, 2)
  return (
    <section className="settings-section form-stack" aria-labelledby="pace-heading">
      <h2 id="pace-heading">Their days</h2>
      <Field label={`Drama in your worlds: ${level.label}`} tip="Every world follows this unless it has its own, in Life & cities > This world."
        hint={data.world_drama === null ? level.hint : `${level.hint} ${world ?? 'This world'} has its own level, ${step(DRAMA_LEVELS, data.world_drama, 1).label}, in Life & cities.`}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.drama} label={level.label}
          onChange={(drama) => void save({ drama })} />}
      </Field>
      <Field label={`Their looks change: ${looks.label}`} hint={looks.hint} tip="Only looks the app picked change. Anything you wrote about how someone looks stays exactly as you wrote it.">
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.looks_realism} label={looks.label}
          onChange={(looks_realism) => void save({ looks_realism })} />}
      </Field>
      <Field label={`Work life: ${work.label}`} hint={work.hint}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.work_realism} label={work.label}
          onChange={(work_realism) => void save({ work_realism })} />}
      </Field>
      <Field label={`Life's big turns: ${turns.label}`} hint={turns.hint} tip="Undo any big turn on Today, or make it go another way under Hidden values.">
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.life_turns} label={turns.label}
          onChange={(life_turns) => void save({ life_turns })} />}
      </Field>
      <Toggle label="People can pass away" checked={data.people_pass_away} onChange={(value) => void save({ people_pass_away: value })}
        hint={PASS_AWAY_HINT} tip={PASS_AWAY_TIP} />
      {data.people_pass_away && (
        <Field label={`Loss: ${loss.label}`} hint={loss.hint}>
          {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.loss} label={loss.label}
            onChange={(value) => void save({ loss: value })} />}
        </Field>
      )}
      <Field label={`Their pastimes: ${pastimes.label}`} hint={pastimes.hint} tip="Pastimes from their interests, and ones you add, are never given up on their own.">
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.hobbies_realism} label={pastimes.label}
          onChange={(hobbies_realism) => void save({ hobbies_realism })} />}
      </Field>
      <Field label={`Getting together: ${together.label}`} hint={together.hint} tip="You can always ask them over or out yourself, and say not now when someone knocks.">
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.together_realism} label={together.label}
          onChange={(together_realism) => void save({ together_realism })} />}
      </Field>
      <LoveLifeSlider value={data.love_life} onChange={(love_life) => void save({ love_life })} />
      <Field label={`Growing families: ${families.label}`} hint={families.hint} tip="Babies and children are only ever mentioned in words, never pictured. Town babies show up in the paper.">
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.growing_families} label={families.label}
          onChange={(growing_families) => void save({ growing_families })} />}
      </Field>
      <Field label={`Family life: ${familyLife.label}`} hint={familyLife.hint} tip="Your own children with them, once you two have one. Children are only ever mentioned in words, never pictured.">
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.family_life} label={familyLife.label}
          onChange={(family_life) => void save({ family_life })} />}
      </Field>
      <Field label={`Family shapes: ${shapes.label}`} hint={shapes.hint} tip="Change anyone in their family on Today > People.">
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.family_shapes} label={shapes.label}
          onChange={(family_shapes) => void save({ family_shapes })} />}
      </Field>
      <Field label={`Guests in group chats: ${guests.label}`} hint={guests.hint}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.guests_realism} label={guests.label}
          onChange={(guests_realism) => void save({ guests_realism })} />}
      </Field>
      <Field label={`Reading, watching, listening: ${media.label}`} hint={media.hint}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.media_realism} label={media.label}
          onChange={(media_realism) => void save({ media_realism })} />}
      </Field>
      <Field label={`Memes and GIFs: ${memes.label}`} hint={memes.hint} tip="Memes need no image backend. Reaction GIFs need your own GIPHY key, in Settings > Images.">
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.memes_realism} label={memes.label}
          onChange={(memes_realism) => void save({ memes_realism })} />}
      </Field>
      <Field label={`Their look in chat: ${look.label}`} hint={look.hint} tip={LOOK_TIP}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.their_look} label={look.label}
          onChange={(their_look) => void save({ their_look })} />}
      </Field>
      <Field label={`Inner voice: ${voice.label}`} hint={voice.hint} tip="What the Watching page tells while you just watch a world. Feelings come through in words; numbers show only with Hidden values on.">
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.inner_voice} label={voice.label}
          onChange={(inner_voice) => void save({ inner_voice })} />}
      </Field>
      <Toggle label="Reply at their own pace" checked={data.paced_replies} onChange={(value) => void save({ paced_replies: value })}
        hint={`When a companion is busy they decide how to answer: later, a quick holding text first, or a short note now. Asleep, they answer when they wake, unless a second text, "wake up" or a call wakes them. In group chats, each reply shows after the time it would take to read and type it, one after another. Turn off and busy companions answer right away too.`} />
      {data.paced_replies && (
        <div className="toggle-nested">
          <Field label={`Waking them: ${waking.label}`} hint={waking.hint} tip="A companion in another time zone can live on your clock instead: the switch is on their Character page.">
            {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.waking_realism} label={waking.label}
              onChange={(waking_realism) => void save({ waking_realism })} />}
          </Field>
        </div>
      )}
      <Field label={`How quickly they read your texts: ${reading.label}`} hint={reading.hint} tip={READ_TIP}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.read_pace} label={reading.label}
          onChange={(read_pace) => void save({ read_pace })} />}
      </Field>
      <Toggle label="Let their days go off plan" checked={data.day_shifts} onChange={(value) => void save({ day_shifts: value })}
        hint={`Now and then they run late, stay late, have plans fall through, have something come up or get a surprise visit. Rolled with fixed dice, so a day never changes after the fact. Off: every day goes as planned.`} />
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

/** Love and friendship (companion/life/steps.py): how soon companions bring up the next step, whether a close
 * friend can fall for you, rough patches and breakups. */
export function LoveSettings() {
  const { settings, data, save, result } = useLifeSettings()
  if (!data) return <SectionPending queries={[settings]} heading="love-heading" title="Love and friendship" />
  const pace = PACE_LEVELS[data.steps_pace] ?? PACE_LEVELS[2]
  const rough = step(ROUGH_PATCH_LEVELS, data.rough_patches_realism, 2)
  return (
    <section className="settings-section form-stack" aria-labelledby="love-heading">
      <div>
        <h2 id="love-heading">Love and friendship</h2>
        <p className="subtle">Relationships move on by themselves: being exclusive, saying "I love you", meeting their people, becoming best friends. You can always bring a step up yourself, or set it on their Character page.</p>
      </div>
      <Field label={`Relationship pace: ${pace.label}`} hint={pace.hint}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.steps_pace} label={pace.label}
          onChange={(steps_pace) => void save({ steps_pace })} />}
      </Field>
      <Toggle label="Friends can fall for you" checked={data.friends_fall} onChange={(value) => void save({ friends_fall: value })}
        hint={'Now and then a close friend falls for you and tells you. Say yes and you start dating; say no and the friendship carries on after a few awkward days. Rare on a real life, likelier with more drama.'}
        tip="Keep a friend as just friends on their Character page." />
      {/* Next to Breaks and breakups, which needs rough patches at true to life or more (Iris). */}
      <Field label={`Rough patches: ${rough.label}`} hint={rough.hint} tip="You can always clear the air yourself. Companions can be the ones at fault too, and then they apologise first.">
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.rough_patches_realism} label={rough.label}
          onChange={(rough_patches_realism) => void save({ rough_patches_realism })} />}
      </Field>
      <Toggle label="Breaks and breakups" checked={data.breakups} onChange={(value) => void save({ breakups: value })}
        hint={BREAKUPS_HINT} tip="Either of you can end it, and getting back together is possible later. Nothing is deleted." />
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

/** Their own love life (companion/life/love_life.py): how much goes on in the love lives of the people around you. */
function LoveLifeSlider({ value, onChange }: { value: number; onChange: (value: number) => void }) {
  const love = LOVE_LIFE_LEVELS[value] ?? LOVE_LIFE_LEVELS[2]
  return (
    <Field label={`Their love life: ${love.label}`} hint={love.hint} tip="Anyone they start seeing joins the people in their life. You can remove them there, or undo it on Today. Someone in a relationship with you only sees other people in an open relationship, or in secret on Drama.">
      {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={value} label={love.label} onChange={onChange} />}
    </Field>
  )
}

/** Around the home: one slider for each home feature (Vanta, 2026-10-13), each its own life setting. */
export function HomeLifeSettings() {
  const { settings, data, save, result } = useLifeSettings()
  if (!data) return <SectionPending queries={[settings]} heading="home-life-heading" title="Around the home" />
  const upkeep = UPKEEP_LEVELS[data.upkeep_realism] ?? UPKEEP_LEVELS[2]
  const kitchen = KITCHEN_LEVELS[data.kitchen_realism] ?? KITCHEN_LEVELS[2]
  const pets = PET_LEVELS[data.pets_realism] ?? PET_LEVELS[2]
  const admin = ADMIN_LEVELS[data.admin_realism] ?? ADMIN_LEVELS[2]
  return (
    <section className="settings-section form-stack" aria-labelledby="home-life-heading">
      <div>
        <h2 id="home-life-heading">Around the home</h2>
        <p className="subtle">How much everyday life happens at home. Past days stay as they were; changes apply from today.</p>
      </div>
      <Field label={`Housework: ${upkeep.label}`} hint={upkeep.hint}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.upkeep_realism} label={upkeep.label}
          onChange={(upkeep_realism) => void save({ upkeep_realism })} />}
      </Field>
      <Field label={`Kitchen: ${kitchen.label}`} hint={kitchen.hint}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.kitchen_realism} label={kitchen.label}
          onChange={(kitchen_realism) => void save({ kitchen_realism })} />}
      </Field>
      <Field label={`Pets: ${pets.label}`} hint={pets.hint}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.pets_realism} label={pets.label}
          onChange={(pets_realism) => void save({ pets_realism })} />}
      </Field>
      <Toggle label="Pets can die" checked={data.pets_can_die} disabled={data.pets_realism === 0} onChange={(value) => void save({ pets_can_die: value })}
        hint="Rarely, and only late in life: of old age, or a serious illness when they are very old. Off: pets still grow old but are always there. A pet that died can be brought back on the Character page." />
      <Field label={`Life admin: ${admin.label}`} hint={admin.hint}>
        {(id, describedBy) => <StepSlider id={id} describedBy={describedBy} value={data.admin_realism} label={admin.label}
          onChange={(admin_realism) => void save({ admin_realism })} />}
      </Field>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
    </section>
  )
}

/** A slider's step as shown, or the fallback step when the saved value is out of range. */
function step<T>(levels: readonly T[], value: number, fallback: number): T {
  return levels[value] ?? levels[fallback]
}

/** A four-step Realism slider (0 to 3) in the accent colour, with a tick at each step and the step's name read out. */
function StepSlider({ id, describedBy, value, label, onChange }: { id: string; describedBy?: string; value: number; label: string; onChange: (value: number) => void }) {
  return <>
    <input id={id} className="step-slider" type="range" list={`${id}-steps`} min={0} max={3} step={1} value={value} aria-valuetext={label}
      aria-describedby={describedBy} onChange={(event) => onChange(Number(event.target.value))} />
    <datalist id={`${id}-steps`}>{[0, 1, 2, 3].map((step) => <option key={step} value={step} />)}</datalist>
  </>
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
    <section className="settings-section form-stack" aria-labelledby="closeness-settings-heading">
      <div>
        <h2 id="closeness-settings-heading">Closeness</h2>
        <p className="subtle">Closeness grows from the days you talk and the moments you keep. Skip ahead, hold it still or put a limit on it. It only changes how they talk with you.</p>
      </div>
      {companions.length > SEARCH_FROM && (
        <TextInput label="Find a companion" value={filter} onChange={setFilter} maxLength={60} type="search" />
      )}
      {companions.length > 1 && (
        <Field label="Companion" hint="Shows their closeness here. Your open chat stays as it is.">{(id, describedBy) => (
          <select id={id} aria-describedby={describedBy} value={chosen?.id ?? ''} onChange={(event) => setPicked(event.target.value)}>
            {shown.map((chat) => <option key={chat.id} value={chat.id}>{chat.name}</option>)}
          </select>
        )}</Field>
      )}
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
    <div className="form-stack">
      <p>{stageLine(closeness.data, name)}</p>
      <div className="closeness-controls"><StageControls name={name} state={closeness.data} change={change} path={path} /></div>
      {result && <Notice tone={result.tone}>{result.text}</Notice>}
      {open
        ? <p className="subtle">Nickname, running jokes and starting over are in <a href="#memories">{name}&apos;s Memories</a>.</p>
        : <p className="subtle">Nickname, running jokes and starting over are in {name}&apos;s Memories, once their chat is open.</p>}
    </div>
  )
}

/** "Mira is at Friends.", saying so when the user set or keeps it there. */
function stageLine(state: ClosenessState, name: string) {
  const how = state.held_level ? ', kept there by you' : state.set_on ? ', set by you' : ''
  return `${name} is at ${state.name}${how}.`
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
    <section className="settings-section form-stack" aria-labelledby="adult-side-heading">
      <div>
        <h2 id="adult-side-heading">Adult side of life</h2>
        <p className="subtle">Real people have a love life and desires of their own. Off until you turn it on.</p>
      </div>
      <Toggle label="Give adults an adult side" checked={settings.data?.adult_side === true} disabled={!settings.data} onChange={(checked) => void save(checked)}
        hint="Every adult townsperson and companion gets who they're drawn to, how adventurous they are, their drive and a few things they're into, rolled by the app. Adults only: nobody under 18 ever gets one. It stays private to each person and only shapes them when romance or intimacy comes up. It never goes into pictures, the town paper or the feed."
        tip="Change a companion's on their Character page, under Life details. Hidden values can show what townsfolk are like this way." />
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
