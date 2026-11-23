import { useState } from "react";

import Home from "./pages/Home";
import Room from "./pages/Room";
import type { Session } from "./types";

export default function App() {
  const [session, setSession] = useState<Session | null>(null);

  if (session === null) {
    return <Home onSession={setSession} />;
  }
  return <Room session={session} onLeave={() => setSession(null)} />;
}
