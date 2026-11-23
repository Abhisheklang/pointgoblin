export interface Participant {
  key: string;
  name: string;
  is_host: boolean;
}

export interface StoryItem {
  id: string;
  title: string;
  status: "pending" | "active" | "revealed" | "done";
}

export interface VoteResult {
  name: string;
  value: string;
}

export interface RoundResults {
  votes: VoteResult[];
  average: number | null;
  agreement: number | null;
}

export interface RoundState {
  story_id: string;
  revealed: boolean;
  voted: string[];
  vote_count: number;
  results: RoundResults | null;
}

export interface RoomState {
  type: "state";
  room: { code: string; name: string; host_name: string | null };
  deck: string[];
  participants: Participant[];
  stories: StoryItem[];
  round: RoundState | null;
}

export interface YouMessage {
  type: "you";
  name: string;
  is_host: boolean;
}

export type SocketMessage = RoomState | YouMessage;

export interface Session {
  token: string;
  name: string;
  code: string;
  isHostAccount: boolean;
}
