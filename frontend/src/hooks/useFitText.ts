import { useEffect, useState } from 'react';

/**
 * useFitText hook - finds a font size that fits the text inside a width
 * Usage: const fontSize = useFitText(ref, { min: 12, max: 36 })
 */
export default function useFitText(ref: React.RefObject<HTMLElement | null>, opts?: { min?: number; max?: number; precision?: number }) {
  const min = opts?.min ?? 10;
  const max = opts?.max ?? 36;
  const precision = opts?.precision ?? 0.5; // px steps
  const [fontSize, setFontSize] = useState<number>(max);

  useEffect(() => {
    let mounted = true;
    if (!ref?.current) return;

    const el = ref.current;

    const compute = () => {
      if (!el) return;
      // Get parent container width
      const container = el.parentElement || el;
      const containerWidth = container.clientWidth - 16; // small padding

      // Build canvas for measure
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const style = window.getComputedStyle(el);
      // Compose font string for canvas measure (e.g. "bold 16px Roboto")
      const font = `${style.fontWeight} ${max}px ${style.fontFamily}`;
      ctx.font = font;

      const text = el.textContent || '';
      let low = min;
      let high = max;
      let best = min;

      while (low <= high) {
        const mid = (low + high) / 2;
        ctx.font = `${style.fontWeight} ${mid}px ${style.fontFamily}`;
        const width = ctx.measureText(text).width;
        if (width <= containerWidth) {
          best = mid;
          low = mid + precision; // try larger
        } else {
          high = mid - precision;
        }
      }

      const chosen = Math.max(min, Math.min(max, best));
      if (mounted) setFontSize(chosen);
    };

    // compute on next tick
    const id = requestAnimationFrame(compute);
    const ro = new ResizeObserver(() => compute());
    try { ro.observe(el); } catch { }
    try { ro.observe(el.parentElement as Element); } catch { }

    // Add event listeners for changes in text (mutation observer)
    const mo = new MutationObserver(() => compute());
    mo.observe(el, { characterData: true, subtree: true, childList: true });

    // cleanup
    return () => {
      mounted = false;
      cancelAnimationFrame(id);
      try { ro.disconnect(); } catch (e) { }
      try { mo.disconnect(); } catch (e) { }
    };
  }, [ref, min, max, precision]);

  return fontSize;
}
