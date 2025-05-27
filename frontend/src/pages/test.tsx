import { useState } from 'react';

export default function Test() {
  const [count, setCount] = useState(0);

  return (
    <div style={{ padding: '50px' }}>
      <h1>React Test</h1>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        Click me
      </button>
    </div>
  );
} 