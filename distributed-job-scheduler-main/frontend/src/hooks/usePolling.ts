import { useEffect, useRef, useState } from 'react';

export function usePolling(callback: () => void | Promise<void>, intervalMs: number = 5000) {
  const [isPolling, setIsPolling] = useState(true);
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!isPolling) return;

    // Call once initially
    savedCallback.current();

    const id = setInterval(() => {
      savedCallback.current();
    }, intervalMs);

    return () => clearInterval(id);
  }, [intervalMs, isPolling]);

  return { isPolling, setIsPolling };
}
