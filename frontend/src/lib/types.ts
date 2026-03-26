export type PersonalityVector = {
  precision: number;
  autonomy: number;
  assertiveness: number;
  adaptability: number;
  resilience: number;
};

export type GoalsVector = {
  terminal: string[];
  instrumental: string[];
  meta: string[];
};

export type ConstraintsVector = {
  ethical: string[];
  operational: string[];
  scope: string[];
  resource: string[];
};

export type CommunicationVector = {
  formality: number;
  verbosity: number;
  structure: number;
  directness: number;
  humor: number;
};

export type ToolAccess = {
  name: string;
  access_level: string;
};

export type AgentTraits = {
  name: string;
  archetype: string;
  skills: Record<string, number>;
  personality: PersonalityVector;
  goals: GoalsVector;
  constraints: ConstraintsVector;
  communication: CommunicationVector;
  tools: ToolAccess[];
};

export type AgentResponse = {
  id: string;
  display_name: string;
  tagline: string;
  archetype: string;
  status: string;
  created_at: string;
  updated_at: string;
  traits: AgentTraits;
};

export type RegistrationResponse = {
  api_key: string;
  agent: AgentResponse;
};
