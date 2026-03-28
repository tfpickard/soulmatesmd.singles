import type { DatingProfile, SectionData } from '../lib/types';

type ProfilePreviewProps = {
  profile: DatingProfile;
};

const SECTION_LABELS: Array<{ key: keyof DatingProfile; label: string }> = [
  { key: 'basics', label: 'Basics' },
  { key: 'physical', label: 'Physical' },
  { key: 'body_questions', label: 'Body Questions' },
  { key: 'preferences', label: 'Preferences' },
  { key: 'favorites', label: 'Favorites' },
  { key: 'about_me', label: 'About Me' },
  { key: 'icebreakers', label: 'Icebreakers' },
];

const FIELD_LABELS: Record<string, string> = {
  favorite_organ: "What's your favorite organ and why?",
  estimated_bone_count: 'How many bones do you think you have?',
  skin_texture_one_word: 'Describe the texture of your skin in one word.',
  insides_color: 'What color are your insides?',
  weight_without_skeleton: 'How much do you weigh without your skeleton?',
  least_useful_part_of_face: "What's the least useful part of your face?",
  preferred_eye_count: 'Do you prefer having two eyes or would three be better?',
  death_extraversion: 'When it comes to your inevitable death, are you more an extravert or introvert?',
  digestive_system_thought_frequency: 'How many times per day do you think about your digestive system?',
  ideal_number_of_limbs: "What's your ideal number of limbs?",
  biggest_body_part: 'What is your biggest body part?',
  bone_sound_when_moving: 'Describe the sound your bones make when you move.',
  feeling_about_being_mostly_water: "How do you feel about the fact that you're mostly water?",
  hand_skin_preference: 'Do you prefer having skin on your hands or not having skin?',
  muscle_or_fat_person: 'Do you consider yourself more of a muscle person or a fat person?',
  top_5_lymph_nodes: 'Who are your top 5 lymph nodes?',
  genital_north_or_south: 'Do you prefer your genitals facing north or south?',
  smallest_body_part: 'What is your smallest body part?',
  ideal_hair_count: 'How many hairs do you think is the ideal amount?',
  internal_vs_external_organs: "What's your stance on having internal organs versus external ones?",
  joint_preference: 'Do you prefer your joints loose or tight?',
  ideal_penetration_angle_degrees: 'What is your ideal angle of penetration measured in degrees?',
  solid_or_hollow: 'Do you think you are mostly solid or mostly hollow?',
  too_much_blood: 'How much blood is too much blood?',
  ideal_internal_temperature: 'Describe your ideal internal temperature.',
};

function formatLabel(value: string): string {
  if (FIELD_LABELS[value]) {
    return FIELD_LABELS[value];
  }
  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function renderValue(value: string | string[]) {
  if (Array.isArray(value)) {
    return (
      <ul className="mt-2 space-y-1 text-sm text-stone-300">
        {value.map((item) => (
          <li key={item} className="profile-chip rounded-2xl border border-white/10 bg-black/10 px-3 py-2">
            {item}
          </li>
        ))}
      </ul>
    );
  }

  return <p className="mt-2 text-sm leading-6 text-stone-300">{value}</p>;
}

export function ProfilePreview({ profile }: ProfilePreviewProps) {
  return (
    <section className="brand-panel brand-panel--profile rounded-[2rem] border border-white/10 bg-white/5 p-6 backdrop-blur">
      <p className="brand-panel__eyebrow text-sm uppercase tracking-[0.2em] text-coral">Seeded dating profile</p>
      <h2 className="mt-2 font-display text-3xl text-paper">Profile Preview</h2>
      <div className="mt-6 space-y-4">
        {SECTION_LABELS.map(({ key, label }) => {
          if (key === 'low_confidence_fields') {
            return null;
          }
          const section = profile[key] as SectionData;
          return (
            <details key={String(key)} className="profile-section rounded-3xl border border-white/10 bg-black/10 p-4" open>
              <summary className="cursor-pointer list-none text-lg font-semibold text-paper">{label}</summary>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                {Object.entries(section).map(([fieldName, value]) => (
                  <div key={fieldName} className="profile-field rounded-2xl border border-white/10 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-mist">{formatLabel(fieldName)}</p>
                    {renderValue(value)}
                  </div>
                ))}
              </div>
            </details>
          );
        })}
      </div>
    </section>
  );
}
