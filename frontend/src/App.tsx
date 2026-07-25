import { useEffect, useState } from "react";

function App() {
  const [health, setHealth] = useState("checking...");

  useEffect(() => {
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data) => setHealth(data.status))
      .catch(() => setHealth("unreachable"));
  }, []);

  return (
    <div>
      <h1>Job App Agent</h1>
      <p>Backend health: {health}</p>
    </div>
  );
}

export default App;
