'use client';
import { useEffect, useRef, useState } from 'react';
import { fmtNum } from '@/lib/format';

/** Renders a price; briefly tints green/red when it changes, fading over ~500ms. */
export function PriceCell({ price, testId }: { price: number | null | undefined; testId?: string }) {
  const prev = useRef<number | null | undefined>(price);
  const [flash, setFlash] = useState<'up' | 'down' | null>(null);

  useEffect(() => {
    if (price == null || prev.current == null || price === prev.current) {
      prev.current = price;
      return;
    }
    setFlash(price > prev.current ? 'up' : 'down');
    prev.current = price;
    const t = setTimeout(() => setFlash(null), 80);
    return () => clearTimeout(t);
  }, [price]);

  // While flashing: instant colour. After: transition back (class without flash carries the transition).
  const cls = flash === 'up' ? 'bg-up/30' : flash === 'down' ? 'bg-down/30' : 'bg-transparent transition-colors duration-500';
  return (
    <span data-testid={testId} data-flash={flash ?? ''} className={`inline-block px-1 font-mono ${cls}`}>
      {price == null ? '--' : fmtNum(price)}
    </span>
  );
}
